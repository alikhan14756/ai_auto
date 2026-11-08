"""Voice Generation, Voice Profiles, Audio Streaming, and Narration REST API Endpoints."""

import base64
import io
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db
from app.models.channel import Channel
from app.models.project import VideoProject
from app.models.user import User
from app.models.voice import NarrationTrack, Voiceover, VoiceProfile
from app.providers.voice.base import VoiceProviderError
from app.providers.voice.factory import get_voice_provider
from app.schemas.job import JobRead
from app.schemas.voice import (
    NarrationGenerateRequest,
    NarrationSectionRegenerateRequest,
    NarrationTrackResponse,
    VoiceInfoResponse,
    VoiceoverChunkResponse,
    VoicePreviewRequest,
    VoicePreviewResponse,
    VoiceProfileCreate,
    VoiceProfileResponse,
    VoiceProfileUpdate,
)
from app.services.job_queue import JobQueueService
from app.services.narration import NarrationService
from app.services.storage import StorageService

router = APIRouter()


async def _verify_channel_access(channel_id: UUID, user: User, db: AsyncSession) -> Channel:
    """Verify channel exists and belongs to authenticated user."""
    stmt = select(Channel).where(Channel.id == channel_id)
    res = await db.execute(stmt)
    channel = res.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found.")

    if channel.user_id != user.id and user.role != "SUPER_ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access to channel denied.")

    return channel


async def _verify_project_access(project_id: UUID, user: User, db: AsyncSession) -> VideoProject:
    """Verify video project exists and belongs to authenticated user."""
    stmt = (
        select(VideoProject)
        .options(selectinload(VideoProject.channel))
        .where(VideoProject.id == project_id)
    )
    res = await db.execute(stmt)
    project = res.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="VideoProject not found.")

    if project.channel.user_id != user.id and user.role != "SUPER_ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access to project denied.")

    return project


def _format_track_response(track: NarrationTrack) -> NarrationTrackResponse:
    """Format NarrationTrack and populate audio download URLs."""
    resp = NarrationTrackResponse.model_validate(track)
    resp.audio_url = f"/api/v1/voice/tracks/{track.id}/audio"
    if track.voiceovers:
        resp.voiceovers = [
            VoiceoverChunkResponse(
                id=vo.id,
                scene_id=vo.scene_id,
                chunk_index=vo.chunk_index,
                duration_seconds=float(vo.duration_seconds),
                word_timestamps=vo.word_timestamps or [],
                loudness_lufs=float(vo.loudness_lufs),
                status=vo.status,
                audio_url=f"/api/v1/voice/chunks/{vo.id}/audio",
            )
            for vo in track.voiceovers
        ]
    return resp


# ============================================================================
# Providers & Voice Discovery
# ============================================================================

@router.get("/providers")
async def list_voice_providers(current_user: User = Depends(get_current_user)):
    """List available text-to-speech engines and capabilities."""
    provider = get_voice_provider()
    caps = provider.get_capabilities()
    return {
        "active_provider": provider.name,
        "available_providers": [
            {
                "name": "edge-tts",
                "display_name": "Microsoft Edge Online Neural TTS",
                "cost_tier": "Free / Zero-Cost",
                "is_active": provider.name == "edge-tts",
                "supports_word_timestamps": True,
            },
            {
                "name": "mock",
                "display_name": "Deterministic Mock Voice Engine",
                "cost_tier": "Free / Offline Testing",
                "is_active": provider.name == "mock",
                "supports_word_timestamps": True,
            },
        ],
        "active_capabilities": caps,
    }


@router.get("/voices", response_model=List[VoiceInfoResponse])
async def list_voices(
    language_code: Optional[str] = Query(None, description="Locale filter (e.g. en-US)"),
    current_user: User = Depends(get_current_user),
):
    """Browse available voices from the active TTS engine."""
    provider = get_voice_provider()
    try:
        voices = await provider.list_voices(language_code=language_code)
        return [
            VoiceInfoResponse(
                voice_id=v.voice_id,
                display_name=v.display_name,
                provider=v.provider,
                language_code=v.language_code,
                gender=v.gender,
                description=v.description,
                is_neural=v.is_neural,
                is_free=v.is_free,
            )
            for v in voices
        ]
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))


# ============================================================================
# Voice Profiles Management
# ============================================================================

