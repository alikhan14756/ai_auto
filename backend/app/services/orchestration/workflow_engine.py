"""Workflow State Machine Engine and Stage Orchestrator."""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple
from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload

from app.models.workflow import (
    WorkflowExecution,
    WorkflowStage,
    WorkflowEvent,
    WorkflowPolicy,
    WorkflowFailure,
    WORKFLOW_STATUS_DRAFT,
    WORKFLOW_STATUS_SCHEDULED,
    WORKFLOW_STATUS_READY,
    WORKFLOW_STATUS_RUNNING,
    WORKFLOW_STATUS_PAUSED,
    WORKFLOW_STATUS_WAITING_FOR_APPROVAL,
    WORKFLOW_STATUS_RECOVERING,
    WORKFLOW_STATUS_COMPLETED,
    WORKFLOW_STATUS_FAILED,
    WORKFLOW_STATUS_CANCELLED,
    STAGE_STATUS_PENDING,
    STAGE_STATUS_RUNNING,
    STAGE_STATUS_WAITING_APPROVAL,
    STAGE_STATUS_COMPLETED,
    STAGE_STATUS_FAILED,
    STAGE_STATUS_SKIPPED,
    ALLOWED_WORKFLOW_TRANSITIONS,
)
from app.models.job import (
    AutomationJob,
    JOB_STATUS_QUEUED,
    JOB_STATUS_PROCESSING,
    JOB_STATUS_COMPLETED,
    JOB_STATUS_FAILED,
)
from app.models.project import VideoProject
from app.services.orchestration.templates import get_template_by_key, TEMPLATE_LONG_FORM
from app.services.orchestration.policy_engine import PolicyEngine, PolicyViolationError
from app.services.orchestration.governor import ResourceGovernor


class InvalidStateTransitionError(Exception):
    """Raised when attempting an unauthorized status transition in the state machine."""
    pass


