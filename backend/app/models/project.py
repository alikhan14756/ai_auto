"""Video project model."""

from sqlalchemy import Column, String, Integer, ForeignKey, Numeric, DateTime
from sqlalchemy.types import Uuid
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.models.base import UUIDPrimaryKeyMixin, TimestampMixin


class VideoProject(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Central production lifecycle container for a video."""

    __tablename__ = "video_projects"

    channel_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("channels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    topic_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("topics.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title = Column(String(255), nullable=False)
    format = Column(String(32), default="LONG_FORM", nullable=False)  # LONG_FORM, SHORTS
    state = Column(String(64), default="IDEA", nullable=False, index=True)
    target_duration_seconds = Column(Integer, default=480, nullable=False)
    actual_duration_seconds = Column(Numeric(8, 2), nullable=True)
    revision_number = Column(Integer, default=1, nullable=False)
    published_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    channel = relationship("Channel", back_populates="projects")
    topic = relationship("Topic", back_populates="projects")
    scripts = relationship("Script", back_populates="project", cascade="all, delete-orphan")
    script_claims = relationship("ScriptClaim", back_populates="project", cascade="all, delete-orphan")
    scenes = relationship("Scene", back_populates="project", cascade="all, delete-orphan")
    media_assets = relationship("MediaAsset", back_populates="project", cascade="all, delete-orphan")
    voiceovers = relationship("Voiceover", back_populates="project", cascade="all, delete-orphan")
    narration_tracks = relationship("NarrationTrack", back_populates="project", cascade="all, delete-orphan")
    storyboards = relationship("Storyboard", back_populates="project", cascade="all, delete-orphan")
    timelines = relationship("VideoTimeline", back_populates="project", cascade="all, delete-orphan")
    thumbnails = relationship("Thumbnail", back_populates="project", cascade="all, delete-orphan")
    metadata_drafts = relationship("VideoMetadataDraft", back_populates="project", cascade="all, delete-orphan")
    publication_packages = relationship("PublicationPackage", back_populates="project", cascade="all, delete-orphan")
    render_jobs = relationship("RenderJob", back_populates="project", cascade="all, delete-orphan")
    quality_reports = relationship("QualityReport", back_populates="project", cascade="all, delete-orphan")
    qa_runs = relationship("QARun", back_populates="project", cascade="all, delete-orphan")
    publishing_jobs = relationship("PublishingJob", back_populates="project", cascade="all, delete-orphan")
    youtube_videos = relationship("YouTubeVideo", back_populates="project", cascade="all, delete-orphan")
