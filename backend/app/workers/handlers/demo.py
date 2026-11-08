"""Demo and verification job handler for M04 testing."""

import asyncio
from typing import Dict, Any, Optional
from app.models.job import AutomationJob
from app.workers.handlers.base import (
    BaseJobHandler,
    ProgressCallback,
    CancellationChecker,
    TransientException,
    HardFailureException,
    JobCancelledException,
)
from app.core.logging import logger


class DemoJobHandler(BaseJobHandler):
    """Test job handler that exercises multi-stage progress, cancellation,
    and simulated error conditions without calling external services.
    """

    async def validate(self, payload: Dict[str, Any]) -> None:
        """Validate payload parameters."""
        if not isinstance(payload, dict):
            raise HardFailureException("Payload must be a JSON dictionary")

        if payload.get("force_validation_error"):
            raise HardFailureException("Simulated payload validation error")

    async def execute(
        self,
        job: AutomationJob,
        update_progress: ProgressCallback,
        is_cancelled: CancellationChecker,
    ) -> Dict[str, Any]:
        """Execute simulated multi-stage workflow."""
        payload = job.payload or {}
        step_delay = float(payload.get("step_delay_seconds", 0.05))

        logger.info(f"[DemoJobHandler] Starting job {job.id}")

        # Stage 1: Initializing
        await update_progress(10, "INITIALIZING")
        await asyncio.sleep(step_delay)
        if await is_cancelled():
            raise JobCancelledException("Job was cancelled during initialization")

        # Simulate Transient Failure if requested on first attempt
        if payload.get("simulate_transient_failure"):
            fail_until_attempt = int(payload.get("fail_until_attempt", 2))
            if job.attempt_count < fail_until_attempt:
                raise TransientException(
                    f"Simulated network timeout on attempt {job.attempt_count} (recovers at {fail_until_attempt})"
                )

        # Simulate Hard Failure if requested
        if payload.get("simulate_permanent_failure"):
            raise HardFailureException("Simulated unrecoverable domain error")

        # Stage 2: Processing
        await update_progress(40, "PROCESSING_DATA")
        await asyncio.sleep(step_delay)
        if await is_cancelled():
            raise JobCancelledException("Job was cancelled during data processing")

        # Stage 3: Synthesizing
        await update_progress(75, "SYNTHESIZING_RESULTS")
        await asyncio.sleep(step_delay)
        if await is_cancelled():
            raise JobCancelledException("Job was cancelled during synthesis")

        # Stage 4: Finalizing
        await update_progress(95, "FINALIZING")
        await asyncio.sleep(step_delay)

        logger.info(f"[DemoJobHandler] Completed job {job.id}")
        return {
            "status": "success",
            "message": "Demo job executed flawlessly",
            "stages_completed": 4,
            "processed_payload": payload,
        }
