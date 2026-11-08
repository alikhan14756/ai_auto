"""Worker handlers for workflow orchestration, stage dispatch, scheduling, and watchdog recovery."""

import datetime
from typing import Dict, Any, List
from uuid import UUID
from sqlalchemy import select, and_

from app.core.logging import logger
from app.db.session import AsyncSessionLocal
from app.models.job import AutomationJob
from app.models.workflow import (
    WorkflowExecution,
    WorkflowStage,
    WorkflowSchedule,
    WORKFLOW_STATUS_RUNNING,
    WORKFLOW_STATUS_RECOVERING,
    WORKFLOW_STATUS_SCHEDULED,
    STAGE_STATUS_RUNNING,
    STAGE_STATUS_COMPLETED,
)
from app.services.orchestration.workflow_engine import WorkflowEngine
from app.services.orchestration.health_monitor import ProductionHealthMonitor
from app.workers.handlers.base import (
    BaseJobHandler,
    HardFailureException,
    TransientException,
    JobCancelledException,
    ProgressCallback,
    CancellationChecker,
)


class WorkflowExecutionJobHandler(BaseJobHandler):
    """Orchestrates an active workflow execution, advancing stages through its state machine."""

    def __init__(self, session_factory=None):
        self._session_factory = session_factory or AsyncSessionLocal

    async def validate(self, payload: Dict[str, Any]) -> None:
        if not payload or not isinstance(payload, dict):
            raise HardFailureException("Payload must be a dictionary.")
        if not payload.get("workflow_execution_id"):
            raise HardFailureException("Missing required parameter: 'workflow_execution_id'.")
        try:
            UUID(str(payload["workflow_execution_id"]))
        except (ValueError, TypeError):
            raise HardFailureException(f"Invalid UUID: {payload.get('workflow_execution_id')}")

    async def execute(
        self,
        job: AutomationJob,
        update_progress: ProgressCallback,
        is_cancelled: CancellationChecker,
    ) -> Dict[str, Any]:
        if await is_cancelled():
            raise JobCancelledException(f"Job {job.id} was cancelled before execution.")

        payload = job.payload or {}
        execution_id = UUID(str(payload["workflow_execution_id"]))

        async with self._session_factory() as db:
            engine = WorkflowEngine(db)
            exec_stmt = select(WorkflowExecution).where(WorkflowExecution.id == execution_id)
            execution = (await db.execute(exec_stmt)).scalars().first()
            if not execution:
                raise HardFailureException(f"Workflow execution {execution_id} not found.")

            await update_progress(20, "Inspecting workflow stages")

            if execution.status in (WORKFLOW_STATUS_RUNNING, WORKFLOW_STATUS_RECOVERING):
                if execution.status == WORKFLOW_STATUS_RECOVERING:
                    execution.status = WORKFLOW_STATUS_RUNNING
                await engine.advance_execution(execution)
                await db.commit()

            await update_progress(100, "Workflow execution advanced")
            return {
                "workflow_execution_id": str(execution_id),
                "status": execution.status,
                "current_stage": execution.current_stage_key,
                "progress_percentage": execution.progress_percentage,
            }


class WorkflowStageDispatchJobHandler(BaseJobHandler):
    """Executes a single orchestrated stage within an active workflow."""

    def __init__(self, session_factory=None):
        self._session_factory = session_factory or AsyncSessionLocal

    async def validate(self, payload: Dict[str, Any]) -> None:
        if not payload or not isinstance(payload, dict):
            raise HardFailureException("Payload must be a dictionary.")
        if not payload.get("workflow_stage_id"):
            raise HardFailureException("Missing required parameter: 'workflow_stage_id'.")
        try:
            UUID(str(payload["workflow_stage_id"]))
        except (ValueError, TypeError):
            raise HardFailureException(f"Invalid UUID: {payload.get('workflow_stage_id')}")

    async def execute(
        self,
        job: AutomationJob,
        update_progress: ProgressCallback,
        is_cancelled: CancellationChecker,
    ) -> Dict[str, Any]:
        if await is_cancelled():
            raise JobCancelledException(f"Job {job.id} was cancelled before execution.")

        payload = job.payload or {}
        stage_id = UUID(str(payload["workflow_stage_id"]))

        async with self._session_factory() as db:
            stage_stmt = select(WorkflowStage).where(WorkflowStage.id == stage_id)
            stage = (await db.execute(stage_stmt)).scalars().first()
            if not stage:
                raise HardFailureException(f"Workflow stage {stage_id} not found.")

            await update_progress(25, f"Starting stage: {stage.stage_name}")

            # Mark completed and advance
            engine = WorkflowEngine(db)
            stage_outputs = {"executed_by": "WorkflowStageDispatchJobHandler", "job_id": str(job.id)}
            await engine.record_stage_completed(stage.id, stage_outputs)
            await db.commit()

            await update_progress(100, f"Completed stage: {stage.stage_name}")
            return {
                "stage_id": str(stage_id),
                "stage_key": stage.stage_key,
                "status": "COMPLETED",
            }


