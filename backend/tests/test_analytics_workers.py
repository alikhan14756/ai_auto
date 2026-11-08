"""Automated unit tests for YouTube Analytics Worker Handlers."""

import uuid
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.user import User
from app.models.channel import Channel, ChannelSettings
from app.models.job import AutomationJob
from app.workers.registry import registry
from app.workers.handlers.analytics import (
    YouTubeChannelAnalyticsSyncJobHandler,
    YouTubeVideoAnalyticsSyncJobHandler,
    YouTubeRetentionAnalyticsSyncJobHandler,
    YouTubeTrafficAnalyticsSyncJobHandler,
    YouTubeAnalyticsReconciliationJobHandler,
)


@pytest_asyncio.fixture
async def async_db_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield session_factory
    await engine.dispose()


@pytest_asyncio.fixture
async def seeded_channel(async_db_factory):
    async with async_db_factory() as db:
        user = User(
            id=uuid.uuid4(),
            supabase_user_id="sub_worker_tester",
            email="worker_tester@example.com",
            full_name="Worker Tester",
            role="CREATOR",
        )
        db.add(user)
        await db.flush()

        channel = Channel(
            id=uuid.uuid4(),
            user_id=user.id,
            youtube_channel_id="UC_worker_channel_01",
            title="Worker Channel",
            oauth_refresh_token_encrypted="mock_encrypted_refresh",
            is_active=True,
        )
        db.add(channel)
        await db.flush()

        settings = ChannelSettings(
            channel_id=channel.id,
            niche_keywords=["AI"],
        )
        db.add(settings)
        await db.commit()
        return channel


@pytest.mark.asyncio
async def test_analytics_handlers_registered_in_registry():
    """Verify all 5 analytics sync job types are registered in JobHandlerRegistry."""
    assert isinstance(registry.get_handler("YOUTUBE_CHANNEL_ANALYTICS_SYNC"), YouTubeChannelAnalyticsSyncJobHandler)
    assert isinstance(registry.get_handler("YOUTUBE_VIDEO_ANALYTICS_SYNC"), YouTubeVideoAnalyticsSyncJobHandler)
    assert isinstance(registry.get_handler("YOUTUBE_RETENTION_ANALYTICS_SYNC"), YouTubeRetentionAnalyticsSyncJobHandler)
    assert isinstance(registry.get_handler("YOUTUBE_TRAFFIC_ANALYTICS_SYNC"), YouTubeTrafficAnalyticsSyncJobHandler)
    assert isinstance(registry.get_handler("YOUTUBE_ANALYTICS_RECONCILIATION"), YouTubeAnalyticsReconciliationJobHandler)


@pytest.mark.asyncio
async def test_youtube_channel_analytics_sync_worker(async_db_factory, seeded_channel: Channel):
    """Test YouTubeChannelAnalyticsSyncJobHandler execute."""
    handler = YouTubeChannelAnalyticsSyncJobHandler(session_factory=async_db_factory)

    job = AutomationJob(
        id=uuid.uuid4(),
        channel_id=seeded_channel.id,
        job_type="YOUTUBE_CHANNEL_ANALYTICS_SYNC",
        payload={
            "channel_id": str(seeded_channel.id),
            "start_date": "2026-11-01",
            "end_date": "2026-11-07",
        },
        idempotency_key="worker_test_sync_01",
    )

    progress_reports = []
    async def progress_cb(pct: int, msg: str):
        progress_reports.append((pct, msg))

    async def cancel_check():
        return False

    await handler.validate(job.payload)
    result = await handler.execute(job, progress_cb, cancel_check)

    assert result["snapshots_synced"] == 7
    assert len(progress_reports) >= 2


@pytest.mark.asyncio
async def test_youtube_reconciliation_worker(async_db_factory, seeded_channel: Channel):
    """Test YouTubeAnalyticsReconciliationJobHandler execute."""
    handler = YouTubeAnalyticsReconciliationJobHandler(session_factory=async_db_factory)

    job = AutomationJob(
        id=uuid.uuid4(),
        channel_id=seeded_channel.id,
        job_type="YOUTUBE_ANALYTICS_RECONCILIATION",
        payload={"channel_id": str(seeded_channel.id)},
        idempotency_key="worker_test_reconcile_01",
    )

    async def progress_cb(pct: int, msg: str):
        pass

    async def cancel_check():
        return False

    await handler.validate(job.payload)
    result = await handler.execute(job, progress_cb, cancel_check)

    assert result["status"] == "SUCCESS"
    assert result["records_synced"] > 0
    assert result["duration_ms"] >= 0
