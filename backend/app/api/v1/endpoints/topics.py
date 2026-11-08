"""Topic research and management REST API endpoints."""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, get_current_active_user
from app.models.channel import Channel
from app.models.job import AutomationJob
from app.models.topic import Topic, ResearchSource
from app.models.user import User
from app.providers.ai.base import AIBudgetExceededError, AIProviderError
from app.providers.ai.factory import get_ai_provider
from app.schemas.job import JobRead
from app.schemas.topic import (
    TopicListResponse,
    TopicResearchTriggerRequest,
    TopicResponse,
    TopicStatusUpdate,
)
from app.services.job_queue import JobQueueService
from app.services.topic_research import TopicResearchService

router = APIRouter()


async def _verify_channel_access(channel_id: UUID, user: User, db: AsyncSession) -> Channel:
    """Ensure channel exists and belongs to the authenticated user (unless super admin)."""
    stmt = select(Channel).where(Channel.id == channel_id)
    res = await db.execute(stmt)
    channel = res.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found.")
    if channel.user_id != user.id and user.role != "SUPER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this channel.",
        )
    return channel


@router.post("/research", response_model=JobRead, status_code=status.HTTP_202_ACCEPTED)
async def trigger_topic_research_job(
    request: TopicResearchTriggerRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Enqueue an asynchronous topic research job into the durable worker queue."""
    await _verify_channel_access(request.channel_id, current_user, db)

    queue_service = JobQueueService(db)
    job, _ = await queue_service.enqueue_job(
        channel_id=request.channel_id,
        job_type="DISCOVER_TOPICS",
        payload={
            "channel_id": str(request.channel_id),
            "niche_override": request.niche_override,
            "count": request.count,
        },
        priority=2,
    )
    return job


@router.post("/sync", response_model=List[TopicResponse], status_code=status.HTTP_201_CREATED)
async def trigger_topic_research_sync(
    request: TopicResearchTriggerRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Synchronously execute topic research and return the newly generated topics immediately."""
    await _verify_channel_access(request.channel_id, current_user, db)

    try:
        service = TopicResearchService(provider=get_ai_provider())
        topics = await service.discover_and_persist_topics(
            channel_id=request.channel_id,
            db=db,
            niche_override=request.niche_override,
            count=request.count,
        )
        return topics
    except AIBudgetExceededError as exc:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=str(exc),
        )
    except AIProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI Provider error: {str(exc)}",
        )


@router.get("", response_model=TopicListResponse)
async def list_topics(
    channel_id: UUID = Query(..., description="Target Channel ID"),
    topic_status: Optional[str] = Query(None, alias="status", description="Filter by DISCOVERED, SELECTED, ARCHIVED"),
    min_score: Optional[float] = Query(None, ge=0.0, le=100.0, description="Minimum opportunity score filter"),
    search: Optional[str] = Query(None, description="Search term in title or niche"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Retrieve scored topics for a channel with optional filtering and pagination."""
    await _verify_channel_access(channel_id, current_user, db)

    query = (
        select(Topic)
        .options(selectinload(Topic.research_sources))
        .where(Topic.channel_id == channel_id)
    )

    if topic_status:
        query = query.where(Topic.status == topic_status.upper())
    if min_score is not None:
        query = query.where(Topic.opportunity_score >= min_score)
    if search:
        pattern = f"%{search}%"
        query = query.where((Topic.title.ilike(pattern)) | (Topic.niche_category.ilike(pattern)))

    # Total count
    count_stmt = select(func.count()).select_from(query.subquery())
    total_res = await db.execute(count_stmt)
    total = total_res.scalar() or 0

    # Paginate ordered by highest opportunity score
    query = query.order_by(Topic.opportunity_score.desc(), Topic.created_at.desc()).offset(skip).limit(limit)
    res = await db.execute(query)
    items = list(res.scalars().all())

    return TopicListResponse(items=items, total=total)


@router.get("/{topic_id}", response_model=TopicResponse)
async def get_topic(
    topic_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Retrieve detailed topic metadata and verified research sources."""
    stmt = (
        select(Topic)
        .options(selectinload(Topic.research_sources))
        .where(Topic.id == topic_id)
    )
    res = await db.execute(stmt)
    topic = res.scalar_one_or_none()
    if not topic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found.")

    await _verify_channel_access(topic.channel_id, current_user, db)
    return topic


@router.patch("/{topic_id}/status", response_model=TopicResponse)
async def update_topic_status(
    topic_id: UUID,
    payload: TopicStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update topic workflow status (e.g. DISCOVERED -> SELECTED or ARCHIVED)."""
    stmt = (
        select(Topic)
        .options(selectinload(Topic.research_sources))
        .where(Topic.id == topic_id)
    )
    res = await db.execute(stmt)
    topic = res.scalar_one_or_none()
    if not topic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found.")

    await _verify_channel_access(topic.channel_id, current_user, db)

    topic.status = payload.status
    await db.commit()
    await db.refresh(topic)
    return topic


@router.post("/{topic_id}/approve", response_model=TopicResponse)
async def approve_topic(
    topic_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Approve topic for video production (sets status to SELECTED)."""
    return await update_topic_status(
        topic_id=topic_id,
        payload=TopicStatusUpdate(status="SELECTED"),
        db=db,
        current_user=current_user,
    )


@router.post("/{topic_id}/reject", response_model=TopicResponse)
async def reject_topic(
    topic_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Reject and archive topic (sets status to ARCHIVED)."""
    return await update_topic_status(
        topic_id=topic_id,
        payload=TopicStatusUpdate(status="ARCHIVED"),
        db=db,
        current_user=current_user,
    )
