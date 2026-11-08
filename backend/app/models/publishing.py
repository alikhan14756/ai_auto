"""Publishing job, YouTube resumable upload session, and published YouTube video models."""

from sqlalchemy import Column, String, Text, BigInteger, Integer, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.types import Uuid
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.models.base import UUIDPrimaryKeyMixin, TimestampMixin


class PublishingJob(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """YouTube upload, scheduled publishing, and metadata dispatch job."""

    __tablename__ = "publishing_jobs"

    project_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("video_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("channels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    publication_package_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("publication_packages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    idempotency_key = Column(String(128), unique=True, nullable=True, index=True)
    scheduled_publish_time = Column(DateTime(timezone=True), nullable=True)
    privacy_status = Column(String(32), default="unlisted", nullable=False)
    synthetic_media_declared = Column(Boolean, default=True, nullable=False)
    self_declared_made_for_kids = Column(Boolean, default=False, nullable=False)
    status = Column(String(32), default="PENDING", nullable=False, index=True)  # PENDING, UPLOADING, COMPLETED, FAILED, CANCELLED
    current_stage = Column(String(64), default="DRAFT", nullable=False)  # DRAFT, QUEUED, UPLOADING, RECOVERING, PROCESSING, SCHEDULED, PUBLISHED, FAILED, CANCELLED

    # Progress and recovery tracking
    bytes_uploaded = Column(BigInteger, default=0, nullable=False)
    total_bytes = Column(BigInteger, default=0, nullable=False)
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=5, nullable=False)
    last_error_code = Column(String(64), nullable=True)
    last_error_message = Column(Text, nullable=True)

    # Publish metadata snapshot
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    tags = Column(JSON, default=list, nullable=False)
    category_id = Column(String(16), default="28", nullable=False)

    # Relationships
    project = relationship("VideoProject", back_populates="publishing_jobs")
    channel = relationship("Channel", back_populates="publishing_jobs")
    publication_package = relationship("PublicationPackage", lazy="selectin")
    upload_session = relationship(
        "YouTubeUploadSession",
        back_populates="publishing_job",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    youtube_video = relationship(
        "YouTubeVideo",
        back_populates="publishing_job",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class YouTubeUploadSession(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Tracks resumable byte-level upload sessions to Google YouTube servers."""

    __tablename__ = "youtube_upload_sessions"

    publishing_job_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("publishing_jobs.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    session_uri_encrypted = Column(Text, nullable=False)
    file_size_bytes = Column(BigInteger, default=0, nullable=False)
    bytes_uploaded = Column(BigInteger, default=0, nullable=False)
    last_byte_offset = Column(BigInteger, default=0, nullable=False)
    chunk_size_bytes = Column(BigInteger, default=8 * 1024 * 1024, nullable=False)  # 8MB chunk default
    status = Column(String(32), default="ACTIVE", nullable=False, index=True)  # ACTIVE, EXPIRED, COMPLETED, ABORTED
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    publishing_job = relationship("PublishingJob", back_populates="upload_session")


class YouTubeVideo(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Published YouTube video record and metrics container."""

    __tablename__ = "youtube_videos"

    publishing_job_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("publishing_jobs.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    project_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("video_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    youtube_video_id = Column(String(64), unique=True, nullable=False, index=True)
    published_video_url = Column(Text, nullable=False)
    view_count = Column(BigInteger, default=0, nullable=False)
    like_count = Column(BigInteger, default=0, nullable=False)
    comment_count = Column(BigInteger, default=0, nullable=False)

    # Relationships
    publishing_job = relationship("PublishingJob", back_populates="youtube_video")
    project = relationship("VideoProject", back_populates="youtube_videos")
    analytics_snapshots = relationship("AnalyticsSnapshot", back_populates="youtube_video", cascade="all, delete-orphan")
