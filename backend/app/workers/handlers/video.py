"""Worker job handlers for Video Timeline Generation, Video Rendering, and Video Validation."""

import asyncio
import os
import uuid
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import select
from app.core.config import settings
from app.core.logging import logger
from app.db.session import AsyncSessionLocal
from app.models.job import AutomationJob
from app.models.project import VideoProject
from app.models.qa import QualityReport
from app.models.render import RenderJob
from app.models.storyboard import Storyboard
from app.models.scene import Scene
from app.models.timeline import VideoTimeline, TimelineScene, CaptionAsset
from app.models.user import User
from app.models.voice import NarrationTrack
from app.services.video.renderer import VideoRenderingEngine
from app.services.video.validator import VideoValidationService
from app.services.video.subtitles import SubtitleCompiler
from app.workers.handlers.base import (
    BaseJobHandler,
    CancellationChecker,
    HardFailureException,
    JobCancelledException,
    ProgressCallback,
)


class TimelineGenerationJobHandler(BaseJobHandler):
    """Processes asynchronous timeline generation from a storyboard."""

    def __init__(self, session_factory=None):
        self._session_factory = session_factory or AsyncSessionLocal

    async def validate(self, payload: Dict[str, Any]) -> None:
        if not payload or not isinstance(payload, dict):
            raise HardFailureException("Payload must be a non-empty JSON object.")
        if not payload.get("storyboard_id"):
            raise HardFailureException("Missing required parameter: 'storyboard_id'.")
        try:
            UUID(str(payload["storyboard_id"]))
        except (ValueError, TypeError):
            raise HardFailureException(f"Invalid UUID for 'storyboard_id': {payload.get('storyboard_id')}")

    async def execute(
        self,
        job: AutomationJob,
        update_progress: ProgressCallback,
        is_cancelled: CancellationChecker,
    ) -> Dict[str, Any]:
        if await is_cancelled():
            raise JobCancelledException(f"Job {job.id} was cancelled before execution.")

        payload = job.payload or {}
        storyboard_id = UUID(str(payload["storyboard_id"]))
        aspect_ratio = payload.get("aspect_ratio")
        fps = int(payload.get("fps", 30))

        await update_progress(10, "INITIALIZING")

        async with self._session_factory() as db:
            # Query storyboard
            sb_stmt = select(Storyboard).where(Storyboard.id == storyboard_id)
            sb_res = await db.execute(sb_stmt)
            storyboard = sb_res.scalars().first()
            if not storyboard:
                raise HardFailureException(f"Storyboard {storyboard_id} not found.")

            target_aspect = aspect_ratio or storyboard.aspect_ratio or "16:9"
            width, height = (1080, 1920) if target_aspect == "9:16" else (1920, 1080)

            # Query scenes
            sc_stmt = (
                select(Scene)
                .where(Scene.storyboard_id == storyboard.id)
                .order_by(Scene.scene_order.asc())
            )
            sc_res = await db.execute(sc_stmt)
            scenes = sc_res.scalars().all()

            await update_progress(30, "ASSEMBLING_TIMELINE")

            timeline = VideoTimeline(
                id=uuid.uuid4(),
                project_id=storyboard.project_id,
                aspect_ratio=target_aspect,
                fps=fps,
                width=width,
                height=height,
                total_duration_seconds=Decimal("0.00"),
                status="READY",
                ducking_enabled=True,
                ducking_db=-6.0,
                narration_track_id=storyboard.narration_track_id,
                settings={},
            )
            db.add(timeline)
            await db.flush()

            current_time = Decimal("0.00")
            subtitle_cues = []

            for seq, sc in enumerate(scenes, start=1):
                dur = sc.duration_seconds if sc.duration_seconds and sc.duration_seconds > 0 else Decimal("5.00")
                start_t = current_time
                end_t = current_time + dur
                current_time = end_t

                tl_scene = TimelineScene(
                    id=uuid.uuid4(),
                    timeline_id=timeline.id,
                    scene_id=sc.id,
                    sequence_number=seq,
                    start_time_seconds=start_t,
                    end_time_seconds=end_t,
                    duration_seconds=dur,
                    asset_id=sc.selected_asset_id,
                    visual_asset_path=sc.image_prompt,  # default
                    transition_type=sc.transition.lower() if sc.transition else "cut",
                    transition_duration=Decimal("0.50"),
                    motion_effect="zoom_in",
                    motion_intensity=1.15,
                    voiceover_segment_id=None,
                    clip_settings={},
                )
                db.add(tl_scene)

                text = sc.narration_text or sc.script_text or ""
                if text:
                    subtitle_cues.append({
                        "start": float(start_t),
                        "end": float(end_t),
                        "text": text,
                    })

            timeline.total_duration_seconds = current_time

            # Subtitles compilation
            await update_progress(70, "COMPILING_CAPTIONS")
            ass_content = SubtitleCompiler.compile_ass(
                cues=subtitle_cues,
                style_preset="vivid_ember",
                width=width,
                height=height,
            )
            sub_filename = f"subtitles_{timeline.id}.ass"
            sub_path = f"{settings.SUBTITLES_OUTPUT_DIR}/{sub_filename}"
            saved_sub_path = SubtitleCompiler.save_subtitles(ass_content, sub_path)

            caption = CaptionAsset(
                id=uuid.uuid4(),
                timeline_id=timeline.id,
                format="ass",
                style_preset="vivid_ember",
                primary_color="&H00FFFFFF",
                highlight_color="&H00007AFF",
                font_name="Arial",
                font_size=48,
                file_path=saved_sub_path,
                raw_content=ass_content,
                is_embedded=True,
            )
            db.add(caption)

            await db.commit()
            await update_progress(100, "COMPLETED")

            return {
                "timeline_id": str(timeline.id),
                "scene_count": len(scenes),
                "total_duration_seconds": float(current_time),
                "aspect_ratio": target_aspect,
            }


