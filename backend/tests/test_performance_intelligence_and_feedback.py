"""Automated tests for Performance Intelligence Engine, deterministic baselines, and topic feedback loop."""

import uuid
import datetime
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.user import User
from app.models.channel import Channel, ChannelSettings
from app.models.analytics import (
    VideoAnalyticsSnapshot,
    PerformanceInsight,
    PerformanceRecommendation,
)
from app.services.analytics.intelligence_engine import PerformanceIntelligenceEngine
from app.services.analytics.feedback_loop import TopicRetentionFeedbackLoop
from app.services.youtube.constants import (
    CONTENT_LONG_FORM,
    CONTENT_SHORTS,
    REC_STATUS_ACCEPTED,
    REC_STATUS_REJECTED,
)


@pytest_asyncio.fixture
async def async_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def test_channel_with_data(async_db: AsyncSession):
    user = User(
        id=uuid.uuid4(),
        supabase_user_id="sub_user_intel_01",
        email="intel_test@example.com",
        full_name="Intelligence Tester",
        role="CREATOR",
    )
    async_db.add(user)
    await async_db.flush()

    channel = Channel(
        id=uuid.uuid4(),
        user_id=user.id,
        youtube_channel_id="UC_intel_test_01",
        title="AI Engineering Intelligence",
        subscriber_count=50000,
        oauth_refresh_token_encrypted="mock_encrypted_refresh_token",
        is_active=True,
    )
    async_db.add(channel)
    await async_db.flush()

    settings = ChannelSettings(
        channel_id=channel.id,
        niche_keywords=["AI Tools", "Developer Productivity"],
        topic_retention_weights={"AI Tools": 1.15, "Developer Productivity": 1.10},
    )
    async_db.add(settings)

    # Seed 4 video snapshots with varied metrics
    now_dt = datetime.datetime.now(datetime.timezone.utc)
    vids = [
        VideoAnalyticsSnapshot(
            channel_id=channel.id,
            youtube_video_id="mock_vid_ai_tools_agents",
            snapshot_date=now_dt,
            views=15000,
            watch_time_minutes=4200.0,
            average_view_duration_seconds=250.0,
            average_view_percentage=58.0,
            click_through_rate=0.085,
            retention_at_30s=0.78,
            content_type=CONTENT_LONG_FORM,
        ),
        VideoAnalyticsSnapshot(
            channel_id=channel.id,
            youtube_video_id="mock_vid_fastapi_worker",
            snapshot_date=now_dt,
            views=5000,
            watch_time_minutes=1500.0,
            average_view_duration_seconds=180.0,
            average_view_percentage=45.0,
            click_through_rate=0.052,
            retention_at_30s=0.62,  # Low hook retention (< 0.65)
            content_type=CONTENT_LONG_FORM,
        ),
        VideoAnalyticsSnapshot(
            channel_id=channel.id,
            youtube_video_id="mock_vid_shorts_cursor",
            snapshot_date=now_dt,
            views=25000,  # Outperforming views
            watch_time_minutes=250.0,
            average_view_duration_seconds=42.0,
            average_view_percentage=82.0,
            click_through_rate=0.092,
            retention_at_30s=0.85,
            content_type=CONTENT_SHORTS,
        ),
    ]
    for v in vids:
        async_db.add(v)

    await async_db.commit()
    await async_db.refresh(channel)
    return channel


@pytest.mark.asyncio
async def test_deterministic_intelligence_analysis(async_db: AsyncSession, test_channel_with_data: Channel):
    """Test deterministic analysis: median calculations, outperformer detection, and hook drop warnings."""
    report = await PerformanceIntelligenceEngine.analyze_channel(async_db, test_channel_with_data.id)

    assert report["status"] == "ANALYSIS_COMPLETE"
    assert report["median_views"] == 15000
    assert report["insights_generated"] > 0
    assert report["recommendations_generated"] > 0

    # Verify insights stored in database
    res = await async_db.execute(select(PerformanceInsight))
    insights = res.scalars().all()
    assert len(insights) >= 2

    # Check for hook drop-off warning
    hook_drop = [i for i in insights if i.insight_type == "RETENTION_DROP"]
    assert len(hook_drop) >= 1
    assert "mock_vid_fastapi_worker" in hook_drop[0].youtube_video_id


@pytest.mark.asyncio
async def test_topic_retention_feedback_loop_rebalance(async_db: AsyncSession, test_channel_with_data: Channel):
    """Test topic weight rebalancing based on category retention."""
    weights = await TopicRetentionFeedbackLoop.rebalance_topic_weights(async_db, test_channel_with_data.id)

    assert "AI Tools" in weights
    assert weights["AI Tools"] >= 1.0  # High-retention topic boosted
    assert weights["AI Tools"] <= 1.30  # Clamped within max multiplier bounds

    # Verify ChannelSettings record was updated on disk
    stmt = select(ChannelSettings).where(ChannelSettings.channel_id == test_channel_with_data.id)
    res = await async_db.execute(stmt)
    settings = res.scalar_one()
    assert settings.topic_retention_weights["AI Tools"] == weights["AI Tools"]


@pytest.mark.asyncio
async def test_recommendation_lifecycle_actions(async_db: AsyncSession, test_channel_with_data: Channel):
    """Test accepting and rejecting strategic recommendations."""
    # Create recommendation
    rec = PerformanceRecommendation(
        channel_id=test_channel_with_data.id,
        recommendation_type="TOPIC_OPPORTUNITY",
        title="Prioritize Autonomous Agent Tutorials",
        explanation="Viewer retention outpaced channel median by 18%.",
        supporting_metrics={"retention_ratio": 1.18},
        confidence_level="HIGH",
        status="NEW",
    )
    async_db.add(rec)
    await async_db.commit()
    await async_db.refresh(rec)

    # Accept recommendation
    accepted = await TopicRetentionFeedbackLoop.accept_recommendation(async_db, rec.id)
    assert accepted.status == REC_STATUS_ACCEPTED
    assert accepted.applied_at is not None

    # Reject recommendation
    rec2 = PerformanceRecommendation(
        channel_id=test_channel_with_data.id,
        recommendation_type="CADENCE",
        title="Test Cadence",
        explanation="Test explanation",
        status="NEW",
    )
    async_db.add(rec2)
    await async_db.commit()
    await async_db.refresh(rec2)

    rejected = await TopicRetentionFeedbackLoop.reject_recommendation(async_db, rec2.id)
    assert rejected.status == REC_STATUS_REJECTED
