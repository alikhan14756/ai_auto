"""Test queue concurrency, race condition prevention, and priority dispatch."""

import asyncio
import pytest
from app.services.job_queue import JobQueueService
from tests.conftest import TestingSessionLocal


@pytest.mark.asyncio
async def test_concurrent_worker_claiming_no_duplicates(test_channel):
    """Multiple workers claiming concurrently must receive disjoint jobs with zero duplicates."""
    # Enqueue 10 distinct jobs
    async with TestingSessionLocal() as session:
        queue = JobQueueService(session)
        for i in range(10):
            await queue.enqueue_job(
                channel_id=test_channel.id,
                job_type="TEST_DEMO",
                payload={"index": i},
                priority=10,
            )

    # 4 distinct workers claim concurrently using independent database sessions per claim
    async def worker_claim(worker_name: str):
        claimed_ids = []
        while True:
            async with TestingSessionLocal() as session:
                q = JobQueueService(session)
                job = await q.claim_next_job(worker_id=worker_name)
                if not job:
                    break
                claimed_ids.append(job.id)
                await asyncio.sleep(0.005)
        return claimed_ids

    results = await asyncio.gather(
        worker_claim("worker_1"),
        worker_claim("worker_2"),
        worker_claim("worker_3"),
        worker_claim("worker_4"),
    )

    all_claimed = []
    for worker_claimed in results:
        all_claimed.extend(worker_claimed)

    # Every job must be claimed exactly once with zero collisions or duplicates
    assert len(all_claimed) == 10
    assert len(set(all_claimed)) == 10


@pytest.mark.asyncio
async def test_priority_ordering_dispatch(db_session, test_channel):
    """High priority (lower integer value) jobs are claimed before lower priority jobs."""
    queue = JobQueueService(db_session)

    # Enqueue low priority job first
    low_job, _ = await queue.enqueue_job(
        channel_id=test_channel.id,
        job_type="TEST_DEMO",
        payload={"task": "low_priority"},
        priority=50,
    )
    # Enqueue high priority job second
    high_job, _ = await queue.enqueue_job(
        channel_id=test_channel.id,
        job_type="TEST_DEMO",
        payload={"task": "high_priority"},
        priority=1,
    )

    # First claim must be the high priority job
    first_claimed = await queue.claim_next_job("worker_test")
    assert first_claimed.id == high_job.id

    # Second claim must be the low priority job
    second_claimed = await queue.claim_next_job("worker_test")
    assert second_claimed.id == low_job.id