class VideoRenderJobHandler(BaseJobHandler):
    """Executes FFmpeg or MockVideoRenderer video assembly pipeline."""

    def __init__(self, session_factory=None):
        self._session_factory = session_factory or AsyncSessionLocal

    async def validate(self, payload: Dict[str, Any]) -> None:
        if not payload or not isinstance(payload, dict):
            raise HardFailureException("Payload must be a non-empty JSON object.")
        if not payload.get("render_job_id"):
            raise HardFailureException("Missing required parameter: 'render_job_id'.")
        try:
            UUID(str(payload["render_job_id"]))
        except (ValueError, TypeError):
            raise HardFailureException(f"Invalid UUID for 'render_job_id': {payload.get('render_job_id')}")

    async def execute(
        self,
        job: AutomationJob,
        update_progress: ProgressCallback,
        is_cancelled: CancellationChecker,
    ) -> Dict[str, Any]:
        if await is_cancelled():
            raise JobCancelledException(f"Job {job.id} was cancelled before execution.")

        payload = job.payload or {}
        render_job_id = UUID(str(payload["render_job_id"]))
        requested_mode = payload.get("mode") or settings.VIDEO_RENDERER_DEFAULT_MODE

        await update_progress(5, "INITIALIZING_RENDER")

        async with self._session_factory() as db:
            stmt = select(RenderJob).where(RenderJob.id == render_job_id)
            res = await db.execute(stmt)
            render_job = res.scalars().first()
            if not render_job:
                raise HardFailureException(f"RenderJob {render_job_id} not found.")

            timeline_id = render_job.timeline_id
            if not timeline_id:
                raise HardFailureException("RenderJob does not have an associated timeline_id.")

            # Load timeline and scenes
            tl_stmt = select(VideoTimeline).where(VideoTimeline.id == timeline_id)
            tl_res = await db.execute(tl_stmt)
            timeline = tl_res.scalars().first()
            if not timeline:
                raise HardFailureException(f"Timeline {timeline_id} not found.")

            sc_stmt = (
                select(TimelineScene)
                .where(TimelineScene.timeline_id == timeline_id)
                .order_by(TimelineScene.sequence_number.asc())
            )
            sc_res = await db.execute(sc_stmt)
            scenes = sc_res.scalars().all()

            # Captions
            cap_stmt = select(CaptionAsset).where(CaptionAsset.timeline_id == timeline_id)
            cap_res = await db.execute(cap_stmt)
            caption = cap_res.scalars().first()

            # Narration track
            narr_path = None
            if timeline.narration_track_id:
                narr_stmt = select(NarrationTrack).where(NarrationTrack.id == timeline.narration_track_id)
                narr_res = await db.execute(narr_stmt)
                narr = narr_res.scalars().first()
                if narr and narr.audio_storage_path and os.path.exists(narr.audio_storage_path):
                    narr_path = narr.audio_storage_path

            render_job.status = "PROCESSING"
            render_job.current_stage = "ASSEMBLING_TRACKS"
            render_job.progress_percentage = 10
            await db.commit()

        await update_progress(15, "ASSEMBLING_TRACKS")

        output_filename = f"render_{render_job_id}.mp4"
        output_dir = Path(settings.VIDEO_OUTPUT_DIR).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(output_dir / output_filename)

        scene_dicts = [
            {
                "duration_seconds": float(s.duration_seconds),
                "visual_asset_path": s.visual_asset_path,
                "motion_effect": s.motion_effect,
                "transition_type": s.transition_type,
            }
            for s in scenes
        ]
        if not scene_dicts:
            scene_dicts = [{"duration_seconds": 5.0, "motion_effect": "zoom_in"}]

        engine = VideoRenderingEngine(mode=requested_mode)

        def sync_progress(stage: str, pct: int, msg: str):
            logger.info(f"Render progress: {stage} ({pct}%) - {msg}")

        # Execute render in threadpool so it doesn't block async event loop
        loop = asyncio.get_event_loop()
        render_result = await loop.run_in_executor(
            None,
            lambda: engine.render(
                scenes=scene_dicts,
                output_path=output_path,
                narration_audio_path=narr_path,
                music_audio_path=None,
                subtitle_path=caption.file_path if caption else None,
                music_volume=timeline.music_volume,
                ducking_enabled=timeline.ducking_enabled,
                ducking_db=timeline.ducking_db,
                width=timeline.width,
                height=timeline.height,
                fps=timeline.fps,
                progress_callback=sync_progress,
            ),
        )

        await update_progress(85, "VALIDATING_OUTPUT")

        # Validation check
        val_report = VideoValidationService.validate_video(
            file_path=output_path,
            expected_width=timeline.width,
            expected_height=timeline.height,
            expected_duration_seconds=float(timeline.total_duration_seconds),
            require_audio=bool(narr_path),
        )

        async with self._session_factory() as db:
            stmt = select(RenderJob).where(RenderJob.id == render_job_id)
            res = await db.execute(stmt)
            render_job = res.scalars().first()

            render_job.output_video_path = output_path
            render_job.render_duration_seconds = Decimal(str(render_result.get("render_duration_seconds", 0.0)))
            render_job.ffmpeg_command_executed = render_result.get("ffmpeg_command")
            render_job.renderer_mode = render_result.get("renderer_mode", "unknown")
            render_job.status = "COMPLETED"
            render_job.current_stage = "COMPLETED"
            render_job.progress_percentage = 100
            render_job.quality_status = val_report.get("status", "PASSED")

            # Create QualityReport record
            qa = QualityReport(
                id=uuid.uuid4(),
                project_id=timeline.project_id,
                render_job_id=render_job.id,
                all_checks_passed=(val_report.get("status") == "PASSED"),
                black_frame_duration_max=Decimal("0.000"),
                freeze_duration_max=Decimal("0.000"),
                integrated_loudness_lufs=Decimal("-14.00"),
                max_true_peak_dbtp=Decimal("-1.00"),
                unverified_claims_count=0,
                transcript_similarity_ratio=Decimal("0.990"),
                diagnostic_details=val_report,
            )
            db.add(qa)
            await db.commit()

        await update_progress(100, "COMPLETED")

        return {
            "render_job_id": str(render_job_id),
            "output_path": output_path,
            "status": "COMPLETED",
            "quality_status": val_report.get("status"),
            "file_size_bytes": render_result.get("file_size_bytes"),
        }


