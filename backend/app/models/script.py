"""Script and ScriptClaim models."""

from sqlalchemy import Column, String, Text, Integer, Boolean, ForeignKey, Numeric
from sqlalchemy.types import Uuid
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.models.base import UUIDPrimaryKeyMixin, TimestampMixin


class Script(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Generated and revised production script."""

    __tablename__ = "scripts"

    project_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("video_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version = Column(Integer, default=1, nullable=False)
    full_text = Column(Text, nullable=False)
    word_count = Column(Integer, nullable=False)
    estimated_duration_seconds = Column(Integer, nullable=False)
    is_locked = Column(Boolean, default=False, nullable=False)

    # Relationships
    project = relationship("VideoProject", back_populates="scripts")
    claims = relationship("ScriptClaim", back_populates="script", cascade="all, delete-orphan")


class ScriptClaim(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Atomic factual claims extracted from scripts for automated verification."""

    __tablename__ = "script_claims"

    script_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("scripts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("video_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    claim_text = Column(Text, nullable=False)
    extracted_entity = Column(String(255), nullable=True)
    claim_type = Column(String(64), nullable=False)  # BENCHMARK, PRICING, RELEASE_DATE, FEATURE
    is_verified = Column(Boolean, default=False, nullable=False)
    confidence_score = Column(Numeric(4, 3), default=0.000, nullable=False)
    citation_url = Column(Text, nullable=True)
    citation_snippet = Column(Text, nullable=True)

    # Relationships
    script = relationship("Script", back_populates="claims")
    project = relationship("VideoProject", back_populates="script_claims")