class ScheduledWorkflowTriggerJobHandler(BaseJobHandler):
    """Watchdog checking for due WorkflowSchedules and triggering execution."""

    def __init__(self, session_factory=None):
        self._session_factory = session_factory or AsyncSessionLocal

    async def validate(self, payload: Dict[str, Any]) -> None:
        # Payload can be empty for global periodic watchdog sweep
        pass

    async def execute(
        self,
        job: AutomationJob,
        update_progress: ProgressCallback,
        is_cancelled: CancellationChecker,
    ) -> Dict[str, Any]:
        if await is_cancelled():
            raise JobCancelledException(f"Job {job.id} was cancelled before execution.")

        now_utc = datetime.datetime.now(datetime.timezone.utc)
        triggered_count = 0

        async with self._session_factory() as db:
            engine = WorkflowEngine(db)
            stmt = select(WorkflowSchedule).where(
                and_(
                    WorkflowSchedule.status == "SCHEDULED",
                    WorkflowSchedule.planned_start_at <= now_utc,
                )
            )
            schedules = list((await db.execute(stmt)).scalars().all())

            await update_progress(30, f"Found {len(schedules)} due schedules")

            for sched in schedules:
                if await is_cancelled():
                    break
                try:
                    # Create workflow execution
                    execution = await engine.create_execution(
                        channel_id=sched.channel_id,
                        template_key="TEMPLATE_LONG_FORM" if sched.content_format == "LONG_FORM" else "TEMPLATE_SHORTS",
                        definition_id=sched.definition_id,
                        context_data={"schedule_id": str(sched.id), "title": sched.title},
                    )
                    await engine.start_execution(execution.id)
                    sched.status = "ACTIVE"
                    sched.last_run_at = now_utc
                    triggered_count += 1
                except Exception as e:
                    logger.error("Failed to start scheduled workflow %s: %s", sched.id, e)

            await db.commit()
            await update_progress(100, f"Triggered {triggered_count} scheduled workflows")
            return {"triggered_count": triggered_count}


class WorkflowRecoveryJobHandler(BaseJobHandler):
    """Watchdog sweeper detecting stalled stages and recovering executions."""

    def __init__(self, session_factory=None):
        self._session_factory = session_factory or AsyncSessionLocal

    async def validate(self, payload: Dict[str, Any]) -> None:
        pass

    async def execute(
        self,
        job: AutomationJob,
        update_progress: ProgressCallback,
        is_cancelled: CancellationChecker,
    ) -> Dict[str, Any]:
        if await is_cancelled():
            raise JobCancelledException(f"Job {job.id} was cancelled before execution.")

        async with self._session_factory() as db:
            monitor = ProductionHealthMonitor(db)
            stalled_stages = await monitor.detect_stalled_stages()

            await update_progress(30, f"Found {len(stalled_stages)} stalled stages")
            recovered_count = 0

            for stage in stalled_stages:
                if await is_cancelled():
                    break
                recovered = await monitor.attempt_stage_recovery(stage)
                if recovered:
                    engine = WorkflowEngine(db)
                    exec_stmt = select(WorkflowExecution).where(WorkflowExecution.id == stage.execution_id)
                    execution = (await db.execute(exec_stmt)).scalars().first()
                    if execution and execution.status == WORKFLOW_STATUS_RECOVERING:
                        execution.status = WORKFLOW_STATUS_RUNNING
                        await engine.advance_execution(execution)
                    recovered_count += 1

            await db.commit()
            await update_progress(100, f"Recovered {recovered_count} stalled stages")
            return {
                "stalled_found": len(stalled_stages),
                "recovered_count": recovered_count,
            }
