"""Scene storyboard and sequencing model."""

from sqlalchemy import Column, String, Text, Integer, ForeignKey, Numeric, JSON
from sqlalchemy.types import Uuid
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.models.base import UUIDPrimaryKeyMixin, TimestampMixin


class Scene(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Discrete storyboard unit containing narration, directive, and visual specifications."""

    __tablename__ = "scenes"

    project_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("video_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    storyboard_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("storyboards.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    scene_order = Column(Integer, nullable=False)
    narration_text = Column(Text, nullable=False)
    visual_archetype = Column(String(64), nullable=False)  # BROWSER_CAPTURE, CODE_TERMINAL, INFOGRAPHIC, BROLL
    visual_directive = Column(Text, nullable=False)
    visual_purpose = Column(String(64), default="CONCEPT_EXPLANATION", nullable=False)  # HOOK_ENGAGEMENT, CONCEPT_EXPLANATION, DEMONSTRATION, SUMMARY
    suggested_asset_type = Column(String(64), default="GENERATED_IMAGE", nullable=False)  # SCREENSHOT, SOFTWARE_INTERFACE, CODE_DEMONSTRATION, PRODUCT_IMAGERY, ILLUSTRATION, DIAGRAM, CHART, STOCK_FOOTAGE, BACKGROUND_VISUAL, GENERATED_IMAGE
    search_keywords = Column(JSON, default=list, nullable=False)
    image_prompt = Column(Text, nullable=True)
    transition = Column(String(32), default="CUT", nullable=False)  # CUT, FADE, ZOOM_IN, PAN_RIGHT, SLIDE_LEFT
    review_status = Column(String(32), default="DRAFT", nullable=False)  # DRAFT, SUGGESTED, APPROVED, REJECTED
    target_url = Column(Text, nullable=True)
    duration_seconds = Column(Numeric(6, 2), nullable=False)
    selected_asset_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("media_assets.id", use_alter=True, name="fk_scenes_selected_asset_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Relationships
    project = relationship("VideoProject", back_populates="scenes")
    storyboard = relationship("Storyboard", back_populates="scenes")
    media_assets = relationship("MediaAsset", foreign_keys="MediaAsset.scene_id", back_populates="scene")
    selected_asset = relationship("MediaAsset", foreign_keys=[selected_asset_id], uselist=False)
    voiceover = relationship("Voiceover", back_populates="scene", uselist=False, cascade="all, delete-orphan")
