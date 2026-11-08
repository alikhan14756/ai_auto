"""Durable worker job handler for Autonomous QA Package Inspection."""

import uuid
from typing import Any, Dict, Optional
from uuid import UUID

from app.core.logging import logger
from app.db.session import AsyncSessionLocal
from app.models.job import AutomationJob
from app.services.qa_service import QAService
from app.workers.handlers.base import (
    BaseJobHandler,
    CancellationChecker,
    HardFailureException,
    JobCancelledException,
    ProgressCallback,
)


class QAPackageInspectionJobHandler(BaseJobHandler):
    """Executes asynchronous 12-category QA evaluation and veto determination."""

    def __init__(self, session_factory=None):
        self._session_factory = session_factory or AsyncSessionLocal

    async def validate(self, payload: Dict[str, Any]) -> None:
        if not payload or not isinstance(payload, dict):
            raise HardFailureException("Payload must be a non-empty dictionary.")
        if not payload.get("run_id"):
            raise HardFailureException("Missing required parameter: 'run_id'.")
        try:
            UUID(str(payload["run_id"]))
        except (ValueError, TypeError):
            raise HardFailureException(f"Invalid UUID for 'run_id': {payload.get('run_id')}")

    async def execute(
        self,
        job: AutomationJob,
        update_progress: ProgressCallback,
        is_cancelled: CancellationChecker,
    ) -> Dict[str, Any]:
        if await is_cancelled():
            raise JobCancelledException(f"Job {job.id} was cancelled before execution.")

        payload = job.payload or {}
        run_id = UUID(str(payload["run_id"]))
        target_categories = None
        if "target_categories" in payload and isinstance(payload["target_categories"], list):
            target_categories = set(payload["target_categories"])

        logger.info(f"Starting QA package inspection for run_id={run_id}")

        await update_progress(15, "INITIALIZING_CONTEXT")
        if await is_cancelled():
            raise JobCancelledException(f"Job {job.id} was cancelled.")

        async with self._session_factory() as session:
            await update_progress(45, "INSPECTING_ALL_CATEGORIES")
            if await is_cancelled():
                raise JobCancelledException(f"Job {job.id} was cancelled.")

            qa_run = await QAService.execute_qa_run(
                db=session,
                run_id=run_id,
                target_categories=target_categories,
            )

            await update_progress(90, "VETO_EVALUATION_AND_SCORING")
            if await is_cancelled():
                raise JobCancelledException(f"Job {job.id} was cancelled.")

            await update_progress(100, "QA_AUDIT_COMPLETED")

            logger.info(
                f"QA Inspection completed for run_id={run_id}: "
                f"Score={qa_run.overall_score}, Veto={qa_run.veto_decision}, CanPublish={qa_run.can_publish}"
            )

            return {
                "run_id": str(qa_run.id),
                "project_id": str(qa_run.project_id),
                "overall_score": float(qa_run.overall_score or 0.0),
                "veto_decision": qa_run.veto_decision,
                "can_publish": qa_run.can_publish,
                "summary": qa_run.summary,
            }
