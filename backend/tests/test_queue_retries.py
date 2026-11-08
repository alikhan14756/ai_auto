"""Test retry semantics, exponential backoff scheduling, and failure classification."""

import pytest
from datetime import datetime, timezone, timedelta
from app.services.job_queue import JobQueueService
from app.models.job import (
    JOB_STATUS_RETRYING,
    JOB_STATUS_FAILED,
)
from app.core.config import settings


@pytest.mark.asyncio
async def test_transient_failure_exponential_backoff(db_session, test_channel):
    """Transient errors schedule exponential retry with formula: 2^(attempt - 1) * base_backoff."""
    queue = JobQueueService(db_session)
    job, _ = await queue.enqueue_job(
        channel_id=test_channel.id,
        job_type="TEST_DEMO",
        payload={},
        max_retries=3,
    )

    # Attempt 1: backoff = 2^0 * 30s = 30s
    claimed = await queue.claim_next_job("worker_1")
    retrying_1 = await queue.mark_failed(claimed.id, "Temporary network blip", is_permanent=False)
    assert retrying_1.status == JOB_STATUS_RETRYING
    assert retrying_1.attempt_count == 1
    # Check scheduled_at is approximately 30s in future
    expected_delay_1 = settings.WORKER_BASE_BACKOFF_SECONDS
    now = datetime.now(timezone.utc)
    sched_1 = retrying_1.scheduled_at if retrying_1.scheduled_at.tzinfo else retrying_1.scheduled_at.replace(tzinfo=timezone.utc)
    assert sched_1 > now + timedelta(seconds=expected_delay_1 - 2)

    # Force scheduled_at to past so it can be claimed for attempt 2
    retrying_1.scheduled_at = now - timedelta(seconds=1)
    await db_session.commit()

    # Attempt 2: backoff = 2^1 * 30s = 60s
    claimed_2 = await queue.claim_next_job("worker_1")
    assert claimed_2.attempt_count == 2
    retrying_2 = await queue.mark_failed(claimed_2.id, "Second temporary blip", is_permanent=False)
    assert retrying_2.status == JOB_STATUS_RETRYING
    expected_delay_2 = settings.WORKER_BASE_BACKOFF_SECONDS * 2
    sched_2 = retrying_2.scheduled_at if retrying_2.scheduled_at.tzinfo else retrying_2.scheduled_at.replace(tzinfo=timezone.utc)
    assert sched_2 > now + timedelta(seconds=expected_delay_2 - 2)


@pytest.mark.asyncio
async def test_permanent_failure_marks_failed_immediately(db_session, test_channel):
    """Permanent domain failure marks job FAILED immediately without retrying."""
    queue = JobQueueService(db_session)
    job, _ = await queue.enqueue_job(
        channel_id=test_channel.id,
        job_type="TEST_DEMO",
        payload={},
        max_retries=5,
    )
    claimed = await queue.claim_next_job("worker_1")
    failed = await queue.mark_failed(claimed.id, "Invalid schema", is_permanent=True)

    assert failed.status == JOB_STATUS_FAILED
    assert failed.attempt_count == 1  # Only 1 attempt made
    assert failed.completed_at is not None
    assert failed.scheduled_at is None
