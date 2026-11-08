"""Narration Generation, Scene-Level Speech Synthesis, and Track Assembly Service."""

import io
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.logging import logger
from app.models.channel import Channel
from app.models.project import VideoProject
from app.models.scene import Scene
from app.models.script import Script
from app.models.voice import NarrationTrack, Voiceover, VoiceProfile
from app.providers.voice.base import VoiceProviderInterface
from app.providers.voice.factory import get_voice_provider
from app.providers.voice.mock import create_synthetic_wav_bytes
from app.services.audio_processing import AudioProcessingService
from app.services.audio_quality import AudioQualityService
from app.services.storage import StorageService


class NarrationService:
    """Orchestrates scene speech synthesis, chunk management, audio mastering, and versioning."""

    def __init__(
        self,
        provider: Optional[VoiceProviderInterface] = None,
        storage: Optional[StorageService] = None,
    ):
        self._provider = provider or get_voice_provider()
        self._storage = storage or StorageService()

    @property
    def provider(self) -> VoiceProviderInterface:
        return self._provider

    @property
    def storage(self) -> StorageService:
        return self._storage

    async def _resolve_voice_profile(
        self,
        channel_id: UUID,
        voice_profile_id: Optional[UUID],
        db: AsyncSession,
    ) -> VoiceProfile:
        """Resolve requested voice profile or fallback to channel default or create system profile."""
        if voice_profile_id:
            stmt = select(VoiceProfile).where(VoiceProfile.id == voice_profile_id)
            res = await db.execute(stmt)
            profile = res.scalar_one_or_none()
            if profile:
                return profile

        # Look for default channel profile
        stmt = (
            select(VoiceProfile)
            .where(VoiceProfile.channel_id == channel_id, VoiceProfile.is_default.is_(True))
        )
        res = await db.execute(stmt)
        profile = res.scalar_one_or_none()
        if profile:
            return profile

        # Any channel profile
        stmt = select(VoiceProfile).where(VoiceProfile.channel_id == channel_id)
        res = await db.execute(stmt)
        profile = res.scalars().first()
        if profile:
            return profile

        # Create standard default profile for channel
        default_voice_id = "en-US-ChristopherNeural" if self.provider.name == "edge-tts" else "mock-tech-male-1"
        profile = VoiceProfile(
            channel_id=channel_id,
            display_name="Christopher (Default Tech Lead)",
            provider=self.provider.name,
            provider_voice_id=default_voice_id,
            language_code="en-US",
            description="Calm, authoritative narrator for technical topics.",
            gender="MALE",
            speed_ratio=1.00,
            pitch_semitones=0.00,
            is_default=True,
            is_active=True,
        )
        db.add(profile)
        await db.flush()
        return profile

    async def generate_narration_for_project(
        self,
        project_id: UUID,
        db: AsyncSession,
        voice_profile_id: Optional[UUID] = None,
        speed_ratio: Optional[float] = None,
        pitch_semitones: Optional[float] = None,
    ) -> NarrationTrack:
        """Execute full speech synthesis across all scenes, concatenate master track, and run QA."""
        # 1. Load project context
        stmt = (
            select(VideoProject)
            .options(
                selectinload(VideoProject.channel),
                selectinload(VideoProject.scripts),
                selectinload(VideoProject.scenes),
            )
            .where(VideoProject.id == project_id)
        )
        res = await db.execute(stmt)
        project = res.scalar_one_or_none()
        if not project:
            raise ValueError(f"Project with ID '{project_id}' not found.")

        channel: Channel = project.channel
        scripts: List[Script] = project.scripts
        if not scripts:
            raise ValueError(f"Project '{project_id}' has no scripts. Generate a script before voiceover.")

        # Use latest script
        latest_script = sorted(scripts, key=lambda s: s.version, reverse=True)[0]

        # Scenes
        scenes = sorted(project.scenes, key=lambda s: s.scene_order)
        if not scenes:
            # Fallback: create default scene from script
            scene = Scene(
                project_id=project.id,
                scene_order=1,
                narration_text=latest_script.full_text,
                visual_archetype="INFOGRAPHIC",
                visual_directive="Full screen architectural diagram",
                duration_seconds=latest_script.estimated_duration_seconds or 60,
            )
            db.add(scene)
            await db.flush()
            scenes = [scene]

        # 2. Resolve Voice Profile
        profile = await self._resolve_voice_profile(channel.id, voice_profile_id, db)
        effective_speed = speed_ratio or float(profile.speed_ratio)
        effective_pitch = pitch_semitones or float(profile.pitch_semitones)

        logger.info(
            f"Generating narration for project {project_id}: {len(scenes)} scenes using voice '{profile.provider_voice_id}'"
        )

        # 3. Synthesize speech for each scene
        wav_chunks: List[bytes] = []
        voiceover_rows: List[Voiceover] = []

        for idx, scene in enumerate(scenes, start=1):
            synthesis_result = await self.provider.generate_speech(
                text=scene.narration_text,
                voice_id=profile.provider_voice_id,
                speed_ratio=effective_speed,
                pitch_semitones=effective_pitch,
                output_format="wav",
            )

            # Standardize to WAV for downstream concatenation
            chunk_bytes = synthesis_result.audio_bytes
            if synthesis_result.file_format != "wav":
                # Convert or wrap synthetic WAV
                chunk_bytes = create_synthetic_wav_bytes(
                    duration_seconds=synthesis_result.duration_seconds,
                    sample_rate=24000,
                )

            # Save individual scene chunk to storage
            chunk_filename = f"chunk_scene_{scene.scene_order}_{uuid4().hex[:8]}.wav"
            rel_path = await self.storage.save_audio_file(
                channel_id=channel.id,
                project_id=project.id,
                filename=chunk_filename,
                data=chunk_bytes,
            )

            wav_chunks.append(chunk_bytes)

            # Check existing voiceover for scene
            vo_stmt = select(Voiceover).where(Voiceover.scene_id == scene.id)
            vo_res = await db.execute(vo_stmt)
            existing_vo = vo_res.scalar_one_or_none()

            word_timestamps_dict = [
                {"word": wt.word, "start": wt.start, "end": wt.end}
                for wt in synthesis_result.word_timestamps
            ]

            if existing_vo:
                existing_vo.tts_engine = self.provider.name
                existing_vo.voice_id = profile.provider_voice_id
                existing_vo.audio_storage_path = rel_path
                existing_vo.duration_seconds = synthesis_result.duration_seconds
                existing_vo.word_timestamps = word_timestamps_dict
                existing_vo.loudness_lufs = synthesis_result.loudness_lufs or -14.0
                existing_vo.chunk_index = scene.scene_order
                existing_vo.status = "GENERATED"
                voiceover_rows.append(existing_vo)
            else:
                new_vo = Voiceover(
                    scene_id=scene.id,
                    project_id=project.id,
                    tts_engine=self.provider.name,
                    voice_id=profile.provider_voice_id,
                    audio_storage_path=rel_path,
                    duration_seconds=synthesis_result.duration_seconds,
                    word_timestamps=word_timestamps_dict,
                    loudness_lufs=synthesis_result.loudness_lufs or -14.0,
                    chunk_index=scene.scene_order,
                    status="GENERATED",
                )
                db.add(new_vo)
                voiceover_rows.append(new_vo)

        # 4. Stitch Master Audio Track with 350ms pauses between scenes
        master_wav_bytes = AudioProcessingService.concatenate_wav_chunks(
            wav_chunks=wav_chunks,
            pause_between_chunks_sec=0.35,
        )

        master_meta = AudioProcessingService.get_wav_metadata(master_wav_bytes)
        loudness_lufs = AudioProcessingService.estimate_loudness_lufs(master_wav_bytes)

        # Save master audio track to storage
        master_filename = f"master_track_s{latest_script.version}_{uuid4().hex[:8]}.wav"
        master_rel_path = await self.storage.save_audio_file(
            channel_id=channel.id,
            project_id=project.id,
            filename=master_filename,
            data=master_wav_bytes,
        )

        # 5. Run Quality Evaluation
        quality_eval = AudioQualityService.evaluate_narration_quality(
            master_wav_bytes=master_wav_bytes,
            script_word_count=latest_script.word_count,
            scene_count=len(scenes),
            chunk_count=len(wav_chunks),
            expected_duration_seconds=latest_script.estimated_duration_seconds,
        )

        # 6. Determine Track Version
        existing_tracks_stmt = (
            select(NarrationTrack)
            .where(NarrationTrack.project_id == project_id)
            .order_by(NarrationTrack.track_version.desc())
        )
        existing_tracks_res = await db.execute(existing_tracks_stmt)
        latest_track = existing_tracks_res.scalars().first()
        next_track_version = (latest_track.track_version + 1) if latest_track else 1

        # 7. Create NarrationTrack Record
        track = NarrationTrack(
            project_id=project_id,
            script_id=latest_script.id,
            voice_profile_id=profile.id,
            script_version=latest_script.version,
            track_version=next_track_version,
            audio_storage_path=master_rel_path,
            file_format="wav",
            sample_rate=master_meta.sample_rate,
            channels=master_meta.channels,
            duration_seconds=master_meta.duration_seconds,
            file_size_bytes=master_meta.file_size_bytes,
            loudness_lufs=loudness_lufs,
            is_approved=False,
            status="READY",
            quality_status=quality_eval["quality_status"],
            quality_report=quality_eval,
        )
        db.add(track)
        await db.flush()

        # Link voiceovers to narration track
        for vo in voiceover_rows:
            vo.narration_track_id = track.id

        # Update Project State
        project.state = "VOICE_GENERATED"
        await db.commit()

        # Reload with relations
        reload_stmt = (
            select(NarrationTrack)
            .options(
                selectinload(NarrationTrack.voice_profile),
                selectinload(NarrationTrack.voiceovers).selectinload(Voiceover.scene),
            )
            .where(NarrationTrack.id == track.id)
        )
        reload_res = await db.execute(reload_stmt)
        return reload_res.scalar_one()

    async def regenerate_scene_audio(
        self,
        narration_track_id: UUID,
        scene_id: UUID,
        db: AsyncSession,
        custom_speed: Optional[float] = None,
    ) -> NarrationTrack:
        """Regenerate audio for a single scene and re-stitch the master track."""
        stmt = (
            select(NarrationTrack)
            .options(
                selectinload(NarrationTrack.project).selectinload(VideoProject.channel),
                selectinload(NarrationTrack.voice_profile),
                selectinload(NarrationTrack.voiceovers).selectinload(Voiceover.scene),
            )
            .where(NarrationTrack.id == narration_track_id)
        )
        res = await db.execute(stmt)
        track = res.scalar_one_or_none()
        if not track:
            raise ValueError(f"NarrationTrack '{narration_track_id}' not found.")

        # Find voiceover for this scene
        target_vo = next((vo for vo in track.voiceovers if str(vo.scene_id) == str(scene_id)), None)
        if not target_vo:
            raise ValueError(f"Scene '{scene_id}' is not associated with NarrationTrack '{narration_track_id}'.")

        scene = target_vo.scene
        profile = track.voice_profile
        effective_speed = custom_speed or (float(profile.speed_ratio) if profile else 1.0)
        voice_id = profile.provider_voice_id if profile else "en-US-ChristopherNeural"

        logger.info(f"Regenerating audio for scene {scene.scene_order} (ID: {scene_id})")

        # Synthesize updated scene audio
        result = await self.provider.generate_speech(
            text=scene.narration_text,
            voice_id=voice_id,
            speed_ratio=effective_speed,
            output_format="wav",
        )

        chunk_bytes = result.audio_bytes
        if result.file_format != "wav":
            chunk_bytes = create_synthetic_wav_bytes(result.duration_seconds, sample_rate=24000)

        chunk_filename = f"chunk_scene_{scene.scene_order}_{uuid4().hex[:8]}.wav"
        rel_path = await self.storage.save_audio_file(
            channel_id=track.project.channel_id,
            project_id=track.project_id,
            filename=chunk_filename,
            data=chunk_bytes,
        )

        # Update voiceover
        target_vo.audio_storage_path = rel_path
        target_vo.duration_seconds = result.duration_seconds
        target_vo.word_timestamps = [
            {"word": wt.word, "start": wt.start, "end": wt.end}
            for wt in result.word_timestamps
        ]
        target_vo.loudness_lufs = result.loudness_lufs or -14.0

        # Reload all scene audio chunks in order and re-stitch
        ordered_vos = sorted(track.voiceovers, key=lambda vo: vo.chunk_index)
        wav_chunks: List[bytes] = []
        for vo in ordered_vos:
            chunk_data = await self.storage.read_audio_file(vo.audio_storage_path)
            wav_chunks.append(chunk_data)

        # Re-stitch master
        master_wav_bytes = AudioProcessingService.concatenate_wav_chunks(wav_chunks, pause_between_chunks_sec=0.35)
        master_meta = AudioProcessingService.get_wav_metadata(master_wav_bytes)

        # Save updated master file
        updated_master_name = f"master_track_v{track.track_version}_rev_{uuid4().hex[:8]}.wav"
        updated_master_path = await self.storage.save_audio_file(
            channel_id=track.project.channel_id,
            project_id=track.project_id,
            filename=updated_master_name,
            data=master_wav_bytes,
        )

        # Update track metadata
        track.audio_storage_path = updated_master_path
        track.duration_seconds = master_meta.duration_seconds
        track.file_size_bytes = master_meta.file_size_bytes
        track.loudness_lufs = AudioProcessingService.estimate_loudness_lufs(master_wav_bytes)

        # Re-evaluate QA
        quality_eval = AudioQualityService.evaluate_narration_quality(
            master_wav_bytes=master_wav_bytes,
            script_word_count=len(" ".join(vo.scene.narration_text for vo in ordered_vos).split()),
            scene_count=len(ordered_vos),
            chunk_count=len(ordered_vos),
        )
        track.quality_status = quality_eval["quality_status"]
        track.quality_report = quality_eval

        await db.commit()
        reload_stmt = (
            select(NarrationTrack)
            .options(
                selectinload(NarrationTrack.voice_profile),
                selectinload(NarrationTrack.voiceovers).selectinload(Voiceover.scene),
            )
            .where(NarrationTrack.id == track.id)
        )
        reload_res = await db.execute(reload_stmt)
        return reload_res.scalar_one()
