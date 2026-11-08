"""Channel and ChannelSettings models."""

from sqlalchemy import Column, String, Text, BigInteger, Boolean, DateTime, ForeignKey, Numeric, JSON
from sqlalchemy.types import Uuid
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.models.base import UUIDPrimaryKeyMixin, TimestampMixin


class Channel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Connected YouTube Channel workspace."""

    __tablename__ = "channels"

    user_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    youtube_channel_id = Column(String(128), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    custom_url = Column(String(128), nullable=True)
    thumbnail_url = Column(Text, nullable=True)
    subscriber_count = Column(BigInteger, default=0, nullable=False)
    oauth_refresh_token_encrypted = Column(Text, nullable=False)
    token_expires_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    user = relationship("User", back_populates="channels")
    settings = relationship("ChannelSettings", back_populates="channel", uselist=False, cascade="all, delete-orphan")
    topics = relationship("Topic", back_populates="channel", cascade="all, delete-orphan")
    projects = relationship("VideoProject", back_populates="channel", cascade="all, delete-orphan")
    publishing_jobs = relationship("PublishingJob", back_populates="channel", cascade="all, delete-orphan")
    automation_jobs = relationship("AutomationJob", back_populates="channel", cascade="all, delete-orphan")
    provider_usages = relationship("ProviderUsage", back_populates="channel", cascade="all, delete-orphan")
    voice_profiles = relationship("VoiceProfile", back_populates="channel", cascade="all, delete-orphan")
    media_assets = relationship("MediaAsset", back_populates="channel", cascade="all, delete-orphan")
    channel_analytics_snapshots = relationship("ChannelAnalyticsSnapshot", back_populates="channel", cascade="all, delete-orphan")
    video_analytics_snapshots = relationship("VideoAnalyticsSnapshot", back_populates="channel", cascade="all, delete-orphan")
    traffic_source_snapshots = relationship("TrafficSourceSnapshot", back_populates="channel", cascade="all, delete-orphan")
    performance_insights = relationship("PerformanceInsight", back_populates="channel", cascade="all, delete-orphan")
    performance_recommendations = relationship("PerformanceRecommendation", back_populates="channel", cascade="all, delete-orphan")
    analytics_sync_runs = relationship("AnalyticsSyncRun", back_populates="channel", cascade="all, delete-orphan")
    workflow_definitions = relationship("WorkflowDefinition", back_populates="channel", cascade="all, delete-orphan", lazy="selectin")
    workflow_executions = relationship("WorkflowExecution", back_populates="channel", cascade="all, delete-orphan", lazy="selectin")
    workflow_policy = relationship("WorkflowPolicy", back_populates="channel", uselist=False, cascade="all, delete-orphan", lazy="selectin")
    workflow_schedules = relationship("WorkflowSchedule", back_populates="channel", cascade="all, delete-orphan", lazy="selectin")
    resource_usage_records = relationship("ResourceUsageRecord", back_populates="channel", cascade="all, delete-orphan", lazy="selectin")


class ChannelSettings(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Configuration and production parameters for a channel."""

    __tablename__ = "channel_settings"

    channel_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("channels.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    niche_keywords = Column(JSON, default=list, nullable=False)
    default_privacy = Column(String(32), default="unlisted", nullable=False)
    default_category_id = Column(String(16), default="28", nullable=False)  # 28: Science & Technology
    weekly_cadence_long = Column(BigInteger, default=2, nullable=False)
    weekly_cadence_shorts = Column(BigInteger, default=3, nullable=False)
    auto_publish_enabled = Column(Boolean, default=False, nullable=False)
    max_monthly_spend_usd = Column(Numeric(8, 2), default=0.00, nullable=False)
    topic_retention_weights = Column(JSON, default=dict, nullable=False)

    # Relationships
    channel = relationship("Channel", back_populates="settings")
