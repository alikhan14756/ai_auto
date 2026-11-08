"""Token consumption metering, cost calculation, and budget circuit-breaker service."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.channel import ChannelSettings
from app.models.usage import ProviderUsage
from app.providers.ai.base import AIBudgetExceededError


class UsageTrackingService:
    """Service to track LLM token usage and enforce channel hard budget guardrails."""

    @staticmethod
    def get_current_month_start() -> datetime:
        """Return the start of the current calendar month in UTC."""
        now = datetime.now(timezone.utc)
        return datetime(now.year, now.month, 1, 0, 0, 0, tzinfo=timezone.utc)

    @classmethod
    async def get_current_month_spend(cls, channel_id: UUID, db: AsyncSession) -> float:
        """Sum cost_usd for this channel recorded since the 1st of the current month."""
        month_start = cls.get_current_month_start()
        stmt = (
            select(func.coalesce(func.sum(ProviderUsage.cost_usd), 0.0))
            .where(
                ProviderUsage.channel_id == channel_id,
                ProviderUsage.recorded_at >= month_start,
            )
        )
        result = await db.execute(stmt)
        spend = float(result.scalar() or 0.0)
        return round(spend, 6)

    @classmethod
    async def check_budget_guardrail(
        cls,
        channel_id: UUID,
        db: AsyncSession,
        estimated_additional_cost: float = 0.0,
    ) -> None:
        """Enforce monthly budget limit.
        
        Raises AIBudgetExceededError if adding the estimated cost would exceed
        the channel's configured max_monthly_spend_usd.
        Default max_monthly_spend_usd is 0.00 (hard stop for paid tokens).
        """
        # Load channel settings
        stmt = select(ChannelSettings).where(ChannelSettings.channel_id == channel_id)
        result = await db.execute(stmt)
        settings = result.scalar_one_or_none()

        max_spend = float(settings.max_monthly_spend_usd) if settings else 0.00
        current_spend = await cls.get_current_month_spend(channel_id, db)

        if max_spend <= 0.00:
            # $0.00 budget: Only zero-cost calls allowed
            if current_spend > 0.00 or estimated_additional_cost > 0.00:
                raise AIBudgetExceededError(
                    f"Channel monthly spending cap is $0.00 (Free Tier only). "
                    f"Current spend: ${current_spend:.4f}. Paid inference blocked.",
                    provider="BUDGET_CIRCUIT_BREAKER",
                )
            return

        if (current_spend + estimated_additional_cost) > max_spend:
            raise AIBudgetExceededError(
                f"Channel monthly spending limit (${max_spend:.2f}) reached or exceeded. "
                f"Current spend: ${current_spend:.4f}. Additional cost: ${estimated_additional_cost:.4f}.",
                provider="BUDGET_CIRCUIT_BREAKER",
            )

    @classmethod
    async def record_usage(
        cls,
        channel_id: UUID,
        provider_name: str,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
        db: AsyncSession,
    ) -> ProviderUsage:
        """Record token consumption and cost into ProviderUsage ledger."""
        usage_entry = ProviderUsage(
            channel_id=channel_id,
            provider_name=provider_name,
            model_name=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
        )
        db.add(usage_entry)
        await db.commit()
        await db.refresh(usage_entry)
        logger.info(
            f"Logged usage for channel {channel_id}: {provider_name}/{model_name} "
            f"({input_tokens} in, {output_tokens} out, ${cost_usd:.6f})"
        )
        return usage_entry

    @classmethod
    async def get_channel_usage_summary(
        cls,
        channel_id: UUID,
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """Aggregate usage analytics, token consumption, and budget status for a channel."""
        month_start = cls.get_current_month_start()

        # Monthly spend and tokens
        month_stmt = (
            select(
                func.coalesce(func.sum(ProviderUsage.cost_usd), 0.0),
                func.coalesce(func.sum(ProviderUsage.input_tokens), 0),
                func.coalesce(func.sum(ProviderUsage.output_tokens), 0),
                func.count(ProviderUsage.id),
            )
            .where(
                ProviderUsage.channel_id == channel_id,
                ProviderUsage.recorded_at >= month_start,
            )
        )
        m_res = await db.execute(month_stmt)
        m_row = m_res.fetchone()
        month_spend = float(m_row[0] or 0.0)
        month_in_tokens = int(m_row[1] or 0)
        month_out_tokens = int(m_row[2] or 0)
        month_requests = int(m_row[3] or 0)

        # Settings
        s_stmt = select(ChannelSettings).where(ChannelSettings.channel_id == channel_id)
        s_res = await db.execute(s_stmt)
        channel_settings = s_res.scalar_one_or_none()
        max_spend = float(channel_settings.max_monthly_spend_usd) if channel_settings else 0.00

        # Breakdown by model
        breakdown_stmt = (
            select(
                ProviderUsage.model_name,
                func.count(ProviderUsage.id).label("requests"),
                func.sum(ProviderUsage.input_tokens).label("in_tokens"),
                func.sum(ProviderUsage.output_tokens).label("out_tokens"),
                func.sum(ProviderUsage.cost_usd).label("cost"),
            )
            .where(
                ProviderUsage.channel_id == channel_id,
                ProviderUsage.recorded_at >= month_start,
            )
            .group_by(ProviderUsage.model_name)
        )
        b_res = await db.execute(breakdown_stmt)
        breakdowns = []
        for r in b_res.fetchall():
            breakdowns.append({
                "model_name": r[0],
                "requests": int(r[1] or 0),
                "input_tokens": int(r[2] or 0),
                "output_tokens": int(r[3] or 0),
                "cost_usd": round(float(r[4] or 0.0), 6),
            })

        return {
            "current_month_spend_usd": round(month_spend, 4),
            "max_monthly_spend_usd": max_spend,
            "is_budget_exceeded": (month_spend >= max_spend) if max_spend > 0 else (month_spend > 0),
            "current_month_input_tokens": month_in_tokens,
            "current_month_output_tokens": month_out_tokens,
            "current_month_total_tokens": month_in_tokens + month_out_tokens,
            "total_requests": month_requests,
            "breakdown_by_model": breakdowns,
        }
