"""Resource usage and budget governor."""

from datetime import datetime, timezone
from typing import Optional, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.models.channel import ChannelSettings
from app.models.workflow import ResourceUsageRecord, WorkflowPolicy


class BudgetExceededError(Exception):
    """Raised when an operation would exceed configured spending limits."""
    pass


class ResourceGovernor:
    """Enforces zero-dollar default budget and monitors resource consumption."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_usage(
        self,
        channel_id: UUID,
        resource_type: str,
        amount_used: float,
        unit: str,
        estimated_cost_usd: float = 0.0,
        execution_id: Optional[UUID] = None,
    ) -> ResourceUsageRecord:
        """Persist a resource consumption record."""
        record = ResourceUsageRecord(
            channel_id=channel_id,
            execution_id=execution_id,
            resource_type=resource_type,
            amount_used=amount_used,
            unit=unit,
            estimated_cost_usd=estimated_cost_usd,
            measured_at=datetime.now(timezone.utc),
        )
        self.db.add(record)
        await self.db.flush()
        return record

    async def check_budget_availability(
        self, channel_id: UUID, expected_cost_usd: float = 0.0
    ) -> bool:
        """Validate if the channel has budget available for an operation."""
        # 1. Fetch channel policy
        policy_stmt = select(WorkflowPolicy).where(WorkflowPolicy.channel_id == channel_id)
        policy = (await self.db.execute(policy_stmt)).scalars().first()
        max_budget = policy.max_monthly_budget_usd if policy else 0.0

        # Also check channel settings
        settings_stmt = select(ChannelSettings).where(ChannelSettings.channel_id == channel_id)
        settings = (await self.db.execute(settings_stmt)).scalars().first()
        settings_budget = float(settings.max_monthly_spend_usd) if settings else 0.0

        effective_ceiling = max(max_budget, settings_budget)

        # If zero-dollar ceiling and expected cost > 0, reject
        if effective_ceiling <= 0.0 and expected_cost_usd > 0.0:
            return False

        # Calculate current monthly spend
        first_of_month = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        spend_stmt = select(func.sum(ResourceUsageRecord.estimated_cost_usd)).where(
            and_(
                ResourceUsageRecord.channel_id == channel_id,
                ResourceUsageRecord.measured_at >= first_of_month,
            )
        )
        current_spend = (await self.db.execute(spend_stmt)).scalar() or 0.0

        if (current_spend + expected_cost_usd) > effective_ceiling:
            return False

        return True

    async def get_resource_summary(self, channel_id: UUID) -> Dict[str, Any]:
        """Aggregate total and current-month resource usage telemetry."""
        first_of_month = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Monthly spend
        spend_stmt = select(func.sum(ResourceUsageRecord.estimated_cost_usd)).where(
            and_(
                ResourceUsageRecord.channel_id == channel_id,
                ResourceUsageRecord.measured_at >= first_of_month,
            )
        )
        current_month_spend = (await self.db.execute(spend_stmt)).scalar() or 0.0

        # Budget ceiling
        policy_stmt = select(WorkflowPolicy).where(WorkflowPolicy.channel_id == channel_id)
        policy = (await self.db.execute(policy_stmt)).scalars().first()
        budget_limit = policy.max_monthly_budget_usd if policy else 0.0

        # Breakdown by resource type
        usage_stmt = (
            select(
                ResourceUsageRecord.resource_type,
                func.sum(ResourceUsageRecord.amount_used).label("total_amount"),
                ResourceUsageRecord.unit,
            )
            .where(
                and_(
                    ResourceUsageRecord.channel_id == channel_id,
                    ResourceUsageRecord.measured_at >= first_of_month,
                )
            )
            .group_by(ResourceUsageRecord.resource_type, ResourceUsageRecord.unit)
        )
        results = (await self.db.execute(usage_stmt)).all()

        breakdown = {}
        for r_type, total, unit in results:
            breakdown[r_type] = {
                "amount": float(total or 0.0),
                "unit": unit,
            }

        return {
            "channel_id": str(channel_id),
            "current_month_spend_usd": round(float(current_month_spend), 4),
            "monthly_budget_usd": float(budget_limit),
            "budget_remaining_usd": max(0.0, float(budget_limit) - float(current_month_spend)),
            "is_budget_capped": current_month_spend >= budget_limit,
            "resource_breakdown": breakdown,
        }
