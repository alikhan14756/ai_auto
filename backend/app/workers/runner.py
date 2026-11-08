"""Autonomous Background Worker Daemon Engine."""

import os
import sys
import uuid
import socket
import signal
import asyncio
from datetime import datetime, timezone
from typing import Optional, Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from app.core.config import settings
from app.core.logging import logger, setup_logging
from app.db.session import AsyncSessionLocal
from app.models.job import (
    AutomationJob,
    JOB_STATUS_CANCELLED,
    JOB_STATUS_PROCESSING,
)
from app.services.job_queue import JobQueueService
from app.workers.registry import registry
from app.workers.handlers.base import (
    TransientException,
    HardFailureException,
    JobCancelledException,
)


class WorkerDaemon:
    """Persistent background worker process that claims and executes queue jobs."""

    def __init__(
        self,
        worker_id: Optional[str] = None,
        session_factory: Optional[async_sessionmaker[AsyncSession]] = None,
    ):
        hostname = socket.gethostname()
        pid = os.getpid()
        self.worker_id = worker_id or settings.WORKER_ID or f"worker_{hostname}_{pid}_{uuid.uuid4().hex[:6]}"
        self.session_factory = session_factory or AsyncSessionLocal
        self.is_running = False
        self._stop_event = asyncio.Event()
        self._last_watchdog_time = 0.0

    def request_stop(self) -> None:
        """Signal worker to stop gracefully after current job completes."""
        logger.info(f"Worker [{self.worker_id}] stop requested...")
        self.is_running = False
        self._stop_event.set()

    async def _send_heartbeats(self, job_id: uuid.UUID) -> None:
        """Background coroutine sending periodic lease heartbeats for the active job."""
        interval = settings.WORKER_HEARTBEAT_INTERVAL
        while self.is_running:
            try:
                await asyncio.sleep(interval)
                async with self.session_factory() as session:
                    queue_service = JobQueueService(session)
                    success = await queue_service.record_heartbeat(job_id, self.worker_id)
                    if success:
                        logger.debug(f"Heartbeat sent for job {job_id} by worker {self.worker_id}")
                    else:
                        logger.warning(f"Failed to record heartbeat for job {job_id} (job no longer active)")
                        break
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error(f"Error in heartbeat loop for job {job_id}: {exc}")

    async def _check_cancellation(self, job_id: uuid.UUID) -> bool:
        """Query DB to check if cancellation has been requested for this job."""
        try:
            async with self.session_factory() as session:
                stmt = select(AutomationJob.status).where(AutomationJob.id == job_id)
                res = await session.execute(stmt)
                status = res.scalar_one_or_none()
                return status == JOB_STATUS_CANCELLED
        except Exception:
            return False

    async def process_one_job(self) -> bool:
        """Attempt to claim and process a single job.
        Returns True if a job was found and processed, False if queue was empty.
        """
        async with self.session_factory() as session:
            queue_service = JobQueueService(session)

            # 1. Periodic Crash Recovery Watchdog
            now_ts = asyncio.get_event_loop().time()
            if now_ts - self._last_watchdog_time > 30.0:
                self._last_watchdog_time = now_ts
                try:
                    reclaimed = await queue_service.reclaim_stale_jobs()
                    if reclaimed > 0:
                        logger.info(f"Watchdog reclaimed {reclaimed} stale jobs")
                except Exception as exc:
                    logger.error(f"Watchdog scan error: {exc}")

            # 2. Claim next job
            job = await queue_service.claim_next_job(self.worker_id)
            if not job:
                return False

            job_id = job.id
            job_type = job.job_type
            job_payload = job.payload

        # 3. Start heartbeat task
        heartbeat_task = asyncio.create_task(self._send_heartbeats(job_id))

        try:
            # 4. Resolve handler
            handler = registry.get_handler(job_type)

            # 5. Validate input
            await handler.validate(job_payload)

            # 6. Callbacks
            async def progress_callback(pct: int, stage: Optional[str] = None) -> None:
                async with self.session_factory() as p_session:
                    p_queue = JobQueueService(p_session)
                    await p_queue.update_progress(job_id, pct, stage)

            async def cancellation_checker() -> bool:
                return await self._check_cancellation(job_id)

            # 7. Execute handler
            result = await handler.execute(job, progress_callback, cancellation_checker)

            # 8. Mark complete
            async with self.session_factory() as c_session:
                c_queue = JobQueueService(c_session)
                await c_queue.mark_completed(job_id, result)

        except TransientException as e:
            logger.warning(f"Transient failure in job {job_id}: {e}")
            async with self.session_factory() as f_session:
                f_queue = JobQueueService(f_session)
                await f_queue.mark_failed(job_id, str(e), is_permanent=False)

        except HardFailureException as e:
            logger.error(f"Permanent failure in job {job_id}: {e}")
            async with self.session_factory() as f_session:
                f_queue = JobQueueService(f_session)
                await f_queue.mark_failed(job_id, str(e), is_permanent=True)

        except JobCancelledException as e:
            logger.info(f"Job {job_id} cancelled during execution: {e}")
            async with self.session_factory() as f_session:
                f_queue = JobQueueService(f_session)
                await f_queue.mark_cancelled(job_id)

        except Exception as e:
            logger.exception(f"Unhandled exception executing job {job_id}: {e}")
            async with self.session_factory() as f_session:
                f_queue = JobQueueService(f_session)
                await f_queue.mark_failed(job_id, f"Unhandled worker exception: {e}", is_permanent=False)

        finally:
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass

        return True

    async def run_loop(self) -> None:
        """Run the persistent polling worker daemon."""
        self.is_running = True
        logger.info(f"Worker Daemon [{self.worker_id}] initialized and running.")
        logger.info(f"Polling interval: {settings.WORKER_POLL_INTERVAL}s | Lease duration: {settings.WORKER_LEASE_SECONDS}s")

        poll_interval = settings.WORKER_POLL_INTERVAL

        while self.is_running:
            try:
                processed = await self.process_one_job()
                if not processed:
                    # Queue is idle, wait poll interval or until stop event
                    try:
                        await asyncio.wait_for(self._stop_event.wait(), timeout=poll_interval)
                    except asyncio.TimeoutError:
                        pass
            except Exception as exc:
                logger.error(f"Worker loop encountered an unexpected error: {exc}")
                await asyncio.sleep(poll_interval)

        logger.info(f"Worker Daemon [{self.worker_id}] stopped cleanly.")


async def start_worker(worker_id: Optional[str] = None) -> None:
    """Bootstrap and start worker daemon with signal handlers."""
    setup_logging(level="DEBUG" if settings.APP_DEBUG else "INFO")
    worker = WorkerDaemon(worker_id=worker_id)

    # Attach signal listeners
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, worker.request_stop)
        except NotImplementedError:
            pass

    try:
        await worker.run_loop()
    except KeyboardInterrupt:
        worker.request_stop()


if __name__ == "__main__":
    try:
        asyncio.run(start_worker())
    except KeyboardInterrupt:
        print("\nWorker process terminated by user.")
