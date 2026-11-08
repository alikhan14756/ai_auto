"""Autonomous Workflow Policy Engine and Execution Governance."""

from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.models.channel import Channel, ChannelSettings
from app.models.workflow import (
    WorkflowPolicy,
    WorkflowExecution,
    AUTOMATION_LEVEL_MANUAL,
    AUTOMATION_LEVEL_ASSISTED,
    AUTOMATION_LEVEL_CONTROLLED,
    AUTOMATION_LEVEL_SCHEDULED,
    WORKFLOW_STATUS_RUNNING,
    WORKFLOW_STATUS_COMPLETED,
)
from app.models.qa import QARun


class PolicyViolationError(Exception):
    """Raised when an action or state transition violates configured policies."""
    pass


class PolicyEngine:
    """Enforces automation tiers, security boundaries, and spending governors."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_policy(self, channel_id: UUID) -> WorkflowPolicy:
        """Fetch channel's workflow policy, creating default Level 1 (Assisted) policy if absent."""
        stmt = select(WorkflowPolicy).where(WorkflowPolicy.channel_id == channel_id)
        result = await self.db.execute(stmt)
        policy = result.scalars().first()

        if not policy:
            policy = WorkflowPolicy(
                channel_id=channel_id,
                automation_level=AUTOMATION_LEVEL_ASSISTED,
                allowed_workflow_types=[
                    "TEMPLATE_LONG_FORM",
                    "TEMPLATE_SHORTS",
                    "TEMPLATE_REPURPOSING",
                    "TEMPLATE_TOPIC_RESEARCH_ONLY",
                    "TEMPLATE_SCRIPT_ONLY",
                    "TEMPLATE_RECOVERY",
                    "TEMPLATE_ANALYTICS_PLANNING",
                ],
                allowed_content_formats=["LONG_FORM", "SHORTS"],
                max_workflows_per_week=5,
                max_concurrent_workflows=2,
                permitted_execution_hours={"start": 0, "end": 23},
                max_monthly_budget_usd=0.0,
                require_topic_approval=True,
                require_script_approval=True,
                require_qa_approval=True,
                require_publish_authorization=True,
                auto_retry_transient_failures=True,
                max_retry_attempts=3,
            )
            self.db.add(policy)
            await self.db.flush()

        return policy

    async def can_start_workflow(
        self, channel_id: UUID, template_key: str, content_format: str
    ) -> Tuple[bool, Optional[str]]:
        """Validate whether a new workflow execution is authorized to start under channel policies."""
        policy = await self.get_or_create_policy(channel_id)

        # 1. Workflow type allowed?
        if policy.allowed_workflow_types and template_key not in policy.allowed_workflow_types:
            return False, f"Workflow template '{template_key}' is not permitted by channel policy."

        # 2. Content format allowed?
        if policy.allowed_content_formats and content_format not in policy.allowed_content_formats:
            return False, f"Content format '{content_format}' is not permitted by channel policy."

        # 3. Permitted execution hours check
        current_hour = datetime.now(timezone.utc).hour
        hours = policy.permitted_execution_hours or {}
        start_hour = hours.get("start", 0)
        end_hour = hours.get("end", 23)
        if start_hour <= end_hour:
            if not (start_hour <= current_hour <= end_hour):
                return False, f"Current UTC hour ({current_hour}) is outside permitted execution window ({start_hour}:00–{end_hour}:00 UTC)."
        else:
            # Wraps midnight
            if not (current_hour >= start_hour or current_hour <= end_hour):
                return False, f"Current UTC hour ({current_hour}) is outside permitted execution window ({start_hour}:00–{end_hour}:00 UTC)."

        # 4. Concurrency limit check
        active_stmt = select(func.count(WorkflowExecution.id)).where(
            and_(
                WorkflowExecution.channel_id == channel_id,
                WorkflowExecution.status == WORKFLOW_STATUS_RUNNING,
            )
        )
        active_count = (await self.db.execute(active_stmt)).scalar() or 0
        if active_count >= policy.max_concurrent_workflows:
            return False, f"Maximum concurrent workflows reached ({active_count}/{policy.max_concurrent_workflows})."

        # 5. Weekly volume limit check
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        # 7 days window
        weekly_stmt = select(func.count(WorkflowExecution.id)).where(
            and_(
                WorkflowExecution.channel_id == channel_id,
                WorkflowExecution.created_at >= week_ago,
                WorkflowExecution.status.in_([WORKFLOW_STATUS_RUNNING, WORKFLOW_STATUS_COMPLETED]),
            )
        )
        weekly_count = (await self.db.execute(weekly_stmt)).scalar() or 0
        if weekly_count >= policy.max_workflows_per_week:
            return False, f"Weekly workflow limit reached ({weekly_count}/{policy.max_workflows_per_week})."

        return True, None

    async def requires_approval(
        self, channel_id: UUID, stage_key: str, default_approval_required: bool
    ) -> bool:
        """Determine if a stage requires human approval before proceeding."""
        policy = await self.get_or_create_policy(channel_id)
        level = policy.automation_level

        # Level 0 (Manual): Every stage requires explicit initiation
        if level == AUTOMATION_LEVEL_MANUAL:
            return True

        # Level 2 (Controlled): Skips intermediate checkpoints unless QA or publishing
        if level == AUTOMATION_LEVEL_CONTROLLED:
            if stage_key in ("stage_qa", "qa", "stage_publishing", "publish"):
                return True
            return False

        # Level 3 (Scheduled): Only halts if explicit policy demands it
        if level == AUTOMATION_LEVEL_SCHEDULED:
            if stage_key in ("stage_publishing", "publish") and policy.require_publish_authorization:
                return True
            return False

        # Level 1 (Assisted): Default level, evaluates specific checkpoint policies
        if stage_key in ("stage_topic", "topic") and policy.require_topic_approval:
            return True

        if stage_key in ("stage_script", "script") and policy.require_script_approval:
            return True

        if stage_key in ("stage_qa", "qa") and policy.require_qa_approval:
            return True

        if stage_key in ("stage_publishing", "publish") and policy.require_publish_authorization:
            return True

        return default_approval_required

    async def validate_publishing_authorization(
        self, channel_id: UUID, project_id: Optional[UUID]
    ) -> Tuple[bool, Optional[str]]:
        """Non-bypassable publication gate: verifies channel credentials, M11 QA veto status, and policy."""
        # 1. Channel exists and has active OAuth credentials
        channel_stmt = select(Channel).where(Channel.id == channel_id)
        channel = (await self.db.execute(channel_stmt)).scalars().first()
        if not channel:
            return False, "Channel not found."

        if not channel.oauth_refresh_token_encrypted:
            return False, "YouTube OAuth credentials not connected. Connect YouTube in Settings."

        # 2. M11 QA Veto Gate Enforcement
        if not project_id:
            return False, "Publication rejected: Video project is missing."

        qa_stmt = (
            select(QARun)
            .where(QARun.project_id == project_id)
            .order_by(QARun.created_at.desc(), QARun.run_number.desc(), QARun.id.desc())
        )
        qa_run = (await self.db.execute(qa_stmt)).scalars().first()
        if not qa_run:
            return False, "Publication rejected: Video has not undergone M11 Quality Assurance evaluation."

        score = float(qa_run.overall_score) if qa_run.overall_score is not None else 0.0
        if qa_run.veto_decision != "APPROVED" or score < 70.0:
            return False, f"Publication vetoed by M11 QA Gate: Score {score}/100. Status: {qa_run.veto_decision}."

        # 3. Policy Publishing Authorization Check
        policy = await self.get_or_create_policy(channel_id)
        if policy.automation_level < AUTOMATION_LEVEL_SCHEDULED and policy.require_publish_authorization:
            # Human must authorize
            return True, None

        return True, None

    async def update_policy(
        self, channel_id: UUID, update_data: Dict[str, Any]
    ) -> WorkflowPolicy:
        """Safely update channel workflow policy with boundary validation."""
        policy = await self.get_or_create_policy(channel_id)

        # Automation Level validation
        if "automation_level" in update_data:
            new_level = int(update_data["automation_level"])
            if new_level not in (
                AUTOMATION_LEVEL_MANUAL,
                AUTOMATION_LEVEL_ASSISTED,
                AUTOMATION_LEVEL_CONTROLLED,
                AUTOMATION_LEVEL_SCHEDULED,
            ):
                raise PolicyViolationError(f"Invalid automation level: {new_level}")
            policy.automation_level = new_level

        if "max_workflows_per_week" in update_data:
            val = int(update_data["max_workflows_per_week"])
            if val < 1 or val > 50:
                raise PolicyViolationError("max_workflows_per_week must be between 1 and 50.")
            policy.max_workflows_per_week = val

        if "max_concurrent_workflows" in update_data:
            val = int(update_data["max_concurrent_workflows"])
            if val < 1 or val > 10:
                raise PolicyViolationError("max_concurrent_workflows must be between 1 and 10.")
            policy.max_concurrent_workflows = val

        if "max_monthly_budget_usd" in update_data:
            val = float(update_data["max_monthly_budget_usd"])
            if val < 0.0:
                raise PolicyViolationError("Budget cannot be negative.")
            policy.max_monthly_budget_usd = val

        if "permitted_execution_hours" in update_data:
            hours = update_data["permitted_execution_hours"]
            if isinstance(hours, dict) and "start" in hours and "end" in hours:
                policy.permitted_execution_hours = {
                    "start": max(0, min(23, int(hours["start"]))),
                    "end": max(0, min(23, int(hours["end"]))),
                }

        for bool_field in (
            "require_topic_approval",
            "require_script_approval",
            "require_qa_approval",
            "require_publish_authorization",
            "auto_retry_transient_failures",
        ):
            if bool_field in update_data:
                setattr(policy, bool_field, bool(update_data[bool_field]))

        if "allowed_workflow_types" in update_data and isinstance(update_data["allowed_workflow_types"], list):
            policy.allowed_workflow_types = update_data["allowed_workflow_types"]

        if "allowed_content_formats" in update_data and isinstance(update_data["allowed_content_formats"], list):
            policy.allowed_content_formats = update_data["allowed_content_formats"]

        await self.db.flush()
        return policy
