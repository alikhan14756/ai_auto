"""FastAPI REST endpoints for production planning, opportunities, and calendar."""

from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.channel import Channel
from app.models.workflow import WorkflowSchedule, OptimizationRecommendation
from app.schemas.workflow import (
    WorkflowScheduleCreate,
    WorkflowScheduleUpdate,
    WorkflowScheduleResponse,
    OptimizationRecommendationResponse,
)
from app.services.orchestration.production_planner import ProductionPlanner

router = APIRouter(prefix="", tags=["Production Planning & Calendar"])


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


@router.get("/opportunities", response_model=List[OptimizationRecommendationResponse])
async def get_opportunities(
    channel_id: Optional[UUID] = Query(None),
    refresh: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve content strategy opportunities backed by M13 performance intelligence."""
    channel = await _get_channel_for_user(db, channel_id, current_user)
    planner = ProductionPlanner(db)

    if refresh:
        recs = await planner.discover_content_opportunities(channel.id)
        await db.commit()
        return [OptimizationRecommendationResponse.model_validate(r) for r in recs]

    stmt = (
        select(OptimizationRecommendation)
        .where(OptimizationRecommendation.channel_id == channel.id)
        .order_by(desc(OptimizationRecommendation.created_at))
    )
    existing = list((await db.execute(stmt)).scalars().all())

    # If empty, discover initially
    if not existing:
        existing = await planner.discover_content_opportunities(channel.id)
        await db.commit()

    return [OptimizationRecommendationResponse.model_validate(r) for r in existing]


@router.post("/opportunities/{id}/accept")
async def accept_opportunity(
    id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Accept an opportunity, marking it for production planning."""
    stmt = select(OptimizationRecommendation).where(OptimizationRecommendation.id == id)
    rec = (await db.execute(stmt)).scalars().first()
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    await _get_channel_for_user(db, rec.channel_id, current_user)

    rec.status = "ACCEPTED"
    await db.commit()
    return {"id": str(id), "status": "ACCEPTED", "message": "Opportunity accepted."}


@router.post("/opportunities/{id}/reject")
async def reject_opportunity(
    id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Dismiss an opportunity."""
    stmt = select(OptimizationRecommendation).where(OptimizationRecommendation.id == id)
    rec = (await db.execute(stmt)).scalars().first()
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    await _get_channel_for_user(db, rec.channel_id, current_user)

    rec.status = "DISMISSED"
    await db.commit()
    return {"id": str(id), "status": "DISMISSED", "message": "Opportunity dismissed."}


@router.get("/calendar", response_model=List[WorkflowScheduleResponse])
async def list_calendar_events(
    channel_id: Optional[UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List production calendar schedules for the channel."""
    channel = await _get_channel_for_user(db, channel_id, current_user)

    stmt = (
        select(WorkflowSchedule)
        .where(WorkflowSchedule.channel_id == channel.id)
        .order_by(WorkflowSchedule.planned_start_at.asc())
    )
    events = (await db.execute(stmt)).scalars().all()
    return [WorkflowScheduleResponse.model_validate(ev) for ev in events]


@router.post("/calendar", response_model=WorkflowScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_calendar_event(
    payload: WorkflowScheduleCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Schedule a video production on the calendar with conflict validation."""
    channel = await _get_channel_for_user(db, payload.channel_id, current_user)
    planner = ProductionPlanner(db)

    try:
        schedule = await planner.schedule_production(
            channel_id=channel.id,
            title=payload.title,
            content_format=payload.content_format,
            planned_start_at=payload.planned_start_at,
            planned_publish_at=payload.planned_publish_at,
            timezone_str=payload.timezone,
        )
        await db.commit()
        await db.refresh(schedule)
        return WorkflowScheduleResponse.model_validate(schedule)
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/calendar/{event_id}", response_model=WorkflowScheduleResponse)
async def update_calendar_event(
    event_id: UUID,
    payload: WorkflowScheduleUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reschedule or update a calendar event."""
    stmt = select(WorkflowSchedule).where(WorkflowSchedule.id == event_id)
    event = (await db.execute(stmt)).scalars().first()
    if not event:
        raise HTTPException(status_code=404, detail="Calendar event not found")

    await _get_channel_for_user(db, event.channel_id, current_user)

    if payload.title is not None:
        event.title = payload.title
    if payload.planned_start_at is not None:
        event.planned_start_at = payload.planned_start_at
    if payload.planned_publish_at is not None:
        event.planned_publish_at = payload.planned_publish_at
    if payload.timezone is not None:
        event.timezone = payload.timezone
    if payload.status is not None:
        event.status = payload.status

    await db.commit()
    await db.refresh(event)
    return WorkflowScheduleResponse.model_validate(event)
