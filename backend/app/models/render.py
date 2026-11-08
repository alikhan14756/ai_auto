"""Render job model."""

from sqlalchemy import Column, String, Text, ForeignKey, Numeric, Integer
from sqlalchemy.types import Uuid
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.models.base import UUIDPrimaryKeyMixin, TimestampMixin


class RenderJob(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """FFmpeg assembly and rendering execution record."""

    __tablename__ = "render_jobs"

    project_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("video_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    timeline_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("video_timelines.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    resolution = Column(String(32), default="1080p", nullable=False)
    video_width = Column(Integer, default=1920, nullable=False)
    video_height = Column(Integer, default=1080, nullable=False)
    fps = Column(Integer, default=30, nullable=False)
    aspect_ratio = Column(String(16), default="16:9", nullable=False)
    renderer_mode = Column(String(32), default="ffmpeg", nullable=False)  # ffmpeg, mock
    current_stage = Column(String(64), default="INIT", nullable=False)
    progress_percentage = Column(Integer, default=0, nullable=False)

    output_video_path = Column(Text, nullable=True)
    render_duration_seconds = Column(Numeric(8, 2), nullable=True)
    ffmpeg_command_executed = Column(Text, nullable=True)
    status = Column(String(32), default="QUEUED", nullable=False, index=True)  # QUEUED, PROCESSING, COMPLETED, FAILED
    quality_status = Column(String(32), default="PENDING", nullable=False)  # PENDING, PASSED, WARNING, FAILED
    log_tail = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    # Relationships
    project = relationship("VideoProject", back_populates="render_jobs")
    timeline = relationship("VideoTimeline", back_populates="render_jobs")
    quality_reports = relationship("QualityReport", back_populates="render_job", cascade="all, delete-orphan")
