"""FastAPI REST endpoints for channel automation policies and permissions."""

from typing import Optional, List, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.channel import Channel
from app.models.workflow import WorkflowPolicy, WorkflowEvent
from app.schemas.workflow import (
    WorkflowPolicyResponse,
    WorkflowPolicyUpdate,
    WorkflowEventResponse,
)
from app.services.orchestration.policy_engine import PolicyEngine, PolicyViolationError

router = APIRouter(prefix="", tags=["Automation Policies & Governance"])


async def _get_channel_for_user(
    db: AsyncSession, channel_id: Optional[UUID], user: User
) -> Channel:
    if channel_id:
        stmt = select(Channel).where(Channel.id == channel_id)
        res = await db.execute(stmt)
        channel = res.scalar_one_or_none()
        if not channel:
            raise HTTPException(status_code=404, detail="Channel not found")
        if user.role != "SUPER_ADMIN" and channel.user_id != user.id:
            raise HTTPException(status_code=403, detail="Unauthorized channel access")
        return channel

    stmt = select(Channel).where(Channel.user_id == user.id)
    res = await db.execute(stmt)
    channel = res.scalars().first()
    if not channel:
        raise HTTPException(status_code=404, detail="No channel found for user")
    return channel


@router.get("/policies", response_model=WorkflowPolicyResponse)
async def get_policies(
    channel_id: Optional[UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve channel automation policy and execution boundaries."""
    channel = await _get_channel_for_user(db, channel_id, current_user)
    engine = PolicyEngine(db)
    policy = await engine.get_or_create_policy(channel.id)
    return WorkflowPolicyResponse.model_validate(policy)


@router.patch("/policies", response_model=WorkflowPolicyResponse)
async def update_policies(
    payload: WorkflowPolicyUpdate,
    channel_id: Optional[UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Safely update channel automation policy and limits."""
    channel = await _get_channel_for_user(db, channel_id, current_user)
    engine = PolicyEngine(db)
    try:
        update_data = payload.model_dump(exclude_unset=True)
        updated = await engine.update_policy(channel.id, update_data)
        await db.commit()
        return WorkflowPolicyResponse.model_validate(updated)
    except PolicyViolationError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/permissions")
async def get_permissions(
    channel_id: Optional[UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Inspect active automation permissions and execution constraints."""
    channel = await _get_channel_for_user(db, channel_id, current_user)
    engine = PolicyEngine(db)
    policy = await engine.get_or_create_policy(channel.id)

    level_names = {
        0: "Level 0: Manual",
        1: "Level 1: Assisted (Default)",
        2: "Level 2: Controlled Automation",
        3: "Level 3: Scheduled Automation",
    }

    return {
        "channel_id": str(channel.id),
        "user_role": current_user.role,
        "automation_level": policy.automation_level,
        "automation_tier_name": level_names.get(policy.automation_level, "Custom"),
        "can_auto_start_workflows": policy.automation_level >= 2,
        "can_auto_publish": policy.automation_level == 3 and not policy.require_publish_authorization,
        "is_qa_veto_gate_mandatory": True,  # Non-bypassable
        "is_youtube_oauth_connected": bool(channel.oauth_refresh_token_encrypted),
        "monthly_budget_usd": policy.max_monthly_budget_usd,
        "max_concurrent_workflows": policy.max_concurrent_workflows,
    }


@router.get("/audit", response_model=List[WorkflowEventResponse])
async def get_audit_trail(
    channel_id: Optional[UUID] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetch append-only audit trail of automation and policy events."""
    channel = await _get_channel_for_user(db, channel_id, current_user)

    stmt = (
        select(WorkflowEvent)
        .where(WorkflowEvent.channel_id == channel.id)
        .order_by(desc(WorkflowEvent.created_at))
        .limit(limit)
    )
    events = (await db.execute(stmt)).scalars().all()
    return [WorkflowEventResponse.model_validate(ev) for ev in events]
