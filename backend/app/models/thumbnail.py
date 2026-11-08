"""Thumbnail variant and layered composition model."""

from sqlalchemy import Column, String, Text, Boolean, ForeignKey, Integer, BigInteger, JSON
from sqlalchemy.types import Uuid
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.models.base import UUIDPrimaryKeyMixin, TimestampMixin


class Thumbnail(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """High-converting layered thumbnail variant and composition record."""

    __tablename__ = "thumbnails"

    project_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("video_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    variant_code = Column(String(16), nullable=False)  # A, B, C
    storage_path = Column(Text, nullable=False)
    headline_text = Column(String(128), nullable=False)
    accent_color_hex = Column(String(16), default="#FF7A00", nullable=False)
    style_preset = Column(String(64), default="modern_tech_editorial", nullable=False)
    width = Column(Integer, default=1280, nullable=False)
    height = Column(Integer, default=720, nullable=False)
    file_size_bytes = Column(BigInteger, default=0, nullable=False)
    format = Column(String(16), default="PNG", nullable=False)
    composition_data = Column(JSON, default=dict, nullable=False)
    concept_data = Column(JSON, default=dict, nullable=False)
    quality_status = Column(String(32), default="PENDING", nullable=False)  # PENDING, PASSED, WARNING, FAILED, NEEDS_REVIEW
    quality_report = Column(JSON, default=dict, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    is_selected = Column(Boolean, default=False, nullable=False)

    # Relationships
    project = relationship("VideoProject", back_populates="thumbnails")
