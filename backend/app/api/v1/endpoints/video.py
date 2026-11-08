"""FastAPI Endpoints for Video Timelines, Automated Editing & FFmpeg Rendering."""

import os
import uuid
from decimal import Decimal
from pathlib import Path
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.project import VideoProject
from app.models.channel import Channel
from app.models.storyboard import Storyboard
from app.models.scene import Scene
from app.models.voice import NarrationTrack
from app.models.timeline import VideoTimeline, TimelineScene, CaptionAsset
from app.models.render import RenderJob
from app.models.qa import QualityReport
from app.services.video.subtitles import SubtitleCompiler
from app.services.job_queue import JobQueueService
from app.schemas.video import (
    VideoTimelineResponse,
    TimelineSceneResponse,
    TimelineSceneUpdate,
    SceneReorderRequest,
    TimelineCreateRequest,
    RenderTriggerRequest,
    RenderJobResponse,
    QualityReportResponse,
)

router = APIRouter(prefix="/video", tags=["Video Studio & Automated Editing"])


async def _verify_project_ownership(db: AsyncSession, project_id: UUID, user: User) -> VideoProject:
    """Verify that current user owns the project via channel membership."""
    stmt = (
        select(VideoProject)
        .join(Channel, VideoProject.channel_id == Channel.id)
        .where(VideoProject.id == project_id)
    )
    if user.role != "SUPER_ADMIN":
        stmt = stmt.where(Channel.user_id == user.id)

    res = await db.execute(stmt)
    project = res.scalars().first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or access denied.",
        )
    return project


async def _verify_timeline_ownership(db: AsyncSession, timeline_id: UUID, user: User) -> VideoTimeline:
    """Verify that current user owns the timeline."""
    stmt = (
        select(VideoTimeline)
        .join(VideoProject, VideoTimeline.project_id == VideoProject.id)
        .join(Channel, VideoProject.channel_id == Channel.id)
        .where(VideoTimeline.id == timeline_id)
        .options(
            selectinload(VideoTimeline.timeline_scenes),
            selectinload(VideoTimeline.captions),
        )
    )
    if user.role != "SUPER_ADMIN":
        stmt = stmt.where(Channel.user_id == user.id)

    res = await db.execute(stmt)
    timeline = res.scalars().first()
    if not timeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Timeline not found or access denied.",
        )
    return timeline


async def _verify_render_ownership(db: AsyncSession, render_id: UUID, user: User) -> RenderJob:
    """Verify that current user owns the render job."""
    stmt = (
        select(RenderJob)
        .join(VideoProject, RenderJob.project_id == VideoProject.id)
        .join(Channel, VideoProject.channel_id == Channel.id)
        .where(RenderJob.id == render_id)
    )
    if user.role != "SUPER_ADMIN":
        stmt = stmt.where(Channel.user_id == user.id)

    res = await db.execute(stmt)
    render_job = res.scalars().first()
    if not render_job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Render job not found or access denied.",
        )
    return render_job


