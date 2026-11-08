"""Timeline Domain Service for assembling, sequencing, reordering, and compiling video timelines."""

import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.logging import logger
from app.models.channel import Channel
from app.models.project import VideoProject
from app.models.storyboard import Storyboard
from app.models.scene import Scene
from app.models.timeline import VideoTimeline, TimelineScene, CaptionAsset
from app.models.voice import NarrationTrack
from app.models.user import User
from app.services.video.subtitles import SubtitleCompiler


class TimelineService:
    """Manages timeline compilation from storyboards, timing recalculations, and caption synchronization."""

    @classmethod
    async def verify_project_ownership(cls, db: AsyncSession, project_id: uuid.UUID, user: User) -> VideoProject:
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
            raise PermissionError("Access denied or project not found.")
        return project

    @classmethod
    async def verify_timeline_ownership(cls, db: AsyncSession, timeline_id: uuid.UUID, user: User) -> VideoTimeline:
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
            raise PermissionError("Access denied or timeline not found.")
        return timeline

    @classmethod
    async def create_timeline_from_storyboard(
        cls,
        db: AsyncSession,
        storyboard_id: uuid.UUID,
        user: User,
        aspect_ratio: Optional[str] = None,
        fps: int = 30,
        music_asset_id: Optional[uuid.UUID] = None,
        music_volume: float = 0.15,
        ducking_enabled: bool = True,
    ) -> VideoTimeline:
        """Generate a complete multitrack video timeline from an approved storyboard."""
        sb_stmt = select(Storyboard).where(Storyboard.id == storyboard_id)
        sb_res = await db.execute(sb_stmt)
        storyboard = sb_res.scalars().first()
        if not storyboard:
            raise ValueError(f"Storyboard {storyboard_id} not found.")

        await cls.verify_project_ownership(db, storyboard.project_id, user)

        target_aspect = aspect_ratio or storyboard.aspect_ratio or "16:9"
        width, height = (1080, 1920) if target_aspect == "9:16" else (1920, 1080)

        # Fetch narration track if attached
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
            fps=fps,
            width=width,
            height=height,
            total_duration_seconds=Decimal("0.00"),
            status="READY",
            music_asset_id=music_asset_id,
            music_volume=music_volume,
            ducking_enabled=ducking_enabled,
            ducking_db=-6.0,
            narration_track_id=narration_track_id,
            settings={},
        )
        db.add(timeline)
        await db.flush()

        # Query storyboard scenes in sequence
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

            text = sc.narration_text or ""
            if text:
                subtitle_cues.append({
                    "start": float(start_t),
                    "end": float(end_t),
                    "text": text,
                })

        timeline.total_duration_seconds = current_time

        # Compile and attach default ASS captions
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
        return await cls.verify_timeline_ownership(db, timeline.id, user)

    @classmethod
    async def recalculate_timeline(cls, db: AsyncSession, timeline: VideoTimeline) -> Decimal:
        """Deterministically recalculate all scene start and end times in order."""
        tl_stmt = (
            select(TimelineScene)
            .where(TimelineScene.timeline_id == timeline.id)
            .order_by(TimelineScene.sequence_number.asc())
            .options(selectinload(TimelineScene.scene))
        )
        tl_res = await db.execute(tl_stmt)
        tl_scenes = tl_res.scalars().all()

        current_time = Decimal("0.00")
        subtitle_cues = []

        for sc in tl_scenes:
            dur = sc.duration_seconds
            start_t = current_time
            end_t = current_time + dur
            sc.start_time_seconds = start_t
            sc.end_time_seconds = end_t
            current_time = end_t

            text = ""
            if sc.scene:
                text = sc.scene.narration_text or ""
            if text:
                subtitle_cues.append({
                    "start": float(start_t),
                    "end": float(end_t),
                    "text": text,
                })

        timeline.total_duration_seconds = current_time

        # Re-compile captions if present
        cap_stmt = select(CaptionAsset).where(CaptionAsset.timeline_id == timeline.id)
        cap_res = await db.execute(cap_stmt)
        caption = cap_res.scalars().first()

        if caption:
            ass_content = SubtitleCompiler.compile_ass(
                cues=subtitle_cues,
                style_preset=caption.style_preset,
                width=timeline.width,
                height=timeline.height,
            )
            caption.raw_content = ass_content
            if caption.file_path:
                SubtitleCompiler.save_subtitles(ass_content, caption.file_path)

        await db.commit()
        await db.refresh(timeline)
        return current_time

    @classmethod
    async def update_timeline_scene(
        cls,
        db: AsyncSession,
        timeline_id: uuid.UUID,
        timeline_scene_id: uuid.UUID,
        user: User,
        duration_seconds: Optional[float] = None,
        transition_type: Optional[str] = None,
        motion_effect: Optional[str] = None,
        asset_id: Optional[uuid.UUID] = None,
        visual_asset_path: Optional[str] = None,
    ) -> TimelineScene:
        """Update properties of an individual scene on the timeline and recalculate downstream timings."""
        timeline = await cls.verify_timeline_ownership(db, timeline_id, user)

        sc_stmt = (
            select(TimelineScene)
            .where(
                TimelineScene.id == timeline_scene_id,
                TimelineScene.timeline_id == timeline.id,
            )
        )
        sc_res = await db.execute(sc_stmt)
        tl_scene = sc_res.scalars().first()
        if not tl_scene:
            raise ValueError(f"Timeline scene {timeline_scene_id} not found.")

        recalculate_needed = False

        if duration_seconds is not None and duration_seconds > 0:
            tl_scene.duration_seconds = Decimal(str(round(duration_seconds, 2)))
            recalculate_needed = True

        if transition_type is not None:
            tl_scene.transition_type = transition_type

        if motion_effect is not None:
            tl_scene.motion_effect = motion_effect

        if asset_id is not None:
            tl_scene.asset_id = asset_id

        if visual_asset_path is not None:
            tl_scene.visual_asset_path = visual_asset_path

        if recalculate_needed:
            await cls.recalculate_timeline(db, timeline)
        else:
            await db.commit()
            await db.refresh(tl_scene)

        return tl_scene

    @classmethod
    async def reorder_timeline_scenes(
        cls,
        db: AsyncSession,
        timeline_id: uuid.UUID,
        new_scene_order_ids: List[uuid.UUID],
        user: User,
    ) -> VideoTimeline:
        """Reorder timeline scenes according to provided list of IDs and recalculate sequence numbers."""
        timeline = await cls.verify_timeline_ownership(db, timeline_id, user)

        sc_stmt = select(TimelineScene).where(TimelineScene.timeline_id == timeline.id)
        sc_res = await db.execute(sc_stmt)
        scenes = sc_res.scalars().all()
        scene_map = {s.id: s for s in scenes}

        for new_seq, s_id in enumerate(new_scene_order_ids, start=1):
            if s_id in scene_map:
                scene_map[s_id].sequence_number = new_seq

        await db.flush()
        await cls.recalculate_timeline(db, timeline)
        return timeline
