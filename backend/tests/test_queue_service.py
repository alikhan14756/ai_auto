"""Test JobQueueService operations, atomic transitions, and state management."""

import uuid
import pytest
from datetime import datetime, timezone, timedelta
from app.services.job_queue import JobQueueService
from app.models.job import (
    AutomationJob,
    JOB_STATUS_QUEUED,
    JOB_STATUS_PROCESSING,
    JOB_STATUS_COMPLETED,
    JOB_STATUS_FAILED,
    JOB_STATUS_CANCELLED,
    JOB_STATUS_RETRYING,
)


@pytest.mark.asyncio
async def test_enqueue_and_claim_job(db_session, test_channel):
    """Enqueue a job and verify atomic claiming transitions it to PROCESSING."""
    queue = JobQueueService(db_session)

    job, created = await queue.enqueue_job(
        channel_id=test_channel.id,
        job_type="TEST_DEMO",
        payload={"task": "test_1"},
        priority=5,
    )
    assert created is True
    assert job.status == JOB_STATUS_QUEUED
    assert job.attempt_count == 0

    # Claim next job
    claimed = await queue.claim_next_job(worker_id="worker_alpha")
    assert claimed is not None
    assert claimed.id == job.id
    assert claimed.status == JOB_STATUS_PROCESSING
    assert claimed.locked_by == "worker_alpha"
    assert claimed.attempt_count == 1
    assert claimed.heartbeat_at is not None


@pytest.mark.asyncio
async def test_empty_queue_returns_none(db_session):
    """Claiming from an empty queue returns None without error."""
    queue = JobQueueService(db_session)
    claimed = await queue.claim_next_job(worker_id="worker_alpha")
    assert claimed is None


@pytest.mark.asyncio
async def test_update_progress_and_complete(db_session, test_channel):
    """Update progress and verify successful completion."""
    queue = JobQueueService(db_session)
    job, _ = await queue.enqueue_job(
        channel_id=test_channel.id,
        job_type="TEST_DEMO",
        payload={"foo": "bar"},
    )
    claimed = await queue.claim_next_job(worker_id="worker_alpha")

    # Update progress
    updated = await queue.update_progress(claimed.id, percentage=50, current_stage="HALF_DONE")
    assert updated.progress_percentage == 50
    assert updated.current_stage == "HALF_DONE"

    # Mark completed
    completed = await queue.mark_completed(claimed.id, result_details={"output": "success"})
    assert completed.status == JOB_STATUS_COMPLETED
    assert completed.progress_percentage == 100
    assert completed.locked_by is None
    assert completed.completed_at is not None
    assert completed.payload["_result"]["output"] == "success"


@pytest.mark.asyncio
async def test_cancel_job(db_session, test_channel):
    """Cancel a queued job sets status to CANCELLED."""
    queue = JobQueueService(db_session)
    job, _ = await queue.enqueue_job(
        channel_id=test_channel.id,
        job_type="TEST_DEMO",
        payload={"cancel_me": True},
    )

    cancelled = await queue.mark_cancelled(job.id)
    assert cancelled.status == JOB_STATUS_CANCELLED
    assert cancelled.completed_at is not None

    # Cancelled job should not be claimable
    claimed = await queue.claim_next_job(worker_id="worker_alpha")
    assert claimed is None


@pytest.mark.asyncio
async def test_manual_retry_resets_failed_job(db_session, test_channel):
    """Manually retrying a FAILED job resets it to QUEUED with fresh attempt count."""
    queue = JobQueueService(db_session)
    job, _ = await queue.enqueue_job(
        channel_id=test_channel.id,
        job_type="TEST_DEMO",
        payload={},
    )
    claimed = await queue.claim_next_job("worker_1")
    failed = await queue.mark_failed(claimed.id, error_message="Fatal error", is_permanent=True)
    assert failed.status == JOB_STATUS_FAILED

    # Manual retry
    retried = await queue.retry_job(job.id)
    assert retried.status == JOB_STATUS_QUEUED
    assert retried.attempt_count == 0
    assert retried.error_log is None
