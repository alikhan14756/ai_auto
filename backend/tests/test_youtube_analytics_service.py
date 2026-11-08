"""Automated unit tests for YouTube Analytics API Service, Mock Client, and Snapshot Synchronization."""

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
    ChannelAnalyticsSnapshot,
    VideoAnalyticsSnapshot,
    AudienceRetentionSnapshot,
    TrafficSourceSnapshot,
    AnalyticsSyncRun,
)
from app.services.youtube.constants import (
    YOUTUBE_ANALYTICS_READONLY_SCOPE,
    YOUTUBE_SCOPES,
    CONTENT_LONG_FORM,
    CONTENT_SHORTS,
    FRESHNESS_FRESH,
)
from app.services.youtube.mock_client import mock_youtube_client
from app.services.youtube.analytics_service import YouTubeAnalyticsService


@pytest_asyncio.fixture
async def async_db():
    """Create in-memory SQLite engine for fast, isolated test execution."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def test_channel(async_db: AsyncSession):
    """Seed test user and channel."""
    user = User(
        id=uuid.uuid4(),
        supabase_user_id="sub_user_analytics_01",
        email="creator_analytics@example.com",
        full_name="Analytics Tester",
        role="CREATOR",
    )
    async_db.add(user)
    await async_db.flush()

    channel = Channel(
        id=uuid.uuid4(),
        user_id=user.id,
        youtube_channel_id="UC_test_analytics_channel_01",
        title="AI Engineering Studio",
        description="Autonomous testing channel",
        subscriber_count=48500,
        oauth_refresh_token_encrypted="mock_encrypted_refresh_token",
        is_active=True,
    )
    async_db.add(channel)
    await async_db.flush()

    settings = ChannelSettings(
        channel_id=channel.id,
        niche_keywords=["AI", "Python", "Automation"],
        topic_retention_weights={"AI Tools": 1.15},
    )
    async_db.add(settings)
    await async_db.commit()
    await async_db.refresh(channel)
    return channel


def test_youtube_analytics_scope_configuration():
    """Verify official yt-analytics.readonly scope is included in authorized scopes."""
    assert YOUTUBE_ANALYTICS_READONLY_SCOPE in YOUTUBE_SCOPES
    assert YOUTUBE_ANALYTICS_READONLY_SCOPE == "https://www.googleapis.com/auth/yt-analytics.readonly"


@pytest.mark.asyncio
async def test_mock_youtube_client_query_reports():
    """Test mock client reports for channel daily trends and video breakdowns."""
    mock_youtube_client.reset()

    # Daily trends
    res_daily = await mock_youtube_client.query_reports(
        access_token="mock_token",
        start_date="2026-11-01",
        end_date="2026-11-07",
        metrics="views,estimatedMinutesWatched",
        dimensions="day",
    )
    assert res_daily["kind"] == "youtubeAnalytics#resultTable"
    assert len(res_daily["rows"]) == 7
    assert res_daily["rows"][0][0] == "2026-11-01"

    # Video breakdown
    res_vids = await mock_youtube_client.query_reports(
        access_token="mock_token",
        start_date="2026-11-01",
        end_date="2026-11-07",
        metrics="views",
        dimensions="video",
    )
    assert len(res_vids["rows"]) >= 3
    assert any("shorts" in r[0] for r in res_vids["rows"])


@pytest.mark.asyncio
async def test_mock_youtube_client_retention_curve():
    """Test mock client 100-point retention curve generator and 30s hook value."""
    ret_long = await mock_youtube_client.query_video_retention("mock_token", "mock_vid_ai_agents_101")
    assert len(ret_long["relative_retention_points"]) == 100
    assert ret_long["relative_retention_points"][0]["ratio"] == 0.01
    assert ret_long["retention_at_30s"] >= 0.65

    ret_shorts = await mock_youtube_client.query_video_retention("mock_token", "mock_vid_shorts_cursor_trick")
    assert ret_shorts["retention_at_30s"] >= 0.80  # Shorts hook retention benchmark


@pytest.mark.asyncio
async def test_sync_channel_daily_snapshots(async_db: AsyncSession, test_channel: Channel):
    """Test fetching and upserting daily channel snapshots."""
    snaps = await YouTubeAnalyticsService.sync_channel_daily_snapshots(
        db=async_db,
        channel=test_channel,
        start_date="2026-11-01",
        end_date="2026-11-07",
    )
    assert len(snaps) == 7
    assert snaps[0].views > 0
    assert snaps[0].channel_id == test_channel.id
    assert snaps[0].freshness_status == FRESHNESS_FRESH

    # Verify idempotency / upsert without duplicate errors
    snaps_repeat = await YouTubeAnalyticsService.sync_channel_daily_snapshots(
        db=async_db,
        channel=test_channel,
        start_date="2026-11-01",
        end_date="2026-11-07",
    )
    assert len(snaps_repeat) == 7

    res = await async_db.execute(select(ChannelAnalyticsSnapshot))
    total_stored = res.scalars().all()
    assert len(total_stored) == 7


@pytest.mark.asyncio
async def test_sync_video_snapshots_and_classification(async_db: AsyncSession, test_channel: Channel):
    """Test video snapshot ingestion and Long-form vs Shorts classification."""
    vid_snaps = await YouTubeAnalyticsService.sync_video_snapshots(
        db=async_db,
        channel=test_channel,
        start_date="2026-11-01",
        end_date="2026-11-07",
    )
    assert len(vid_snaps) >= 3

    shorts_found = any(v.content_type == CONTENT_SHORTS for v in vid_snaps)
    long_found = any(v.content_type == CONTENT_LONG_FORM for v in vid_snaps)
    assert shorts_found is True
    assert long_found is True


@pytest.mark.asyncio
async def test_run_full_sync_audit_run(async_db: AsyncSession, test_channel: Channel):
    """Test complete sync pipeline and AnalyticsSyncRun audit logging."""
    sync_run = await YouTubeAnalyticsService.run_full_sync(
        db=async_db,
        channel=test_channel,
        start_date="2026-11-01",
        end_date="2026-11-07",
    )
    assert sync_run.status == "SUCCESS"
    assert sync_run.records_synced > 0
    assert sync_run.duration_ms >= 0
    assert sync_run.channel_id == test_channel.id
