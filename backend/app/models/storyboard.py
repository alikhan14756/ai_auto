"""Storyboard container model."""

from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.types import Uuid
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.models.base import UUIDPrimaryKeyMixin, TimestampMixin


class Storyboard(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Central container organizing storyboard scenes, asset selections, and approval for a video project."""

    __tablename__ = "storyboards"

    project_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("video_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    script_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("scripts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    narration_track_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("narration_tracks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    version = Column(Integer, default=1, nullable=False)
    status = Column(String(32), default="DRAFT", nullable=False)  # DRAFT, IN_REVIEW, APPROVED
    aspect_ratio = Column(String(16), default="16:9", nullable=False)  # 16:9, 9:16
    scene_count = Column(Integer, default=0, nullable=False)
    approved_scene_count = Column(Integer, default=0, nullable=False)

    # Relationships
    project = relationship("VideoProject", back_populates="storyboards")
    script = relationship("Script")
    narration_track = relationship("NarrationTrack")
    scenes = relationship("Scene", back_populates="storyboard", order_by="Scene.scene_order")
