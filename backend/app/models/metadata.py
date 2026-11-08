"""Video SEO Metadata Draft model for Milestone 10."""

from sqlalchemy import Column, String, Text, ForeignKey, Integer, Float, Boolean, JSON
from sqlalchemy.types import Uuid
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.models.base import UUIDPrimaryKeyMixin, TimestampMixin


class VideoMetadataDraft(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Structured YouTube SEO Metadata draft for a video project."""

    __tablename__ = "video_metadata_drafts"

    project_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("video_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(255), nullable=False)
    title_candidates = Column(JSON, default=list, nullable=False)
    description = Column(Text, nullable=False)
    tags = Column(JSON, default=list, nullable=False)
    hashtags = Column(JSON, default=list, nullable=False)
    chapters = Column(JSON, default=list, nullable=False)
    pinned_comment = Column(Text, nullable=True)
    synthetic_media_disclosure = Column(Boolean, default=True, nullable=False)
    seo_score = Column(Float, default=0.0, nullable=False)
    seo_report = Column(JSON, default=dict, nullable=False)
    pairing_score = Column(Float, default=0.0, nullable=False)
    pairing_report = Column(JSON, default=dict, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    is_approved = Column(Boolean, default=False, nullable=False)

    # Relationships
    project = relationship("VideoProject", back_populates="metadata_drafts")
