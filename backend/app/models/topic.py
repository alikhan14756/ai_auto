"""Topic discovery and research source models."""

from sqlalchemy import Column, String, Text, ForeignKey, Numeric, JSON
from sqlalchemy.types import Uuid
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.models.base import UUIDPrimaryKeyMixin, TimestampMixin


class Topic(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Discovered content topic and scoring metadata."""

    __tablename__ = "topics"

    channel_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("channels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(512), nullable=False)
    niche_category = Column(String(128), nullable=False)
    opportunity_score = Column(Numeric(5, 2), nullable=False)
    search_volume_score = Column(Numeric(5, 2), default=0.00, nullable=False)
    competition_score = Column(Numeric(5, 2), default=0.00, nullable=False)
    status = Column(String(32), default="DISCOVERED", nullable=False, index=True)  # DISCOVERED, SELECTED, ARCHIVED
    raw_discovery_payload = Column(JSON, nullable=True)

    # Relationships
    channel = relationship("Channel", back_populates="topics")
    research_sources = relationship("ResearchSource", back_populates="topic", cascade="all, delete-orphan")
    projects = relationship("VideoProject", back_populates="topic")


class ResearchSource(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Factual and reference research sources supporting a topic."""

    __tablename__ = "research_sources"

    topic_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("topics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_url = Column(Text, nullable=False)
    source_title = Column(String(512), nullable=True)
    extracted_summary = Column(Text, nullable=False)
    relevance_score = Column(Numeric(4, 3), default=1.000, nullable=False)

    # Relationships
    topic = relationship("Topic", back_populates="research_sources")
