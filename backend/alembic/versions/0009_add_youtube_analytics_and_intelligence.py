"""Add YouTube analytics, retention, traffic sources, insights, and recommendations.

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-08 04:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. channel_analytics_snapshots
    op.create_table(
        "channel_analytics_snapshots",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("channel_id", sa.Uuid(), sa.ForeignKey("channels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("snapshot_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("views", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("watch_time_minutes", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0.0"),
        sa.Column("average_view_duration_seconds", sa.Numeric(precision=8, scale=2), nullable=False, server_default="0.0"),
        sa.Column("average_view_percentage", sa.Numeric(precision=5, scale=2), nullable=False, server_default="0.0"),
        sa.Column("subscribers_gained", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("subscribers_lost", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("net_subscribers", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("likes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("comments", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("shares", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("impressions", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("click_through_rate", sa.Numeric(precision=5, scale=4), nullable=False, server_default="0.0"),
        sa.Column("freshness_status", sa.String(length=32), nullable=False, server_default="FRESH"),
        sa.Column("data_completeness", sa.String(length=32), nullable=False, server_default="FINAL"),
        sa.Column("raw_metrics", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("channel_id", "snapshot_date", name="uq_channel_analytics_snapshot_date"),
    )
    op.create_index("ix_channel_analytics_snapshots_channel_id", "channel_analytics_snapshots", ["channel_id"])
    op.create_index("ix_channel_analytics_snapshots_snapshot_date", "channel_analytics_snapshots", ["snapshot_date"])

    # 2. video_analytics_snapshots
    op.create_table(
        "video_analytics_snapshots",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("channel_id", sa.Uuid(), sa.ForeignKey("channels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("youtube_video_id", sa.String(length=64), nullable=False),
        sa.Column("snapshot_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("views", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("watch_time_minutes", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0.0"),
        sa.Column("average_view_duration_seconds", sa.Numeric(precision=8, scale=2), nullable=False, server_default="0.0"),
        sa.Column("average_view_percentage", sa.Numeric(precision=5, scale=2), nullable=False, server_default="0.0"),
        sa.Column("likes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("comments", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("shares", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("subscribers_gained", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("subscribers_lost", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("impressions", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("click_through_rate", sa.Numeric(precision=5, scale=4), nullable=False, server_default="0.0"),
        sa.Column("retention_at_30s", sa.Numeric(precision=5, scale=4), nullable=False, server_default="0.0"),
        sa.Column("content_type", sa.String(length=32), nullable=False, server_default="LONG_FORM"),
        sa.Column("freshness_status", sa.String(length=32), nullable=False, server_default="FRESH"),
        sa.Column("raw_metrics", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("youtube_video_id", "snapshot_date", name="uq_video_analytics_snapshot_date"),
    )
    op.create_index("ix_video_analytics_snapshots_channel_id", "video_analytics_snapshots", ["channel_id"])
    op.create_index("ix_video_analytics_snapshots_youtube_video_id", "video_analytics_snapshots", ["youtube_video_id"])
    op.create_index("ix_video_analytics_snapshots_snapshot_date", "video_analytics_snapshots", ["snapshot_date"])

    # 3. audience_retention_snapshots
    op.create_table(
        "audience_retention_snapshots",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("channel_id", sa.Uuid(), sa.ForeignKey("channels.id", ondelete="CASCADE"), nullable=True),
        sa.Column("youtube_video_id", sa.String(length=64), nullable=False),
        sa.Column("relative_retention_points", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("drop_off_points", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("average_view_duration_seconds", sa.Numeric(precision=8, scale=2), nullable=False, server_default="0.0"),
        sa.Column("retention_at_30s", sa.Numeric(precision=5, scale=4), nullable=False, server_default="0.0"),
        sa.Column("sample_size", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audience_retention_snapshots_youtube_video_id", "audience_retention_snapshots", ["youtube_video_id"], unique=True)
    op.create_index("ix_audience_retention_snapshots_channel_id", "audience_retention_snapshots", ["channel_id"])

    # 4. traffic_source_snapshots
    op.create_table(
        "traffic_source_snapshots",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("channel_id", sa.Uuid(), sa.ForeignKey("channels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("youtube_video_id", sa.String(length=64), nullable=True),
        sa.Column("snapshot_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("traffic_source_type", sa.String(length=64), nullable=False),
        sa.Column("views", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("estimated_minutes_watched", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0.0"),
        sa.Column("percentage", sa.Numeric(precision=5, scale=2), nullable=False, server_default="0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_traffic_source_snapshots_channel_id", "traffic_source_snapshots", ["channel_id"])
    op.create_index("ix_traffic_source_snapshots_youtube_video_id", "traffic_source_snapshots", ["youtube_video_id"])
    op.create_index("ix_traffic_source_snapshots_snapshot_date", "traffic_source_snapshots", ["snapshot_date"])

    # 5. performance_insights
    op.create_table(
        "performance_insights",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("channel_id", sa.Uuid(), sa.ForeignKey("channels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("youtube_video_id", sa.String(length=64), nullable=True),
        sa.Column("insight_type", sa.String(length=64), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False, server_default="CONTENT"),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("evidence_metrics", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("confidence_score", sa.Numeric(precision=4, scale=2), nullable=False, server_default="0.85"),
        sa.Column("limitations", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_performance_insights_channel_id", "performance_insights", ["channel_id"])
    op.create_index("ix_performance_insights_youtube_video_id", "performance_insights", ["youtube_video_id"])

    # 6. performance_recommendations
    op.create_table(
        "performance_recommendations",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("channel_id", sa.Uuid(), sa.ForeignKey("channels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("recommendation_type", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("supporting_metrics", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("suggested_action", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("confidence_level", sa.String(length=32), nullable=False, server_default="HIGH"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="NEW"),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_performance_recommendations_channel_id", "performance_recommendations", ["channel_id"])

    # 7. analytics_sync_runs
    op.create_table(
        "analytics_sync_runs",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("channel_id", sa.Uuid(), sa.ForeignKey("channels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sync_type", sa.String(length=64), nullable=False, server_default="FULL"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="SUCCESS"),
        sa.Column("records_synced", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("error_details", sa.Text(), nullable=True),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_analytics_sync_runs_channel_id", "analytics_sync_runs", ["channel_id"])


def downgrade() -> None:
    op.drop_table("analytics_sync_runs")
    op.drop_table("performance_recommendations")
    op.drop_table("performance_insights")
    op.drop_table("traffic_source_snapshots")
    op.drop_table("audience_retention_snapshots")
    op.drop_table("video_analytics_snapshots")
    op.drop_table("channel_analytics_snapshots")
