"""Job Queue and Automation REST API endpoints."""

import uuid
import json
import asyncio
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.models.channel import Channel, ChannelSettings
from app.models.job import AutomationJob, JOB_STATUS_COMPLETED, JOB_STATUS_FAILED, JOB_STATUS_CANCELLED
from app.schemas.job import JobCreate, JobRead, JobProgressRead, JobListResponse
from app.api.deps import get_current_user
from app.services.job_queue import JobQueueService
from app.workers.registry import registry
from app.core.security import ROLE_SUPER_ADMIN
from app.core.logging import logger

router = APIRouter()


async def verify_job_tenant_access(
    job_id: uuid.UUID,
    current_user: User,
    db: AsyncSession,
) -> AutomationJob:
    """Helper to verify that a job exists and belongs to a channel owned by current_user."""
    stmt = (
        select(AutomationJob)
        .join(Channel, AutomationJob.channel_id == Channel.id)
        .where(AutomationJob.id == job_id)
    )
    result = await db.execute(stmt)
    job = result.scalars().first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    # Check ownership of channel
    channel_stmt = select(Channel).where(Channel.id == job.channel_id)
    channel_res = await db.execute(channel_stmt)
    channel = channel_res.scalars().first()

    if not channel or (channel.user_id != current_user.id and current_user.role != ROLE_SUPER_ADMIN):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    return job


@router.post("", response_model=JobRead, status_code=status.HTTP_201_CREATED, summary="Submit queue job")
async def create_job(
    job_in: JobCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AutomationJob:
    """Enqueue a new production or automation job with idempotency and quota checks."""
    # 1. Verify user owns target channel
    stmt = select(Channel).where(Channel.id == job_in.channel_id)
    res = await db.execute(stmt)
    channel = res.scalars().first()
    if not channel or (channel.user_id != current_user.id and current_user.role != ROLE_SUPER_ADMIN):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target channel not found",
        )

    # 2. Validate job type is registered
    try:
        registry.get_handler(job_in.job_type)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid or unregistered job type: '{job_in.job_type}'",
        )

    # 3. Budget Guardrail Check
    settings_stmt = select(ChannelSettings).where(ChannelSettings.channel_id == channel.id)
    settings_res = await db.execute(settings_stmt)
    channel_settings = settings_res.scalars().first()
    if channel_settings and channel_settings.max_monthly_spend_usd == 0.00:
        # Strict zero-dollar enforcement for billable tasks (M04 uses free test handlers)
        if job_in.payload.get("requires_paid_quota"):
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Operation rejected: Channel monthly budget cap is set to $0.00",
            )

    # 4. Enqueue via JobQueueService
    queue_service = JobQueueService(db)
    job, created = await queue_service.enqueue_job(
        channel_id=job_in.channel_id,
        job_type=job_in.job_type,
        payload=job_in.payload,
        idempotency_key=job_in.idempotency_key,
        priority=job_in.priority,
        scheduled_at=job_in.scheduled_at,
    )
    return job


@router.get("", response_model=JobListResponse, summary="List jobs for user")
async def list_jobs(
    channel_id: Optional[uuid.UUID] = Query(None, description="Optional channel filter"),
    job_status: Optional[str] = Query(None, alias="status", description="Optional status filter"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JobListResponse:
    """List jobs across user's channels with pagination and status filtering."""
    # Base filter: channels owned by current_user (or all if SUPER_ADMIN)
    query = select(AutomationJob).join(Channel, AutomationJob.channel_id == Channel.id)
    count_query = select(func.count(AutomationJob.id)).join(Channel, AutomationJob.channel_id == Channel.id)

    if current_user.role != ROLE_SUPER_ADMIN:
        query = query.where(Channel.user_id == current_user.id)
        count_query = count_query.where(Channel.user_id == current_user.id)

    if channel_id:
        query = query.where(AutomationJob.channel_id == channel_id)
        count_query = count_query.where(AutomationJob.channel_id == channel_id)

    if job_status:
        query = query.where(AutomationJob.status == job_status)
        count_query = count_query.where(AutomationJob.status == job_status)

    total_res = await db.execute(count_query)
    total = total_res.scalar() or 0

    query = query.order_by(AutomationJob.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    items_res = await db.execute(query)
    items = list(items_res.scalars().all())

    return JobListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{job_id}", response_model=JobRead, summary="Get job details")
async def get_job(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AutomationJob:
    """Retrieve full details of a single job with tenant isolation verified."""
    return await verify_job_tenant_access(job_id, current_user, db)


@router.get("/{job_id}/progress", response_model=JobProgressRead, summary="Get job progress")
async def get_job_progress(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AutomationJob:
    """Lightweight endpoint for polling progress percentage and current stage."""
    return await verify_job_tenant_access(job_id, current_user, db)


@router.post("/{job_id}/cancel", response_model=JobRead, summary="Cancel job")
async def cancel_job(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AutomationJob:
    """Cancel an active or queued job."""
    job = await verify_job_tenant_access(job_id, current_user, db)
    queue_service = JobQueueService(db)
    cancelled_job = await queue_service.mark_cancelled(job.id)
    return cancelled_job or job


@router.post("/{job_id}/retry", response_model=JobRead, summary="Manually retry failed job")
async def retry_job(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AutomationJob:
    """Reset a FAILED or CANCELLED job for re-execution."""
    job = await verify_job_tenant_access(job_id, current_user, db)
    queue_service = JobQueueService(db)
    try:
        retried_job = await queue_service.retry_job(job.id)
        return retried_job or job
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/{job_id}/progress-stream", summary="Stream job progress via SSE")
async def progress_stream(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Server-Sent Events (SSE) stream emitting real-time progress updates until completion."""
    # Verify access upfront
    await verify_job_tenant_access(job_id, current_user, db)

    async def event_generator():
        last_progress = -1
        last_stage = None

        while True:
            # Re-query status
            stmt = select(AutomationJob).where(AutomationJob.id == job_id)
            res = await db.execute(stmt)
            job = res.scalars().first()

            if not job:
                yield f"data: {json.dumps({'error': 'Job not found'})}\n\n"
                break

            # Emit only if changed or terminal
            if job.progress_percentage != last_progress or job.current_stage != last_stage or job.status in [JOB_STATUS_COMPLETED, JOB_STATUS_FAILED, JOB_STATUS_CANCELLED]:
                last_progress = job.progress_percentage
                last_stage = job.current_stage
                data = {
                    "id": str(job.id),
                    "status": job.status,
                    "progress_percentage": job.progress_percentage,
                    "current_stage": job.current_stage,
                    "error_log": job.error_log,
                }
                yield f"data: {json.dumps(data)}\n\n"

            if job.status in [JOB_STATUS_COMPLETED, JOB_STATUS_FAILED, JOB_STATUS_CANCELLED]:
                break

            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
