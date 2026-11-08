"""Publication Package model for assembling verified video, thumbnail, and metadata."""

from sqlalchemy import Column, String, ForeignKey, JSON
from sqlalchemy.types import Uuid
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.models.base import UUIDPrimaryKeyMixin, TimestampMixin


class PublicationPackage(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Immutable production bundle linking rendered video, approved thumbnail, and SEO metadata."""

    __tablename__ = "publication_packages"

    project_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("video_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    render_job_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("render_jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    thumbnail_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("thumbnails.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    metadata_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("video_metadata_drafts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status = Column(String(32), default="DRAFT", nullable=False, index=True)  # DRAFT, READY_FOR_QA, APPROVED
    package_manifest = Column(JSON, default=dict, nullable=False)

    # Relationships
    project = relationship("VideoProject", back_populates="publication_packages")
    render_job = relationship("RenderJob", lazy="selectin")
    thumbnail = relationship("Thumbnail", lazy="selectin")
    metadata_draft = relationship("VideoMetadataDraft", lazy="selectin")
    qa_runs = relationship("QARun", back_populates="publication_package", cascade="all, delete-orphan")
