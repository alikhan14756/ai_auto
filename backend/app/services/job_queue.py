"""Durable, database-backed Job Queue Service using PostgreSQL transactional locking."""

import uuid
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import select, update, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.models.job import (
    AutomationJob,
    JOB_STATUS_QUEUED,
    JOB_STATUS_PROCESSING,
    JOB_STATUS_RETRYING,
    JOB_STATUS_COMPLETED,
    JOB_STATUS_FAILED,
    JOB_STATUS_CANCELLED,
    JOB_STATUS_NEEDS_ATTENTION,
)


# Module-level claim lock to synchronize concurrent in-process workers
_in_process_claim_lock = asyncio.Lock()


class JobQueueService:
    """Manages persistent automation jobs with atomic claiming, lease heartbeats,
    and exponential retry backoff.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def enqueue_job(
        self,
        channel_id: uuid.UUID,
        job_type: str,
        payload: Dict[str, Any],
        idempotency_key: Optional[str] = None,
        priority: int = 10,
        scheduled_at: Optional[datetime] = None,
        max_retries: int = 3,
    ) -> Tuple[AutomationJob, bool]:
        """Enqueue a new job or return existing one if idempotency key matches.
        Returns (job, created_flag).
        """
        if not idempotency_key:
            idempotency_key = f"{job_type}_{channel_id}_{uuid.uuid4().hex[:16]}"

        # Check for existing job with same idempotency key
        stmt = select(AutomationJob).where(AutomationJob.idempotency_key == idempotency_key)
        res = await self.db.execute(stmt)
        existing = res.scalars().first()
        if existing:
            logger.info(f"Idempotent job hit: returning existing job {existing.id} ({idempotency_key})")
            return existing, False

        job = AutomationJob(
            channel_id=channel_id,
            job_type=job_type,
            payload=payload,
            idempotency_key=idempotency_key,
            status=JOB_STATUS_QUEUED,
            priority=priority,
            scheduled_at=scheduled_at,
            max_retries=max_retries,
            attempt_count=0,
            progress_percentage=0,
            current_stage="QUEUED",
        )
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        logger.info(f"Enqueued job {job.id} [{job_type}] for channel {channel_id}")
        return job, True

    async def claim_next_job(self, worker_id: str) -> Optional[AutomationJob]:
        """Atomically claim the highest-priority eligible job.
        Uses FOR UPDATE SKIP LOCKED on PostgreSQL and conditional atomic update
        to prevent duplicate execution across concurrent workers on all database engines.
        """
        async with _in_process_claim_lock:
            now = datetime.now(timezone.utc)

            # Base query for eligible jobs
            stmt = (
                select(AutomationJob.id)
                .where(
                    and_(
                        AutomationJob.status.in_([JOB_STATUS_QUEUED, JOB_STATUS_RETRYING]),
                        or_(
                            AutomationJob.scheduled_at.is_(None),
                            AutomationJob.scheduled_at <= now,
                        ),
                    )
                )
                .order_by(AutomationJob.priority.asc(), AutomationJob.created_at.asc())
                .limit(5)
            )

            bind = self.db.get_bind()
            if bind and bind.dialect.name == "postgresql":
                stmt = stmt.with_for_update(skip_locked=True)

            result = await self.db.execute(stmt)
            candidate_ids = result.scalars().all()

            if not candidate_ids:
                return None

            # Attempt atomic conditional update on candidate jobs
            for candidate_id in candidate_ids:
                stmt_update = (
                    update(AutomationJob)
                    .where(
                        and_(
                            AutomationJob.id == candidate_id,
                            AutomationJob.status.in_([JOB_STATUS_QUEUED, JOB_STATUS_RETRYING]),
                        )
                    )
                    .values(
                        status=JOB_STATUS_PROCESSING,
                        locked_by=worker_id,
                        locked_at=now,
                        heartbeat_at=now,
                        started_at=func.coalesce(AutomationJob.started_at, now),
                        attempt_count=AutomationJob.attempt_count + 1,
                        current_stage="PROCESSING",
                    )
                )
                res_update = await self.db.execute(stmt_update)
                if res_update.rowcount > 0:
                    await self.db.commit()
                    # Fetch fresh claimed job
                    fetch_stmt = select(AutomationJob).where(AutomationJob.id == candidate_id)
                    res_fetch = await self.db.execute(fetch_stmt)
                    claimed_job = res_fetch.scalars().first()
                    logger.info(
                        f"Worker [{worker_id}] claimed job {claimed_job.id} [{claimed_job.job_type}], attempt {claimed_job.attempt_count}"
                    )
                    return claimed_job

            # All candidates were claimed by other concurrent workers
            await self.db.rollback()
            return None

    async def record_heartbeat(self, job_id: uuid.UUID, worker_id: str) -> bool:
        """Update heartbeat timestamp for active job to preserve lease."""
        stmt = (
            update(AutomationJob)
            .where(
                and_(
                    AutomationJob.id == job_id,
                    AutomationJob.locked_by == worker_id,
                    AutomationJob.status == JOB_STATUS_PROCESSING,
                )
            )
            .values(heartbeat_at=datetime.now(timezone.utc))
        )
        res = await self.db.execute(stmt)
        if res.rowcount > 0:
            await self.db.commit()
            return True
        return False

    async def update_progress(
        self,
        job_id: uuid.UUID,
        percentage: int,
        current_stage: Optional[str] = None,
    ) -> Optional[AutomationJob]:
        """Update job progress percentage and current stage."""
        clamped = max(0, min(100, percentage))
        values: Dict[str, Any] = {"progress_percentage": clamped}
        if current_stage:
            values["current_stage"] = current_stage

        stmt = update(AutomationJob).where(AutomationJob.id == job_id).values(**values)
        await self.db.execute(stmt)
        await self.db.commit()

        fetch_stmt = select(AutomationJob).where(AutomationJob.id == job_id)
        res = await self.db.execute(fetch_stmt)
        return res.scalars().first()

    async def mark_completed(
        self,
        job_id: uuid.UUID,
        result_details: Optional[Dict[str, Any]] = None,
    ) -> Optional[AutomationJob]:
        """Mark job execution as successfully completed."""
        now = datetime.now(timezone.utc)
        stmt = select(AutomationJob).where(AutomationJob.id == job_id)
        res = await self.db.execute(stmt)
        job = res.scalars().first()
        if not job:
            return None

        job.status = JOB_STATUS_COMPLETED
        job.progress_percentage = 100
        job.current_stage = "COMPLETED"
        job.completed_at = now
        job.locked_by = None

        if result_details:
            updated_payload = dict(job.payload or {})
            updated_payload["_result"] = result_details
            job.payload = updated_payload

        await self.db.commit()
        await self.db.refresh(job)
        logger.info(f"Job {job.id} [{job.job_type}] marked COMPLETED")
        return job

    async def mark_failed(
        self,
        job_id: uuid.UUID,
        error_message: str,
        is_permanent: bool = False,
    ) -> Optional[AutomationJob]:
        """Handle job failure, scheduling exponential retry or marking permanent failure."""
        now = datetime.now(timezone.utc)
        stmt = select(AutomationJob).where(AutomationJob.id == job_id)
        res = await self.db.execute(stmt)
        job = res.scalars().first()
        if not job:
            return None

        job.error_log = error_message
        job.locked_by = None

        if is_permanent or job.attempt_count >= job.max_retries:
            job.status = JOB_STATUS_FAILED
            job.completed_at = now
            job.current_stage = "FAILED"
            logger.error(
                f"Job {job.id} [{job.job_type}] FAILED permanently (attempt {job.attempt_count}/{job.max_retries}): {error_message}"
            )
        else:
            # Exponential backoff: base * 2^(attempt - 1)
            backoff_seconds = (2 ** max(0, job.attempt_count - 1)) * settings.WORKER_BASE_BACKOFF_SECONDS
            job.status = JOB_STATUS_RETRYING
            job.scheduled_at = now + timedelta(seconds=backoff_seconds)
            job.current_stage = f"RETRYING_IN_{backoff_seconds}S"
            logger.warning(
                f"Job {job.id} [{job.job_type}] failed attempt {job.attempt_count}/{job.max_retries}. "
                f"Retrying in {backoff_seconds}s: {error_message}"
            )

        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def mark_cancelled(self, job_id: uuid.UUID) -> Optional[AutomationJob]:
        """Cancel an eligible non-terminal job."""
        stmt = select(AutomationJob).where(AutomationJob.id == job_id)
        res = await self.db.execute(stmt)
        job = res.scalars().first()
        if not job:
            return None

        if job.status in [JOB_STATUS_COMPLETED, JOB_STATUS_CANCELLED]:
            logger.warning(f"Cannot cancel job {job.id}: already in terminal state {job.status}")
            return job

        job.status = JOB_STATUS_CANCELLED
        job.current_stage = "CANCELLED"
        job.completed_at = datetime.now(timezone.utc)
        job.locked_by = None

        await self.db.commit()
        await self.db.refresh(job)
        logger.info(f"Job {job.id} cancelled successfully")
        return job

    async def retry_job(self, job_id: uuid.UUID) -> Optional[AutomationJob]:
        """Manually restart a FAILED job."""
        stmt = select(AutomationJob).where(AutomationJob.id == job_id)
        res = await self.db.execute(stmt)
        job = res.scalars().first()
        if not job:
            return None

        if job.status not in [JOB_STATUS_FAILED, JOB_STATUS_CANCELLED, JOB_STATUS_NEEDS_ATTENTION]:
            raise ValueError(f"Only FAILED, CANCELLED, or NEEDS_ATTENTION jobs can be retried. Current: {job.status}")

        job.status = JOB_STATUS_QUEUED
        job.current_stage = "QUEUED"
        job.attempt_count = 0
        job.scheduled_at = None
        job.error_log = None
        job.locked_by = None
        job.completed_at = None

        await self.db.commit()
        await self.db.refresh(job)
        logger.info(f"Job {job.id} reset for manual retry")
        return job

    async def reclaim_stale_jobs(self, lease_seconds: Optional[int] = None) -> int:
        """Watchdog scanner: detects crashed workers whose heartbeats have expired.
        Reclaims jobs for retry or marks them failed if max retries exceeded.
        """
        lease = lease_seconds or settings.WORKER_LEASE_SECONDS
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=lease)

        stmt = select(AutomationJob).where(
            and_(
                AutomationJob.status == JOB_STATUS_PROCESSING,
                or_(
                    AutomationJob.heartbeat_at < cutoff,
                    and_(AutomationJob.heartbeat_at.is_(None), AutomationJob.locked_at < cutoff),
                ),
            )
        )
        res = await self.db.execute(stmt)
        stale_jobs = res.scalars().all()

        count = 0
        now = datetime.now(timezone.utc)
        for job in stale_jobs:
            logger.warning(
                f"Crash Watchdog: Reclaiming stale job {job.id} [Worker: {job.locked_by}] "
                f"(last heartbeat: {job.heartbeat_at})"
            )
            count += 1
            if job.attempt_count < job.max_retries:
                backoff_seconds = (2 ** max(0, job.attempt_count - 1)) * settings.WORKER_BASE_BACKOFF_SECONDS
                job.status = JOB_STATUS_RETRYING
                job.scheduled_at = now + timedelta(seconds=backoff_seconds)
                job.error_log = f"Worker crash detected: lease expired after {lease}s without heartbeat"
                job.current_stage = "RETRYING_AFTER_CRASH"
            else:
                job.status = JOB_STATUS_FAILED
                job.completed_at = now
                job.error_log = f"Job failed: worker lease expired and max retries ({job.max_retries}) exhausted"
                job.current_stage = "FAILED_CRASH"
            job.locked_by = None

        if count > 0:
            await self.db.commit()
            logger.info(f"Crash Watchdog reclaimed {count} stale jobs")

        return count
