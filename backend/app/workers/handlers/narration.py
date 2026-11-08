"""Background worker handlers for Narration and Audio Generation jobs."""

from typing import Any, Dict
from uuid import UUID

from app.core.logging import logger
from app.db.session import AsyncSessionLocal
from app.models.job import AutomationJob
from app.providers.voice.factory import get_voice_provider
from app.services.narration import NarrationService
from app.workers.handlers.base import (
    BaseJobHandler,
    CancellationChecker,
    HardFailureException,
    JobCancelledException,
    ProgressCallback,
)


class NarrationGenerationJobHandler(BaseJobHandler):
    """Processes asynchronous full video narration synthesis and assembly."""

    def __init__(self, session_factory=None):
        self._session_factory = session_factory or AsyncSessionLocal

    async def validate(self, payload: Dict[str, Any]) -> None:
        if not payload or not isinstance(payload, dict):
            raise HardFailureException("Payload must be a non-empty JSON object.")
        project_id_raw = payload.get("project_id")
        if not project_id_raw:
            raise HardFailureException("Missing required parameter: 'project_id'.")
        try:
            UUID(str(project_id_raw))
        except (ValueError, TypeError):
            raise HardFailureException(f"Invalid UUID for 'project_id': {project_id_raw}")

    async def execute(
        self,
        job: AutomationJob,
        update_progress: ProgressCallback,
        is_cancelled: CancellationChecker,
    ) -> Dict[str, Any]:
        payload = job.payload or {}
        project_id = UUID(str(payload["project_id"]))
        voice_profile_id = (
            UUID(str(payload["voice_profile_id"])) if payload.get("voice_profile_id") else None
        )
        speed = payload.get("speed_ratio")
        pitch = payload.get("pitch_semitones")

        logger.info(f"Executing NARRATION_GENERATION for job {job.id}, project {project_id}")

        # Stage 1: Initializing
        await update_progress(10, "INITIALIZING_NARRATION")
        if await is_cancelled():
            raise JobCancelledException("Narration generation cancelled by user.")

        # Stage 2: Loading scenes and voice
        await update_progress(30, "LOADING_SCENES_AND_VOICE")
        if await is_cancelled():
            raise JobCancelledException("Narration generation cancelled by user.")

        # Stage 3: Synthesizing scene audio
        await update_progress(60, "SYNTHESIZING_SCENE_AUDIO")
        if await is_cancelled():
            raise JobCancelledException("Narration generation cancelled by user.")

        service = NarrationService(provider=get_voice_provider())
        async with (self._session_factory)() as session:
            track = await service.generate_narration_for_project(
                project_id=project_id,
                db=session,
                voice_profile_id=voice_profile_id,
                speed_ratio=speed,
                pitch_semitones=pitch,
            )

        # Stage 4: Stitching master track
        await update_progress(85, "STITCHING_MASTER_TRACK")
        if await is_cancelled():
            raise JobCancelledException("Narration generation cancelled by user.")

        # Stage 5: Evaluating audio quality
        await update_progress(95, "EVALUATING_AUDIO_QUALITY")
        if await is_cancelled():
            raise JobCancelledException("Narration generation cancelled by user.")

        # Stage 6: Completed
        await update_progress(100, "COMPLETED")

        return {
            "narration_track_id": str(track.id),
            "project_id": str(project_id),
            "track_version": track.track_version,
            "duration_seconds": float(track.duration_seconds),
            "file_format": track.file_format,
            "quality_status": track.quality_status,
            "audio_storage_path": track.audio_storage_path,
        }


class VoicePreviewJobHandler(BaseJobHandler):
    """Processes quick voice audition preview generation."""

    def __init__(self, session_factory=None):
        self._session_factory = session_factory or AsyncSessionLocal

    async def validate(self, payload: Dict[str, Any]) -> None:
        if not payload or not isinstance(payload, dict):
            raise HardFailureException("Payload must be a non-empty JSON object.")
        if not payload.get("voice_id"):
            raise HardFailureException("Missing required parameter: 'voice_id'.")

    async def execute(
        self,
        job: AutomationJob,
        update_progress: ProgressCallback,
        is_cancelled: CancellationChecker,
    ) -> Dict[str, Any]:
        payload = job.payload or {}
        voice_id = str(payload["voice_id"])
        sample_text = payload.get("sample_text")

        await update_progress(30, "SYNTHESIZING_VOICE_PREVIEW")
        provider = get_voice_provider()
        res = await provider.preview_voice(voice_id=voice_id, sample_text=sample_text)

        await update_progress(100, "COMPLETED")
        return {
            "voice_id": voice_id,
            "duration_seconds": res.duration_seconds,
            "file_format": res.file_format,
            "size_bytes": res.file_size_bytes,
        }


class NarrationSectionRegenerateJobHandler(BaseJobHandler):
    """Processes single scene audio regeneration and master track re-stitching."""

    def __init__(self, session_factory=None):
        self._session_factory = session_factory or AsyncSessionLocal

    async def validate(self, payload: Dict[str, Any]) -> None:
        if not payload or not isinstance(payload, dict):
            raise HardFailureException("Payload must be a non-empty JSON object.")
        if not payload.get("narration_track_id"):
            raise HardFailureException("Missing required parameter: 'narration_track_id'.")
        if not payload.get("scene_id"):
            raise HardFailureException("Missing required parameter: 'scene_id'.")
        try:
            UUID(str(payload["narration_track_id"]))
            UUID(str(payload["scene_id"]))
        except (ValueError, TypeError):
            raise HardFailureException("Invalid UUID for 'narration_track_id' or 'scene_id'.")

    async def execute(
        self,
        job: AutomationJob,
        update_progress: ProgressCallback,
        is_cancelled: CancellationChecker,
    ) -> Dict[str, Any]:
        payload = job.payload or {}
        track_id = UUID(str(payload["narration_track_id"]))
        scene_id = UUID(str(payload["scene_id"]))
        custom_speed = payload.get("speed_ratio")

        await update_progress(20, "REGENERATING_SCENE_AUDIO")
        if await is_cancelled():
            raise JobCancelledException("Job cancelled by user.")

        service = NarrationService(provider=get_voice_provider())
        async with (self._session_factory)() as session:
            track = await service.regenerate_scene_audio(
                narration_track_id=track_id,
                scene_id=scene_id,
                db=session,
                custom_speed=custom_speed,
            )

        await update_progress(80, "RESTITCHING_MASTER_TRACK")
        await update_progress(100, "COMPLETED")

        return {
            "narration_track_id": str(track.id),
            "scene_id": str(scene_id),
            "updated_duration_seconds": float(track.duration_seconds),
            "quality_status": track.quality_status,
        }
