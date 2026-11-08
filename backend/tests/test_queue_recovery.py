"""Test watchdog crash recovery and stale lease expiration."""

import pytest
from datetime import datetime, timezone, timedelta
from app.services.job_queue import JobQueueService
from app.models.job import (
    JOB_STATUS_PROCESSING,
    JOB_STATUS_RETRYING,
    JOB_STATUS_FAILED,
)


@pytest.mark.asyncio
async def test_watchdog_reclaims_crashed_worker_job(db_session, test_channel):
    """If a worker crashes and stops sending heartbeats, watchdog reclaims job for retry."""
    queue = JobQueueService(db_session)

    job, _ = await queue.enqueue_job(
        channel_id=test_channel.id,
        job_type="TEST_DEMO",
        payload={"crash_test": True},
        max_retries=3,
    )
    claimed = await queue.claim_next_job(worker_id="crashed_worker")
    assert claimed.status == JOB_STATUS_PROCESSING

    # Simulate worker crash: heartbeat was 5 minutes ago (lease = 120s)
    claimed.heartbeat_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    await db_session.commit()

    # Run watchdog scanner
    reclaimed_count = await queue.reclaim_stale_jobs(lease_seconds=120)
    assert reclaimed_count == 1

    # Verify job status was set to RETRYING and locked_by released
    await db_session.refresh(claimed)
    assert claimed.status == JOB_STATUS_RETRYING
    assert claimed.locked_by is None
    assert "Worker crash detected" in claimed.error_log
    sched = claimed.scheduled_at
    if sched.tzinfo is None:
        sched = sched.replace(tzinfo=timezone.utc)
    assert sched > datetime.now(timezone.utc)


@pytest.mark.asyncio
async def test_watchdog_marks_failed_after_max_retries(db_session, test_channel):
    """If worker crashes repeatedly and max retries is reached, watchdog transitions job to FAILED."""
    queue = JobQueueService(db_session)

    job, _ = await queue.enqueue_job(
        channel_id=test_channel.id,
        job_type="TEST_DEMO",
        payload={},
        max_retries=1,  # Only 1 attempt allowed
    )
    claimed = await queue.claim_next_job(worker_id="doomed_worker")
    assert claimed.attempt_count == 1

    # Simulate expired heartbeat
    claimed.heartbeat_at = datetime.now(timezone.utc) - timedelta(minutes=10)
    await db_session.commit()

    # Run watchdog
    reclaimed_count = await queue.reclaim_stale_jobs(lease_seconds=120)
    assert reclaimed_count == 1

    await db_session.refresh(claimed)
    assert claimed.status == JOB_STATUS_FAILED
    assert claimed.completed_at is not None
    assert "max retries (1) exhausted" in claimed.error_log