class WorkflowEngine:
    """State machine controller coordinating stages, approval gates, and durable queue dispatch."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.policy_engine = PolicyEngine(db)
        self.governor = ResourceGovernor(db)

    async def create_execution(
        self,
        channel_id: UUID,
        template_key: str = TEMPLATE_LONG_FORM,
        project_id: Optional[UUID] = None,
        definition_id: Optional[UUID] = None,
        context_data: Optional[Dict[str, Any]] = None,
        status: str = WORKFLOW_STATUS_DRAFT,
    ) -> WorkflowExecution:
        """Instantiate a new workflow execution and materialize all constituent stage records."""
        template = get_template_by_key(template_key)
        if not template:
            raise ValueError(f"Unknown workflow template: {template_key}")

        execution = WorkflowExecution(
            channel_id=channel_id,
            definition_id=definition_id,
            template_key=template_key,
            project_id=project_id,
            status=status,
            progress_percentage=0,
            context_data=context_data or {},
            failure_count=0,
        )
        self.db.add(execution)
        await self.db.flush()

        # Materialize stage records
        for s_def in template.get("stages", []):
            stage = WorkflowStage(
                execution=execution,
                stage_key=s_def["stage_key"],
                stage_name=s_def["stage_name"],
                job_type=s_def["job_type"],
                status=STAGE_STATUS_PENDING,
                order_index=s_def.get("order_index", 0),
                dependencies=s_def.get("dependencies", []),
                stage_inputs={},
                stage_outputs={},
            )
            self.db.add(stage)

        # Log creation event
        event = WorkflowEvent(
            channel_id=channel_id,
            execution_id=execution.id,
            event_type="WORKFLOW_CREATED",
            actor_type="USER",
            details={"template_key": template_key, "initial_status": status},
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(event)
        await self.db.flush()

        # Reload with eager stages loaded
        stmt = (
            select(WorkflowExecution)
            .where(WorkflowExecution.id == execution.id)
            .options(selectinload(WorkflowExecution.stages))
        )
        loaded = (await self.db.execute(stmt)).scalars().first()
        return loaded or execution

    def _transition_execution(
        self, execution: WorkflowExecution, target_status: str
    ) -> None:
        """Validate and apply a state transition on the workflow execution."""
        allowed = ALLOWED_WORKFLOW_TRANSITIONS.get(execution.status, set())
        if target_status not in allowed:
            raise InvalidStateTransitionError(
                f"Cannot transition workflow from '{execution.status}' to '{target_status}'. Allowed transitions: {list(allowed)}."
            )
        execution.status = target_status

    async def start_execution(self, execution_id: UUID) -> WorkflowExecution:
        """Authorize and initiate workflow execution, dispatching eligible initial stages."""
        stmt = (
            select(WorkflowExecution)
            .where(WorkflowExecution.id == execution_id)
            .options(selectinload(WorkflowExecution.stages))
        )
        execution = (await self.db.execute(stmt)).scalars().first()
        if not execution:
            raise ValueError(f"Workflow execution {execution_id} not found.")

        # Check policy authorization
        can_start, reason = await self.policy_engine.can_start_workflow(
            execution.channel_id, execution.template_key, "LONG_FORM"
        )
        if not can_start:
            raise PolicyViolationError(f"Cannot start workflow: {reason}")

        # Transition state: DRAFT -> READY -> RUNNING
        if execution.status == WORKFLOW_STATUS_DRAFT:
            self._transition_execution(execution, WORKFLOW_STATUS_READY)

        self._transition_execution(execution, WORKFLOW_STATUS_RUNNING)
        execution.started_at = datetime.now(timezone.utc)

        # Advance stages
        await self.advance_execution(execution)
        await self.db.flush()
        return execution

    async def pause_execution(self, execution_id: UUID) -> WorkflowExecution:
        """Suspend an active workflow execution."""
        stmt = (
            select(WorkflowExecution)
            .where(WorkflowExecution.id == execution_id)
            .options(selectinload(WorkflowExecution.stages))
        )
        execution = (await self.db.execute(stmt)).scalars().first()
        if not execution:
            raise ValueError(f"Workflow execution {execution_id} not found.")

        self._transition_execution(execution, WORKFLOW_STATUS_PAUSED)
        await self.db.flush()
        return execution

    async def resume_execution(self, execution_id: UUID) -> WorkflowExecution:
        """Resume a paused workflow execution."""
        stmt = (
            select(WorkflowExecution)
            .where(WorkflowExecution.id == execution_id)
            .options(selectinload(WorkflowExecution.stages))
        )
        execution = (await self.db.execute(stmt)).scalars().first()
        if not execution:
            raise ValueError(f"Workflow execution {execution_id} not found.")

        self._transition_execution(execution, WORKFLOW_STATUS_RUNNING)
        await self.advance_execution(execution)
        await self.db.flush()
        return execution

    async def cancel_execution(self, execution_id: UUID) -> WorkflowExecution:
        """Abort workflow execution and cancel pending stages."""
        stmt = (
            select(WorkflowExecution)
            .where(WorkflowExecution.id == execution_id)
            .options(selectinload(WorkflowExecution.stages))
        )
        execution = (await self.db.execute(stmt)).scalars().first()
        if not execution:
            raise ValueError(f"Workflow execution {execution_id} not found.")

        self._transition_execution(execution, WORKFLOW_STATUS_CANCELLED)

        # Mark all pending/running stages as SKIPPED
        stages_stmt = select(WorkflowStage).where(
            and_(
                WorkflowStage.execution_id == execution_id,
                WorkflowStage.status.in_([STAGE_STATUS_PENDING, STAGE_STATUS_RUNNING]),
            )
        )
        stages = (await self.db.execute(stages_stmt)).scalars().all()
        for stage in stages:
            stage.status = STAGE_STATUS_SKIPPED

        await self.db.flush()
        return execution

    async def approve_checkpoint(
        self, execution_id: UUID, checkpoint_name: str
    ) -> WorkflowExecution:
        """Record explicit human approval for a paused checkpoint and resume execution."""
        stmt = (
            select(WorkflowExecution)
            .where(WorkflowExecution.id == execution_id)
            .options(selectinload(WorkflowExecution.stages))
        )
        execution = (await self.db.execute(stmt)).scalars().first()
        if not execution:
            raise ValueError(f"Workflow execution {execution_id} not found.")

        if execution.status != WORKFLOW_STATUS_WAITING_FOR_APPROVAL:
            raise InvalidStateTransitionError(
                f"Workflow is in '{execution.status}', not WAITING_FOR_APPROVAL."
            )

        # Check if checkpoint is publishing - validate publishing authorization
        if checkpoint_name in ("stage_publishing", "publish"):
            can_pub, pub_reason = await self.policy_engine.validate_publishing_authorization(
                execution.channel_id, execution.project_id
            )
            if not can_pub:
                raise PolicyViolationError(f"Publishing authorization failed: {pub_reason}")

        # Clear checkpoint and resume
        execution.checkpoint_required = None
        self._transition_execution(execution, WORKFLOW_STATUS_RUNNING)

        # Mark the checkpoint stage as approved so advance_execution dispatches it
        for s in execution.stages:
            if s.stage_key == checkpoint_name:
                s.status = STAGE_STATUS_PENDING
                inputs = dict(s.stage_inputs or {})
                inputs["approval_granted"] = True
                s.stage_inputs = inputs

        # Log approval event
        event = WorkflowEvent(
            channel_id=execution.channel_id,
            execution_id=execution.id,
            event_type="CHECKPOINT_APPROVED",
            actor_type="USER",
            details={"checkpoint": checkpoint_name},
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(event)

        await self.advance_execution(execution)
        await self.db.flush()
        return execution

    async def advance_execution(self, execution: WorkflowExecution) -> None:
        """Inspect stage dependency graph and enqueue eligible next stages into M04 queue."""
        # Load all stages
        stages_stmt = (
            select(WorkflowStage)
            .where(WorkflowStage.execution_id == execution.id)
            .order_by(WorkflowStage.order_index)
        )
        stages = list((await self.db.execute(stages_stmt)).scalars().all())

        completed_keys = {s.stage_key for s in stages if s.status == STAGE_STATUS_COMPLETED}
        total_stages = len(stages)
        completed_count = len(completed_keys)

        # Update progress percentage
        if total_stages > 0:
            execution.progress_percentage = int((completed_count / total_stages) * 100)

        # If all stages completed, mark COMPLETED
        if completed_count == total_stages and total_stages > 0:
            self._transition_execution(execution, WORKFLOW_STATUS_COMPLETED)
            execution.completed_at = datetime.now(timezone.utc)
            execution.progress_percentage = 100
            return

        # Find eligible pending stages
        for stage in stages:
            if stage.status == STAGE_STATUS_PENDING:
                # Check dependencies
                deps = stage.dependencies or []
                if all(dep in completed_keys for dep in deps):
                    # Check if human approval is required
                    needs_approval = await self.policy_engine.requires_approval(
                        execution.channel_id, stage.stage_key, default_approval_required=False
                    )
                    is_already_approved = (stage.stage_inputs or {}).get("approval_granted", False)

                    if needs_approval and not is_already_approved and execution.status == WORKFLOW_STATUS_RUNNING:
                        # Halt at checkpoint
                        self._transition_execution(execution, WORKFLOW_STATUS_WAITING_FOR_APPROVAL)
                        execution.checkpoint_required = stage.stage_key
                        execution.current_stage_key = stage.stage_key
                        stage.status = STAGE_STATUS_WAITING_APPROVAL
                        return

                    # Check if stage is publishing - mandatory QA veto gate & YouTube OAuth checks
                    if stage.stage_key in ("stage_publishing", "publish"):
                        can_pub, pub_reason = await self.policy_engine.validate_publishing_authorization(
                            execution.channel_id, execution.project_id
                        )
                        if not can_pub:
                            self._transition_execution(execution, WORKFLOW_STATUS_WAITING_FOR_APPROVAL)
                            execution.checkpoint_required = stage.stage_key
                            execution.current_stage_key = stage.stage_key
                            stage.status = STAGE_STATUS_WAITING_APPROVAL
                            stage.error_message = pub_reason
                            return

                    # Dispatch stage to durable queue
                    await self._dispatch_stage_to_queue(execution, stage)
                    execution.current_stage_key = stage.stage_key
                    # In sequential mode, run one stage at a time
                    break

    async def _dispatch_stage_to_queue(
        self, execution: WorkflowExecution, stage: WorkflowStage
    ) -> None:
        """Create a durable AutomationJob in the PostgreSQL queue for this stage."""
        # Auto-provision VideoProject container if missing and not topic discovery
        if not execution.project_id and stage.job_type not in ("DISCOVER_TOPICS", "TOPIC_RESEARCH"):
            project_title = (execution.context_data or {}).get("title") or f"Production {execution.template_key} {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}"
            proj = VideoProject(
                channel_id=execution.channel_id,
                title=project_title,
                format="SHORTS" if "SHORTS" in execution.template_key else "LONG_FORM",
                state="IDEA",
            )
            self.db.add(proj)
            await self.db.flush()
            execution.project_id = proj.id

        idempotency_key = f"wf_stage_{execution.id}_{stage.stage_key}"

        # Build payload
        payload = {
            "workflow_execution_id": str(execution.id),
            "workflow_stage_id": str(stage.id),
            "stage_key": stage.stage_key,
            "project_id": str(execution.project_id) if execution.project_id else None,
            "channel_id": str(execution.channel_id),
            "inputs": stage.stage_inputs or {},
            "context_data": execution.context_data or {},
        }

        job = AutomationJob(
            channel_id=execution.channel_id,
            job_type=stage.job_type,
            payload=payload,
            idempotency_key=idempotency_key,
            status=JOB_STATUS_QUEUED,
            priority=20,
            scheduled_at=datetime.now(timezone.utc),
            current_stage=stage.stage_key,
        )
        self.db.add(job)
        await self.db.flush()

        stage.job_id = job.id
        stage.status = STAGE_STATUS_RUNNING
        stage.started_at = datetime.now(timezone.utc)

    async def record_stage_completed(
        self, stage_id: UUID, stage_outputs: Dict[str, Any]
    ) -> None:
        """Mark stage completed and trigger downstream pipeline advancement."""
        stage_stmt = select(WorkflowStage).where(WorkflowStage.id == stage_id)
        stage = (await self.db.execute(stage_stmt)).scalars().first()
        if not stage:
            return

        stage.status = STAGE_STATUS_COMPLETED
        stage.stage_outputs = stage_outputs
        stage.completed_at = datetime.now(timezone.utc)

        # Advance execution
        exec_stmt = select(WorkflowExecution).where(WorkflowExecution.id == stage.execution_id)
        execution = (await self.db.execute(exec_stmt)).scalars().first()
        if execution and execution.status == WORKFLOW_STATUS_RUNNING:
            await self.advance_execution(execution)

        await self.db.flush()

    async def record_stage_failed(
        self, stage_id: UUID, error_message: str
    ) -> None:
        """Handle stage failure and transition workflow execution."""
        stage_stmt = select(WorkflowStage).where(WorkflowStage.id == stage_id)
        stage = (await self.db.execute(stage_stmt)).scalars().first()
        if not stage:
            return

        stage.status = STAGE_STATUS_FAILED
        stage.error_message = error_message
        stage.completed_at = datetime.now(timezone.utc)

        exec_stmt = select(WorkflowExecution).where(WorkflowExecution.id == stage.execution_id)
        execution = (await self.db.execute(exec_stmt)).scalars().first()
        if execution:
            execution.status = WORKFLOW_STATUS_FAILED
            execution.error_message = f"Failed at stage '{stage.stage_key}': {error_message}"

            # Persist diagnostic failure record
            failure = WorkflowFailure(
                channel_id=execution.channel_id,
                execution_id=execution.id,
                stage_key=stage.stage_key,
                error_category="STAGE_EXECUTION_FAILURE",
                error_message=error_message,
                recovery_action="INSPECT_DIAGNOSTICS",
                created_at=datetime.now(timezone.utc),
            )
            self.db.add(failure)

            # Persist audit event
            event = WorkflowEvent(
                channel_id=execution.channel_id,
                execution_id=execution.id,
                event_type="STAGE_FAILED",
                stage_key=stage.stage_key,
                actor_type="SYSTEM",
                details={"error_message": error_message},
                created_at=datetime.now(timezone.utc),
            )
            self.db.add(event)

        await self.db.flush()
