"""Production health monitoring, failure detection, and bounded watchdog recovery."""

from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_

from app.models.workflow import (
    WorkflowExecution,
    WorkflowStage,
    WorkflowFailure,
    WorkflowEvent,
    WorkflowPolicy,
    WORKFLOW_STATUS_RUNNING,
    WORKFLOW_STATUS_RECOVERING,
    WORKFLOW_STATUS_FAILED,
    WORKFLOW_STATUS_COMPLETED,
    STAGE_STATUS_RUNNING,
    STAGE_STATUS_PENDING,
    STAGE_STATUS_FAILED,
)
from app.models.job import (
    AutomationJob,
    JOB_STATUS_PROCESSING,
    JOB_STATUS_QUEUED,
    JOB_STATUS_FAILED,
)


class ProductionHealthMonitor:
    """Monitors workflow execution health and triggers bounded, idempotent recoveries."""

    STALL_TIMEOUT_SECONDS = 180  # Consider job stalled if no heartbeat for 3 minutes

    def __init__(self, db: AsyncSession):
        self.db = db

    async def detect_stalled_stages(self, channel_id: Optional[UUID] = None) -> List[WorkflowStage]:
        """Identify stages in RUNNING status whose underlying queue job has ceased heartbeating."""
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=self.STALL_TIMEOUT_SECONDS)

        query = (
            select(WorkflowStage)
            .join(WorkflowExecution, WorkflowStage.execution_id == WorkflowExecution.id)
            .join(AutomationJob, WorkflowStage.job_id == AutomationJob.id)
            .where(
                and_(
                    WorkflowStage.status == STAGE_STATUS_RUNNING,
                    WorkflowExecution.status == WORKFLOW_STATUS_RUNNING,
                    or_(
                        and_(AutomationJob.heartbeat_at.is_not(None), AutomationJob.heartbeat_at < cutoff),
                        and_(
                            AutomationJob.heartbeat_at.is_(None),
                            func.coalesce(AutomationJob.started_at, AutomationJob.created_at) < cutoff,
                        ),
                    ),
                )
            )
        )

        if channel_id:
            query = query.where(WorkflowExecution.channel_id == channel_id)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def attempt_stage_recovery(
        self, stage: WorkflowStage, error_category: str = "WORKER_TIMEOUT"
    ) -> bool:
        """Execute bounded recovery for a stalled or crashed workflow stage."""
        execution_stmt = select(WorkflowExecution).where(WorkflowExecution.id == stage.execution_id)
        execution = (await self.db.execute(execution_stmt)).scalars().first()
        if not execution:
            return False

        # Fetch channel policy
        policy_stmt = select(WorkflowPolicy).where(WorkflowPolicy.channel_id == execution.channel_id)
        policy = (await self.db.execute(policy_stmt)).scalars().first()
        max_retries = policy.max_retry_attempts if policy else 3
        auto_retry = policy.auto_retry_transient_failures if policy else True

        if not auto_retry:
            execution.status = WORKFLOW_STATUS_FAILED
            execution.error_message = f"Automatic recovery disabled by policy. Failed at stage: {stage.stage_key}."
            stage.status = STAGE_STATUS_FAILED
            stage.error_message = "Recovery disabled by channel policy."
            await self._log_failure(execution, stage, error_category, "Manual intervention required.")
            await self.db.flush()
            return False

        if execution.failure_count >= max_retries:
            # Retries exhausted
            execution.status = WORKFLOW_STATUS_FAILED
            execution.error_message = f"Exhausted maximum retry attempts ({max_retries}) at stage: {stage.stage_key}."
            stage.status = STAGE_STATUS_FAILED
            stage.error_message = "Retry limit exceeded."
            await self._log_failure(execution, stage, "RETRY_EXHAUSTED", "Exhausted retry budget.")
            await self.db.flush()
            return False

        # Attempt recovery: increment failure count, reset stage to PENDING, set execution to RECOVERING
        execution.failure_count += 1
        execution.status = WORKFLOW_STATUS_RECOVERING
        stage.status = STAGE_STATUS_PENDING
        stage.error_message = f"Stall recovered (attempt {execution.failure_count}/{max_retries})."

        # Log recovery attempt
        event = WorkflowEvent(
            channel_id=execution.channel_id,
            execution_id=execution.id,
            event_type="STAGE_RECOVERY_ATTEMPTED",
            stage_key=stage.stage_key,
            actor_type="HEALTH_MONITOR",
            details={
                "failure_count": execution.failure_count,
                "max_retries": max_retries,
                "error_category": error_category,
            },
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(event)
        await self.db.flush()
        return True

    async def _log_failure(
        self,
        execution: WorkflowExecution,
        stage: WorkflowStage,
        category: str,
        resolution: str,
    ) -> WorkflowFailure:
        """Create diagnostic failure entry."""
        failure = WorkflowFailure(
            channel_id=execution.channel_id,
            execution_id=execution.id,
            stage_key=stage.stage_key,
            job_id=stage.job_id,
            error_category=category,
            sanitized_error=f"Stage '{stage.stage_name}' failed or stalled.",
            retry_count=execution.failure_count,
            recovery_status="UNRESOLVED",
            suggested_resolution=resolution,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(failure)
        return failure

    async def get_system_health(self, channel_id: Optional[UUID] = None) -> Dict[str, Any]:
        """Aggregate health metrics across executions, queues, and workers."""
        # 1. Active executions
        active_stmt = select(func.count(WorkflowExecution.id)).where(
            WorkflowExecution.status.in_([WORKFLOW_STATUS_RUNNING, WORKFLOW_STATUS_RECOVERING])
        )
        if channel_id:
            active_stmt = active_stmt.where(WorkflowExecution.channel_id == channel_id)
        active_workflows = (await self.db.execute(active_stmt)).scalar() or 0

        # 2. Failed executions
        failed_stmt = select(func.count(WorkflowExecution.id)).where(
            WorkflowExecution.status == WORKFLOW_STATUS_FAILED
        )
        if channel_id:
            failed_stmt = failed_stmt.where(WorkflowExecution.channel_id == channel_id)
        failed_workflows = (await self.db.execute(failed_stmt)).scalar() or 0

        # 3. Completed executions
        completed_stmt = select(func.count(WorkflowExecution.id)).where(
            WorkflowExecution.status == WORKFLOW_STATUS_COMPLETED
        )
        if channel_id:
            completed_stmt = completed_stmt.where(WorkflowExecution.channel_id == channel_id)
        completed_workflows = (await self.db.execute(completed_stmt)).scalar() or 0

        # 4. Queued jobs in underlying queue
        queued_jobs_stmt = select(func.count(AutomationJob.id)).where(
            AutomationJob.status == JOB_STATUS_QUEUED
        )
        if channel_id:
            queued_jobs_stmt = queued_jobs_stmt.where(AutomationJob.channel_id == channel_id)
        queued_jobs = (await self.db.execute(queued_jobs_stmt)).scalar() or 0

        # 5. Stalled jobs count
        stalled_stages = await self.detect_stalled_stages(channel_id=channel_id)

        # 6. Last successful completion
        last_comp_stmt = (
            select(WorkflowExecution.completed_at)
            .where(WorkflowExecution.status == WORKFLOW_STATUS_COMPLETED)
            .order_by(WorkflowExecution.completed_at.desc())
        )
        if channel_id:
            last_comp_stmt = last_comp_stmt.where(WorkflowExecution.channel_id == channel_id)
        last_completed_at = (await self.db.execute(last_comp_stmt)).scalars().first()

        return {
            "status": "HEALTHY" if len(stalled_stages) == 0 else "DEGRADED",
            "active_workflows": active_workflows,
            "failed_workflows": failed_workflows,
            "completed_workflows": completed_workflows,
            "underlying_queued_jobs": queued_jobs,
            "stalled_stages_count": len(stalled_stages),
            "stalled_stage_keys": [s.stage_key for s in stalled_stages],
            "last_successful_completion": last_completed_at.isoformat() if last_completed_at else None,
            "monitored_at": datetime.now(timezone.utc).isoformat(),
        }
