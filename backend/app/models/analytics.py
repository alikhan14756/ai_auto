"""YouTube Analytics and Performance Intelligence domain models."""

from sqlalchemy import (
    Column,
    String,
    Text,
    BigInteger,
    Numeric,
    DateTime,
    ForeignKey,
    JSON,
    UniqueConstraint,
)
from sqlalchemy.types import Uuid
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.models.base import UUIDPrimaryKeyMixin, TimestampMixin


class AnalyticsSnapshot(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Periodic performance metrics snapshot captured from YouTube Analytics API (M01 baseline)."""

    __tablename__ = "analytics_snapshots"

    youtube_video_id = Column(
        String(64),
        ForeignKey("youtube_videos.youtube_video_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    snapshot_time = Column(DateTime(timezone=True), nullable=False, index=True)
    views = Column(BigInteger, nullable=False)
    watch_time_minutes = Column(Numeric(10, 2), nullable=False)
    average_view_duration_seconds = Column(Numeric(8, 2), nullable=False)
    click_through_rate = Column(Numeric(5, 4), nullable=False)
    retention_at_30s = Column(Numeric(5, 4), nullable=False)

    # Relationships
    youtube_video = relationship("YouTubeVideo", back_populates="analytics_snapshots")


class ChannelAnalyticsSnapshot(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Daily or periodic channel-level performance snapshot retrieved via YouTube Analytics API."""

    __tablename__ = "channel_analytics_snapshots"

    channel_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("channels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    snapshot_date = Column(DateTime(timezone=True), nullable=False, index=True)
    views = Column(BigInteger, default=0, nullable=False)
    watch_time_minutes = Column(Numeric(12, 2), default=0.0, nullable=False)
    average_view_duration_seconds = Column(Numeric(8, 2), default=0.0, nullable=False)
    average_view_percentage = Column(Numeric(5, 2), default=0.0, nullable=False)
    subscribers_gained = Column(BigInteger, default=0, nullable=False)
    subscribers_lost = Column(BigInteger, default=0, nullable=False)
    net_subscribers = Column(BigInteger, default=0, nullable=False)
    likes = Column(BigInteger, default=0, nullable=False)
    comments = Column(BigInteger, default=0, nullable=False)
    shares = Column(BigInteger, default=0, nullable=False)
    impressions = Column(BigInteger, default=0, nullable=False)
    click_through_rate = Column(Numeric(5, 4), default=0.0, nullable=False)
    freshness_status = Column(String(32), default="FRESH", nullable=False)
    data_completeness = Column(String(32), default="FINAL", nullable=False)
    raw_metrics = Column(JSON, default=dict, nullable=False)

    __table_args__ = (
        UniqueConstraint("channel_id", "snapshot_date", name="uq_channel_analytics_snapshot_date"),
    )

    # Relationships
    channel = relationship("Channel", back_populates="channel_analytics_snapshots")


class VideoAnalyticsSnapshot(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Granular performance metrics snapshot for an individual published YouTube video."""

    __tablename__ = "video_analytics_snapshots"

    channel_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("channels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    youtube_video_id = Column(String(64), nullable=False, index=True)
    snapshot_date = Column(DateTime(timezone=True), nullable=False, index=True)
    views = Column(BigInteger, default=0, nullable=False)
    watch_time_minutes = Column(Numeric(12, 2), default=0.0, nullable=False)
    average_view_duration_seconds = Column(Numeric(8, 2), default=0.0, nullable=False)
    average_view_percentage = Column(Numeric(5, 2), default=0.0, nullable=False)
    likes = Column(BigInteger, default=0, nullable=False)
    comments = Column(BigInteger, default=0, nullable=False)
    shares = Column(BigInteger, default=0, nullable=False)
    subscribers_gained = Column(BigInteger, default=0, nullable=False)
    subscribers_lost = Column(BigInteger, default=0, nullable=False)
    impressions = Column(BigInteger, default=0, nullable=False)
    click_through_rate = Column(Numeric(5, 4), default=0.0, nullable=False)
    retention_at_30s = Column(Numeric(5, 4), default=0.0, nullable=False)
    content_type = Column(String(32), default="LONG_FORM", nullable=False)  # LONG_FORM, SHORTS, UNKNOWN
    freshness_status = Column(String(32), default="FRESH", nullable=False)
    raw_metrics = Column(JSON, default=dict, nullable=False)

    __table_args__ = (
        UniqueConstraint("youtube_video_id", "snapshot_date", name="uq_video_analytics_snapshot_date"),
    )

    # Relationships
    channel = relationship("Channel", back_populates="video_analytics_snapshots")


class AudienceRetentionSnapshot(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Normalized audience retention curve points and drop-off markers for a video."""

    __tablename__ = "audience_retention_snapshots"

    channel_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("channels.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    youtube_video_id = Column(String(64), unique=True, nullable=False, index=True)
    relative_retention_points = Column(JSON, default=list, nullable=False)  # [{"ratio": 0.05, "watch_percentage": 0.88}]
    drop_off_points = Column(JSON, default=list, nullable=False)  # [{"timestamp_sec": 30, "drop_pct": 12.5, "note": "Hook"}]
    average_view_duration_seconds = Column(Numeric(8, 2), default=0.0, nullable=False)
    retention_at_30s = Column(Numeric(5, 4), default=0.0, nullable=False)
    sample_size = Column(BigInteger, default=0, nullable=False)


class TrafficSourceSnapshot(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Breakdown of viewer acquisition channels (Search, Suggested, Browse, etc.)."""

    __tablename__ = "traffic_source_snapshots"

    channel_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("channels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    youtube_video_id = Column(String(64), nullable=True, index=True)
    snapshot_date = Column(DateTime(timezone=True), nullable=False, index=True)
    traffic_source_type = Column(String(64), nullable=False)  # SEARCH, SUGGESTED, BROWSE, EXTERNAL, DIRECT, PLAYLIST, OTHER
    views = Column(BigInteger, default=0, nullable=False)
    estimated_minutes_watched = Column(Numeric(12, 2), default=0.0, nullable=False)
    percentage = Column(Numeric(5, 2), default=0.0, nullable=False)

    # Relationships
    channel = relationship("Channel", back_populates="traffic_source_snapshots")


class PerformanceInsight(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Deterministic or evidence-backed AI performance pattern detected across channel media."""

    __tablename__ = "performance_insights"

    channel_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("channels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    youtube_video_id = Column(String(64), nullable=True, index=True)
    insight_type = Column(String(64), nullable=False)  # VIEW_VELOCITY, RETENTION_DROP, TOPIC_OUTPERFORMANCE, CTR_VARIANCE, CADENCE
    category = Column(String(32), default="CONTENT", nullable=False)  # CONTENT, RETENTION, METADATA, AUDIENCE
    title = Column(String(255), nullable=False)
    explanation = Column(Text, nullable=False)
    evidence_metrics = Column(JSON, default=dict, nullable=False)
    confidence_score = Column(Numeric(4, 2), default=0.85, nullable=False)
    limitations = Column(Text, nullable=True)
    status = Column(String(32), default="ACTIVE", nullable=False)  # ACTIVE, ARCHIVED

    # Relationships
    channel = relationship("Channel", back_populates="performance_insights")


class PerformanceRecommendation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Actionable strategic content recommendation with lifecycle state and feedback tracking."""

    __tablename__ = "performance_recommendations"

    channel_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("channels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recommendation_type = Column(String(64), nullable=False)  # TOPIC_OPPORTUNITY, HOOK_OPTIMIZATION, CADENCE, FORMAT_SELECTION
    title = Column(String(255), nullable=False)
    explanation = Column(Text, nullable=False)
    supporting_metrics = Column(JSON, default=dict, nullable=False)
    suggested_action = Column(JSON, default=dict, nullable=False)
    confidence_level = Column(String(32), default="HIGH", nullable=False)  # HIGH, MEDIUM, LOW
    status = Column(String(32), default="NEW", nullable=False)  # NEW, ACCEPTED, REJECTED, COMPLETED, ARCHIVED
    applied_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    channel = relationship("Channel", back_populates="performance_recommendations")


class AnalyticsSyncRun(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Audit record and execution trace for YouTube Analytics background sync jobs."""

    __tablename__ = "analytics_sync_runs"

    channel_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("channels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sync_type = Column(String(64), default="FULL", nullable=False)  # FULL, CHANNEL, VIDEOS, RETENTION, TRAFFIC
    status = Column(String(32), default="SUCCESS", nullable=False)  # SUCCESS, FAILED, PARTIAL, SYNCING
    records_synced = Column(BigInteger, default=0, nullable=False)
    error_details = Column(Text, nullable=True)
    start_time = Column(DateTime(timezone=True), nullable=False)
    completed_time = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(BigInteger, default=0, nullable=False)

    # Relationships
    channel = relationship("Channel", back_populates="analytics_sync_runs")
