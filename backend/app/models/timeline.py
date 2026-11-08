"""Video Timeline, Timeline Scene, and Caption Asset models for Milestone 09."""

from sqlalchemy import Column, String, Text, ForeignKey, Numeric, Integer, Float, Boolean, JSON
from sqlalchemy.types import Uuid
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.models.base import UUIDPrimaryKeyMixin, TimestampMixin


class VideoTimeline(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Editable multitrack sequencing timeline for a video project."""

    __tablename__ = "video_timelines"

    project_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("video_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    aspect_ratio = Column(String(16), default="16:9", nullable=False)  # "16:9" (1920x1080) or "9:16" (1080x1920)
    fps = Column(Integer, default=30, nullable=False)  # 24, 30, 60
    width = Column(Integer, default=1920, nullable=False)
    height = Column(Integer, default=1080, nullable=False)
    total_duration_seconds = Column(Numeric(8, 2), default=0.00, nullable=False)
    status = Column(String(32), default="DRAFT", nullable=False, index=True)  # DRAFT, READY, RENDERING, COMPLETED, FAILED

    music_asset_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("media_assets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    music_volume = Column(Float, default=0.15, nullable=False)
    ducking_enabled = Column(Boolean, default=True, nullable=False)
    ducking_db = Column(Float, default=-6.0, nullable=False)

    narration_track_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("narration_tracks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    settings = Column(JSON, default=dict, nullable=False)

    # Relationships
    project = relationship("VideoProject", back_populates="timelines")
    timeline_scenes = relationship(
        "TimelineScene",
        back_populates="timeline",
        cascade="all, delete-orphan",
        order_by="TimelineScene.sequence_number",
        lazy="selectin",
    )
    captions = relationship(
        "CaptionAsset",
        back_populates="timeline",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    render_jobs = relationship(
        "RenderJob",
        back_populates="timeline",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    narration_track = relationship("NarrationTrack", lazy="selectin")
    music_asset = relationship("MediaAsset", lazy="selectin")


class TimelineScene(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A visual clip/scene arranged sequentially on a video timeline."""

    __tablename__ = "timeline_scenes"

    timeline_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("video_timelines.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scene_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("scenes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    sequence_number = Column(Integer, nullable=False, index=True)
    start_time_seconds = Column(Numeric(8, 2), nullable=False)
    end_time_seconds = Column(Numeric(8, 2), nullable=False)
    duration_seconds = Column(Numeric(8, 2), nullable=False)

    asset_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("media_assets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    visual_asset_path = Column(Text, nullable=True)

    transition_type = Column(String(32), default="cut", nullable=False)  # cut, fade, dissolve, wipeleft, wiperight
    transition_duration = Column(Numeric(4, 2), default=0.50, nullable=False)

    motion_effect = Column(String(32), default="zoom_in", nullable=False)  # static, zoom_in, zoom_out, pan_left, pan_right
    motion_intensity = Column(Float, default=1.15, nullable=False)

    voiceover_segment_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("voiceovers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    clip_settings = Column(JSON, default=dict, nullable=False)

    # Relationships
    timeline = relationship("VideoTimeline", back_populates="timeline_scenes")
    scene = relationship("Scene", lazy="selectin")
    asset = relationship("MediaAsset", lazy="selectin")
    voiceover = relationship("Voiceover", lazy="selectin")


class CaptionAsset(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Subtitles/captions file and styling configuration attached to a timeline."""

    __tablename__ = "caption_assets"

    timeline_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("video_timelines.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    format = Column(String(16), default="ass", nullable=False)  # ass, srt, vtt
    style_preset = Column(String(32), default="vivid_ember", nullable=False)  # vivid_ember, minimal_white, bold_yellow, neon_cyan
    primary_color = Column(String(16), default="&H00007AFF", nullable=False)
    highlight_color = Column(String(16), default="&H0000FFFF", nullable=False)
    font_name = Column(String(64), default="Arial", nullable=False)
    font_size = Column(Integer, default=48, nullable=False)
    file_path = Column(Text, nullable=True)
    raw_content = Column(Text, nullable=True)
    is_embedded = Column(Boolean, default=True, nullable=False)

    # Relationships
    timeline = relationship("VideoTimeline", back_populates="captions")
