"""FastAPI REST endpoints for production health, resource governance, and failure monitoring."""

from typing import Optional, List, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.channel import Channel
from app.models.workflow import WorkflowFailure
from app.schemas.workflow import (
    ProductionHealthResponse,
    ResourceUsageSummaryResponse,
    WorkflowFailureResponse,
)
from app.services.orchestration.health_monitor import ProductionHealthMonitor
from app.services.orchestration.governor import ResourceGovernor

router = APIRouter(prefix="", tags=["System Health & Resource Governance"])


async def _get_channel_for_user(
    db: AsyncSession, channel_id: Optional[UUID], user: User
) -> Optional[Channel]:
    if not channel_id:
        stmt = select(Channel).where(Channel.user_id == user.id)
        res = await db.execute(stmt)
        return res.scalars().first()

    stmt = select(Channel).where(Channel.id == channel_id)
    res = await db.execute(stmt)
    channel = res.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    if user.role != "SUPER_ADMIN" and channel.user_id != user.id:
        raise HTTPException(status_code=403, detail="Unauthorized channel access")
    return channel


@router.get("/production-health", response_model=ProductionHealthResponse)
async def get_production_health(
    channel_id: Optional[UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve production health, active workflows, stalled stages, and watchdog status."""
    channel = await _get_channel_for_user(db, channel_id, current_user)
    monitor = ProductionHealthMonitor(db)
    health = await monitor.get_system_health(channel_id=channel.id if channel else None)
    return ProductionHealthResponse(**health)


@router.get("/resource-usage", response_model=ResourceUsageSummaryResponse)
async def get_resource_usage(
    channel_id: Optional[UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve current monthly resource consumption and breakdown."""
    channel = await _get_channel_for_user(db, channel_id, current_user)
    if not channel:
        raise HTTPException(status_code=404, detail="No channel found for current user")

    governor = ResourceGovernor(db)
    summary = await governor.get_resource_summary(channel.id)
    return ResourceUsageSummaryResponse(**summary)


@router.get("/budget-status")
async def get_budget_status(
    channel_id: Optional[UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Inspect current spending ceiling and zero-dollar budget compliance."""
    channel = await _get_channel_for_user(db, channel_id, current_user)
    if not channel:
        raise HTTPException(status_code=404, detail="No channel found for current user")

    governor = ResourceGovernor(db)
    summary = await governor.get_resource_summary(channel.id)
    return {
        "channel_id": str(channel.id),
        "monthly_budget_usd": summary["monthly_budget_usd"],
        "current_month_spend_usd": summary["current_month_spend_usd"],
        "budget_remaining_usd": summary["budget_remaining_usd"],
        "is_zero_dollar_budget": summary["monthly_budget_usd"] <= 0.0,
        "is_capped": summary["is_budget_capped"],
    }


@router.get("/failures", response_model=List[WorkflowFailureResponse])
async def list_failures(
    channel_id: Optional[UUID] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List diagnostic workflow failure logs and recovery statuses."""
    channel = await _get_channel_for_user(db, channel_id, current_user)
    if not channel:
        raise HTTPException(status_code=404, detail="No channel found for current user")

    stmt = (
        select(WorkflowFailure)
        .where(WorkflowFailure.channel_id == channel.id)
        .order_by(desc(WorkflowFailure.created_at))
        .limit(limit)
    )
    failures = (await db.execute(stmt)).scalars().all()
    return [WorkflowFailureResponse.model_validate(f) for f in failures]