@router.post("/timelines", response_model=VideoTimelineResponse, status_code=status.HTTP_201_CREATED)
async def create_timeline_from_storyboard(
    request: TimelineCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Compile a new multitrack video timeline from an approved storyboard."""
    # Verify storyboard existence and project ownership
    sb_stmt = select(Storyboard).where(Storyboard.id == request.storyboard_id)
    sb_res = await db.execute(sb_stmt)
    storyboard = sb_res.scalars().first()
    if not storyboard:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Storyboard not found.",
        )

    await _verify_project_ownership(db, storyboard.project_id, current_user)

    target_aspect = request.aspect_ratio or storyboard.aspect_ratio or "16:9"
    width, height = (1080, 1920) if target_aspect == "9:16" else (1920, 1080)

    # Query latest narration track if not explicit
    narration_track_id = storyboard.narration_track_id
    if not narration_track_id:
        nt_stmt = (
            select(NarrationTrack.id)
            .where(NarrationTrack.project_id == storyboard.project_id)
            .order_by(NarrationTrack.created_at.desc())
        )
        nt_res = await db.execute(nt_stmt)
        narration_track_id = nt_res.scalars().first()

    timeline = VideoTimeline(
        id=uuid.uuid4(),
        project_id=storyboard.project_id,
        aspect_ratio=target_aspect,
        fps=request.fps,
        width=width,
        height=height,
        total_duration_seconds=Decimal("0.00"),
        status="READY",
        music_asset_id=request.music_asset_id,
        music_volume=request.music_volume,
        ducking_enabled=request.ducking_enabled,
        ducking_db=-6.0,
        narration_track_id=narration_track_id,
        settings={},
    )
    db.add(timeline)
    await db.flush()

    # Query storyboard scenes
    scenes_stmt = (
        select(Scene)
        .where(Scene.storyboard_id == storyboard.id)
        .order_by(Scene.scene_order.asc())
        .options(selectinload(Scene.selected_asset))
    )
    scenes_res = await db.execute(scenes_stmt)
    scenes = scenes_res.scalars().all()

    current_time = Decimal("0.00")
    subtitle_cues = []

    for seq, sc in enumerate(scenes, start=1):
        dur = sc.duration_seconds if sc.duration_seconds and sc.duration_seconds > 0 else Decimal("5.00")
        start_t = current_time
        end_t = current_time + dur
        current_time = end_t

        asset_path = None
        if sc.selected_asset:
            asset_path = sc.selected_asset.storage_path or sc.selected_asset.preview_url

        tl_scene = TimelineScene(
            id=uuid.uuid4(),
            timeline_id=timeline.id,
            scene_id=sc.id,
            sequence_number=seq,
            start_time_seconds=start_t,
            end_time_seconds=end_t,
            duration_seconds=dur,
            asset_id=sc.selected_asset_id,
            visual_asset_path=asset_path,
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

    # Compile default kinetic captions
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
    return await _verify_timeline_ownership(db, timeline.id, current_user)


@router.get("/timelines/{timeline_id}", response_model=VideoTimelineResponse)
async def get_timeline(
    timeline_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve full video timeline details with sequenced clips and caption assets."""
    return await _verify_timeline_ownership(db, timeline_id, current_user)


@router.get("/projects/{project_id}/timelines", response_model=List[VideoTimelineResponse])
async def list_project_timelines(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all timelines compiled for a specific project."""
    await _verify_project_ownership(db, project_id, current_user)
    stmt = (
        select(VideoTimeline)
        .where(VideoTimeline.project_id == project_id)
        .order_by(VideoTimeline.created_at.desc())
        .options(
            selectinload(VideoTimeline.timeline_scenes),
            selectinload(VideoTimeline.captions),
        )
    )
    res = await db.execute(stmt)
    return res.scalars().all()


@router.patch("/timelines/{timeline_id}/scenes/{scene_id}", response_model=TimelineSceneResponse)
async def update_timeline_scene(
    timeline_id: UUID,
    scene_id: UUID,
    request: TimelineSceneUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update clip duration, transition, motion effect, or media asset with deterministic timing recalculation."""
    timeline = await _verify_timeline_ownership(db, timeline_id, current_user)

    sc_stmt = (
        select(TimelineScene)
        .where(
            TimelineScene.id == scene_id,
            TimelineScene.timeline_id == timeline_id,
        )
    )
    sc_res = await db.execute(sc_stmt)
    sc = sc_res.scalars().first()
    if not sc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Timeline scene clip not found.",
        )

    recalculate_needed = False

    if request.duration_seconds is not None:
        sc.duration_seconds = Decimal(str(round(request.duration_seconds, 2)))
        recalculate_needed = True

    if request.transition_type is not None:
        sc.transition_type = request.transition_type

    if request.motion_effect is not None:
        sc.motion_effect = request.motion_effect

    if request.asset_id is not None:
        sc.asset_id = request.asset_id

    if request.visual_asset_path is not None:
        sc.visual_asset_path = request.visual_asset_path

    if recalculate_needed:
        # Re-query all scenes in sequence and recalculate start/end times
        all_scenes_stmt = (
            select(TimelineScene)
            .where(TimelineScene.timeline_id == timeline_id)
            .order_by(TimelineScene.sequence_number.asc())
        )
        all_res = await db.execute(all_scenes_stmt)
        all_scenes = all_res.scalars().all()

        current_time = Decimal("0.00")
        for s in all_scenes:
            s.start_time_seconds = current_time
            s.end_time_seconds = current_time + s.duration_seconds
            current_time = s.end_time_seconds

        timeline.total_duration_seconds = current_time

    await db.commit()
    await db.refresh(sc)
    return sc


@router.post("/timelines/{timeline_id}/reorder", response_model=VideoTimelineResponse)
async def reorder_timeline_scenes(
    timeline_id: UUID,
    request: SceneReorderRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reorder scenes on a timeline and deterministically recalculate sequential timestamps."""
    timeline = await _verify_timeline_ownership(db, timeline_id, current_user)

    scenes_stmt = select(TimelineScene).where(TimelineScene.timeline_id == timeline_id)
    scenes_res = await db.execute(scenes_stmt)
    scenes = scenes_res.scalars().all()
    scene_map = {s.id: s for s in scenes}

    # Verify all provided IDs exist on this timeline
    for s_id in request.scene_ids:
        if s_id not in scene_map:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Scene ID {s_id} does not belong to this timeline.",
            )

    # Assign new sequence numbers
    current_time = Decimal("0.00")
    for new_seq, s_id in enumerate(request.scene_ids, start=1):
        s = scene_map[s_id]
        s.sequence_number = new_seq
        s.start_time_seconds = current_time
        s.end_time_seconds = current_time + s.duration_seconds
        current_time = s.end_time_seconds

    timeline.total_duration_seconds = current_time
    await db.commit()

    return await _verify_timeline_ownership(db, timeline_id, current_user)


@router.post("/renders", response_model=RenderJobResponse, status_code=status.HTTP_202_ACCEPTED)
@router.post("/render", response_model=RenderJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_render(
    request: RenderTriggerRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Enqueue a video assembly and rendering job onto the persistent queue."""
    timeline_id = request.timeline_id
    if not timeline_id:
        stmt = (
            select(VideoTimeline)
            .join(VideoProject, VideoTimeline.project_id == VideoProject.id)
            .join(Channel, VideoProject.channel_id == Channel.id)
        )
        if current_user.role != "SUPER_ADMIN":
            stmt = stmt.where(Channel.user_id == current_user.id)
        stmt = stmt.order_by(VideoTimeline.created_at.desc())
        res = await db.execute(stmt)
        timeline = res.scalars().first()
        if not timeline:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No video timeline found. Please create a project and timeline before rendering.",
            )
    else:
        timeline = await _verify_timeline_ownership(db, timeline_id, current_user)

    # Fetch project and channel
    proj_stmt = (
        select(VideoProject)
        .where(VideoProject.id == timeline.project_id)
        .options(selectinload(VideoProject.channel))
    )
    proj_res = await db.execute(proj_stmt)
    project = proj_res.scalars().first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")

    chosen_mode = request.mode or request.render_mode or settings.VIDEO_RENDERER_DEFAULT_MODE
    aspect = request.aspect_ratio or timeline.aspect_ratio

    render_job = RenderJob(
        id=uuid.uuid4(),
        project_id=project.id,
        timeline_id=timeline.id,
        resolution=request.resolution or "1080p",
        video_width=timeline.width,
        video_height=timeline.height,
        fps=timeline.fps,
        aspect_ratio=aspect,
        renderer_mode=chosen_mode,
        current_stage="QUEUED",
        progress_percentage=0,
        status="QUEUED",
        quality_status="PENDING",
    )
    db.add(render_job)
    await db.flush()

    # Enqueue into durable AutomationJob queue
    queue_service = JobQueueService(db)
    await queue_service.enqueue_job(
        channel_id=project.channel_id,
        job_type="VIDEO_RENDER",
        payload={
            "render_job_id": str(render_job.id),
            "timeline_id": str(timeline.id),
            "project_id": str(project.id),
            "user_id": str(current_user.id),
            "mode": chosen_mode,
        },
        priority=10,
        idempotency_key=f"render_{render_job.id}",
    )

    await db.commit()
    await db.refresh(render_job)
    logger.info(f"Enqueued render job {render_job.id} for timeline {timeline.id}")
    return render_job


@router.get("/renders/{render_id}", response_model=RenderJobResponse)
async def get_render_status(
    render_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Poll rendering progress, stage, execution metrics, and status."""
    return await _verify_render_ownership(db, render_id, current_user)


@router.get("/projects/{project_id}/renders", response_model=List[RenderJobResponse])
async def list_project_renders(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all render jobs for a specific project."""
    await _verify_project_ownership(db, project_id, current_user)
    stmt = (
        select(RenderJob)
        .where(RenderJob.project_id == project_id)
        .order_by(RenderJob.created_at.desc())
    )
    res = await db.execute(stmt)
    return res.scalars().all()


@router.get("/renders/{render_id}/qa", response_model=QualityReportResponse)
async def get_render_qa(
    render_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve deterministic 14-point pre-publish quality assurance audit report."""
    render_job = await _verify_render_ownership(db, render_id, current_user)

    qa_stmt = select(QualityReport).where(QualityReport.render_job_id == render_job.id)
    qa_res = await db.execute(qa_stmt)
    qa = qa_res.scalars().first()
    if not qa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quality report not yet generated for this render job.",
        )
    return qa


@router.get("/renders/{render_id}/stream")
async def stream_rendered_video(
    render_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Stream rendered video file with tenant authorization and path-traversal prevention."""
    render_job = await _verify_render_ownership(db, render_id, current_user)

    if render_job.status != "COMPLETED" or not render_job.output_video_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Video has not completed rendering.",
        )

    file_path = Path(render_job.output_video_path).resolve()
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rendered video file is missing on storage.",
        )

    # Security check: Ensure file resides in allowed storage directory
    allowed_dir = Path(settings.LOCAL_STORAGE_DIR).resolve()
    renders_dir = Path(settings.VIDEO_OUTPUT_DIR).resolve()
    if not (file_path.is_relative_to(allowed_dir) or file_path.is_relative_to(renders_dir)):
        logger.error(f"Unauthorized file path access blocked: {file_path}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to specified file path is forbidden.",
        )

    return FileResponse(
        path=str(file_path),
        media_type="video/mp4",
        filename=f"creator_studio_{render_job.id}.mp4",
    )