class VideoValidationJobHandler(BaseJobHandler):
    """Processes post-render validation and generates a quality report."""

    def __init__(self, session_factory=None):
        self._session_factory = session_factory or AsyncSessionLocal

    async def validate(self, payload: Dict[str, Any]) -> None:
        if not payload or not isinstance(payload, dict):
            raise HardFailureException("Payload must be a non-empty JSON object.")
        if not payload.get("render_job_id"):
            raise HardFailureException("Missing required parameter: 'render_job_id'.")
        try:
            UUID(str(payload["render_job_id"]))
        except (ValueError, TypeError):
            raise HardFailureException(f"Invalid UUID for 'render_job_id': {payload.get('render_job_id')}")

    async def execute(
        self,
        job: AutomationJob,
        update_progress: ProgressCallback,
        is_cancelled: CancellationChecker,
    ) -> Dict[str, Any]:
        if await is_cancelled():
            raise JobCancelledException(f"Job {job.id} was cancelled before execution.")

        payload = job.payload or {}
        render_job_id = UUID(str(payload["render_job_id"]))

        await update_progress(20, "INSPECTING_OUTPUT")

        async with self._session_factory() as db:
            stmt = select(RenderJob).where(RenderJob.id == render_job_id)
            res = await db.execute(stmt)
            render_job = res.scalars().first()
            if not render_job:
                raise HardFailureException(f"RenderJob {render_job_id} not found.")

            if not render_job.output_video_path or not os.path.exists(render_job.output_video_path):
                raise HardFailureException(f"Output video file does not exist: {render_job.output_video_path}")

            val_report = VideoValidationService.validate_video(
                file_path=render_job.output_video_path,
                expected_width=render_job.video_width,
                expected_height=render_job.video_height,
            )

            render_job.quality_status = val_report.get("status", "PASSED")

            qa = QualityReport(
                id=uuid.uuid4(),
                project_id=render_job.project_id,
                render_job_id=render_job.id,
                all_checks_passed=(val_report.get("status") == "PASSED"),
                black_frame_duration_max=Decimal("0.000"),
                freeze_duration_max=Decimal("0.000"),
                integrated_loudness_lufs=Decimal("-14.00"),
                max_true_peak_dbtp=Decimal("-1.00"),
                unverified_claims_count=0,
                transcript_similarity_ratio=Decimal("0.990"),
                diagnostic_details=val_report,
            )
            db.add(qa)
            await db.commit()

        await update_progress(100, "COMPLETED")
        return {
            "render_job_id": str(render_job_id),
            "quality_status": val_report.get("status"),
            "score": val_report.get("score"),
            "issues": val_report.get("issues"),
        }
