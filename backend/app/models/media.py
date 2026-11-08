"""Media asset model."""

from sqlalchemy import Column, String, Text, BigInteger, Boolean, ForeignKey, Integer, Numeric
from sqlalchemy.types import Uuid
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.models.base import UUIDPrimaryKeyMixin, TimestampMixin


class MediaAsset(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Visual or auditory asset referenced in a scene, project, or channel library."""

    __tablename__ = "media_assets"

    channel_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("channels.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    project_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("video_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scene_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("scenes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title = Column(String(255), default="Untitled Asset", nullable=False)
    description = Column(Text, nullable=True)
    asset_type = Column(String(32), default="IMAGE", nullable=False)  # VIDEO_CAPTURE, IMAGE, BROLL, CODE_WIDGET
    asset_category = Column(String(64), default="GENERATED", nullable=False)  # GENERATED, EXTERNAL_STOCK, USER_UPLOADED, SCREENSHOT, DIAGRAM, ILLUSTRATION, BROLL
    source_provider = Column(String(64), default="MOCK", nullable=False)  # MOCK, PEXELS, PIXABAY, UNSPLASH, GEMINI_IMAGEN, USER_UPLOAD
    source_url = Column(Text, nullable=True)
    preview_url = Column(Text, nullable=True)
    author_name = Column(String(255), nullable=True)
    author_url = Column(Text, nullable=True)
    license_type = Column(String(64), default="CC0", nullable=False)  # RECORDED_DEMO, CC0, PEXELS_FREE, PIXABAY_FREE, UNSPLASH_FREE, CUSTOM
    license_status = Column(String(64), default="VERIFIED_COMMERCIAL", nullable=False)  # VERIFIED_COMMERCIAL, ATTRIBUTION_REQUIRED, LICENSE_REVIEW_REQUIRED, RESTRICTED
    attribution_text = Column(Text, nullable=True)
    aspect_ratio = Column(String(16), default="16:9", nullable=False)  # 16:9, 9:16, 1:1, CUSTOM
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    mime_type = Column(String(64), default="image/png", nullable=False)
    duration_seconds = Column(Numeric(8, 2), nullable=True)
    storage_path = Column(Text, nullable=False)
    file_size_bytes = Column(BigInteger, default=0, nullable=False)
    sha256_hash = Column(String(64), default="", nullable=False)
    is_verified = Column(Boolean, default=True, nullable=False)
    is_archived = Column(Boolean, default=False, nullable=False)

    # Relationships
    channel = relationship("Channel", back_populates="media_assets")
    project = relationship("VideoProject", back_populates="media_assets")
    scene = relationship("Scene", foreign_keys=[scene_id], back_populates="media_assets")