@router.get("/profiles", response_model=List[VoiceProfileResponse])
async def list_voice_profiles(
    channel_id: UUID = Query(..., description="Target Channel ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List configured voice profiles for a channel."""
    await _verify_channel_access(channel_id, current_user, db)

    stmt = (
        select(VoiceProfile)
        .where((VoiceProfile.channel_id == channel_id) | (VoiceProfile.channel_id.is_(None)))
        .order_by(VoiceProfile.is_default.desc(), VoiceProfile.created_at.desc())
    )
    res = await db.execute(stmt)
    profiles = list(res.scalars().all())
    return profiles


@router.post("/profiles", response_model=VoiceProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_voice_profile(
    payload: VoiceProfileCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new reusable channel voice profile."""
    await _verify_channel_access(payload.channel_id, current_user, db)

    # If this profile is marked default, unset existing default
    if payload.is_default:
        existing_stmt = select(VoiceProfile).where(VoiceProfile.channel_id == payload.channel_id)
        existing_res = await db.execute(existing_stmt)
        for p in existing_res.scalars().all():
            p.is_default = False

    profile = VoiceProfile(
        channel_id=payload.channel_id,
        display_name=payload.display_name,
        provider=payload.provider,
        provider_voice_id=payload.provider_voice_id,
        language_code=payload.language_code,
        description=payload.description,
        gender=payload.gender,
        speed_ratio=payload.speed_ratio,
        pitch_semitones=payload.pitch_semitones,
        is_default=payload.is_default,
        is_active=True,
        settings=payload.settings,
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


@router.patch("/profiles/{profile_id}", response_model=VoiceProfileResponse)
async def update_voice_profile(
    profile_id: UUID,
    payload: VoiceProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update settings of an existing voice profile."""
    stmt = select(VoiceProfile).where(VoiceProfile.id == profile_id)
    res = await db.execute(stmt)
    profile = res.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voice profile not found.")

    if profile.channel_id:
        await _verify_channel_access(profile.channel_id, current_user, db)

    if payload.display_name is not None:
        profile.display_name = payload.display_name
    if payload.speed_ratio is not None:
        profile.speed_ratio = payload.speed_ratio
    if payload.pitch_semitones is not None:
        profile.pitch_semitones = payload.pitch_semitones
    if payload.is_active is not None:
        profile.is_active = payload.is_active
    if payload.settings is not None:
        profile.settings = payload.settings
    if payload.is_default is not None:
        profile.is_default = payload.is_default

    await db.commit()
    await db.refresh(profile)
    return profile


@router.delete("/profiles/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_voice_profile(
    profile_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a custom voice profile."""
    stmt = select(VoiceProfile).where(VoiceProfile.id == profile_id)
    res = await db.execute(stmt)
    profile = res.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voice profile not found.")

    if profile.channel_id:
        await _verify_channel_access(profile.channel_id, current_user, db)

    await db.delete(profile)
    await db.commit()
    return None


# ============================================================================
# Voice Preview
# ============================================================================

@router.post("/preview", response_model=VoicePreviewResponse)
async def preview_voice(
    payload: VoicePreviewRequest,
    current_user: User = Depends(get_current_user),
):
    """Generate a quick voice audition sample."""
    provider = get_voice_provider(payload.provider)
    try:
        sample = await provider.preview_voice(
            voice_id=payload.voice_id,
            sample_text=payload.sample_text,
        )
        audio_b64 = base64.b64encode(sample.audio_bytes).decode("ascii")
        return VoicePreviewResponse(
            voice_id=payload.voice_id,
            duration_seconds=sample.duration_seconds,
            file_format=sample.file_format,
            audio_base64=audio_b64,
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


# ============================================================================
# Narration Generation Pipeline
# ============================================================================

@router.post("/generate", response_model=JobRead, status_code=status.HTTP_202_ACCEPTED)
async def trigger_narration_generation_job(
    request: NarrationGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Enqueue an asynchronous speech synthesis job in the worker queue."""
    project = await _verify_project_access(request.project_id, current_user, db)

    queue_service = JobQueueService(db)
    job, _ = await queue_service.enqueue_job(
        channel_id=project.channel_id,
        job_type="NARRATION_GENERATION",
        payload={
            "project_id": str(request.project_id),
            "voice_profile_id": str(request.voice_profile_id) if request.voice_profile_id else None,
            "speed_ratio": request.speed_ratio,
            "pitch_semitones": request.pitch_semitones,
        },
        priority=5,
    )
    return job


@router.post("/generate-sync", response_model=NarrationTrackResponse, status_code=status.HTTP_201_CREATED)
async def generate_narration_sync(
    request: NarrationGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Synchronously generate scene audio chunks and assemble master track."""
    await _verify_project_access(request.project_id, current_user, db)

    try:
        service = NarrationService(provider=get_voice_provider())
        track = await service.generate_narration_for_project(
            project_id=request.project_id,
            db=db,
            voice_profile_id=request.voice_profile_id,
            speed_ratio=request.speed_ratio,
            pitch_semitones=request.pitch_semitones,
        )
        return _format_track_response(track)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except VoiceProviderError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))


# ============================================================================
# Narration Track History & Management
# ============================================================================

@router.get("/tracks", response_model=List[NarrationTrackResponse])
async def list_narration_tracks(
    project_id: UUID = Query(..., description="Target VideoProject ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve narration track history for a project."""
    await _verify_project_access(project_id, current_user, db)

    stmt = (
        select(NarrationTrack)
        .options(
            selectinload(NarrationTrack.voice_profile),
            selectinload(NarrationTrack.voiceovers),
        )
        .where(NarrationTrack.project_id == project_id)
        .order_by(NarrationTrack.track_version.desc())
    )
    res = await db.execute(stmt)
    tracks = list(res.scalars().all())
    return [_format_track_response(t) for t in tracks]


@router.get("/tracks/{track_id}", response_model=NarrationTrackResponse)
async def get_narration_track(
    track_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve detailed narration track parameters, scene chunks, and audio quality report."""
    stmt = (
        select(NarrationTrack)
        .options(
            selectinload(NarrationTrack.voice_profile),
            selectinload(NarrationTrack.voiceovers).selectinload(Voiceover.scene),
        )
        .where(NarrationTrack.id == track_id)
    )
    res = await db.execute(stmt)
    track = res.scalar_one_or_none()
    if not track:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Narration track not found.")

    await _verify_project_access(track.project_id, current_user, db)
    return _format_track_response(track)


@router.post("/tracks/{track_id}/approve", response_model=NarrationTrackResponse)
async def approve_narration_track(
    track_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Approve narration track for video rendering."""
    stmt = (
        select(NarrationTrack)
        .options(
            selectinload(NarrationTrack.voice_profile),
            selectinload(NarrationTrack.voiceovers),
        )
        .where(NarrationTrack.id == track_id)
    )
    res = await db.execute(stmt)
    track = res.scalar_one_or_none()
    if not track:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Narration track not found.")

    project = await _verify_project_access(track.project_id, current_user, db)

    track.is_approved = True
    project.state = "VOICE_APPROVED"
    await db.commit()

    reload_stmt = (
        select(NarrationTrack)
        .options(
            selectinload(NarrationTrack.voice_profile),
            selectinload(NarrationTrack.voiceovers).selectinload(Voiceover.scene),
        )
        .where(NarrationTrack.id == track_id)
    )
    reload_res = await db.execute(reload_stmt)
    return _format_track_response(reload_res.scalar_one())


@router.post("/tracks/{track_id}/regenerate-section", response_model=NarrationTrackResponse)
async def regenerate_section_audio(
    track_id: UUID,
    payload: NarrationSectionRegenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Regenerate audio for a single scene and re-stitch the master narration track."""
    stmt = select(NarrationTrack).where(NarrationTrack.id == track_id)
    res = await db.execute(stmt)
    track = res.scalar_one_or_none()
    if not track:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Narration track not found.")

    await _verify_project_access(track.project_id, current_user, db)

    try:
        service = NarrationService(provider=get_voice_provider())
        updated_track = await service.regenerate_scene_audio(
            narration_track_id=track_id,
            scene_id=payload.scene_id,
            db=db,
            custom_speed=payload.speed_ratio,
        )
        return _format_track_response(updated_track)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


# ============================================================================
# Secure Audio Binary Streaming
# ============================================================================

@router.get("/tracks/{track_id}/audio")
async def stream_master_audio(
    track_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Stream or download the master narration WAV audio file with authorization."""
    stmt = select(NarrationTrack).where(NarrationTrack.id == track_id)
    res = await db.execute(stmt)
    track = res.scalar_one_or_none()
    if not track:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Narration track not found.")

    await _verify_project_access(track.project_id, current_user, db)

    storage = StorageService()
    try:
        audio_bytes = await storage.read_audio_file(track.audio_storage_path)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio file not found on disk.")

    media_type = "audio/wav" if track.file_format == "wav" else "audio/mpeg"
    filename = f"narration_track_v{track.track_version}.{track.file_format}"

    return Response(
        content=audio_bytes,
        media_type=media_type,
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.get("/chunks/{chunk_id}/audio")
async def stream_chunk_audio(
    chunk_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Stream or download an individual scene audio chunk."""
    stmt = (
        select(Voiceover)
        .options(selectinload(Voiceover.project).selectinload(VideoProject.channel))
        .where(Voiceover.id == chunk_id)
    )
    res = await db.execute(stmt)
    vo = res.scalar_one_or_none()
    if not vo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scene voiceover not found.")

    if vo.project.channel.user_id != current_user.id and current_user.role != "SUPER_ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    storage = StorageService()
    try:
        audio_bytes = await storage.read_audio_file(vo.audio_storage_path)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chunk audio file not found on disk.")

    return Response(
        content=audio_bytes,
        media_type="audio/wav",
        headers={"Content-Disposition": f'inline; filename="scene_{vo.chunk_index}.wav"'},
    )
