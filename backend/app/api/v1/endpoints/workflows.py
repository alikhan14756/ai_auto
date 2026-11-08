"""FastAPI REST endpoints for workflow executions."""

from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, and_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.channel import Channel
from app.models.workflow import (
    WorkflowExecution,
    WorkflowStage,
    WorkflowEvent,
    VALID_WORKFLOW_STATUSES,
)
from app.schemas.workflow import (
    WorkflowExecutionCreate,
    WorkflowExecutionResponse,
    WorkflowExecutionListResponse,
    WorkflowEventResponse,
)
from app.services.orchestration.workflow_engine import (
    WorkflowEngine,
    InvalidStateTransitionError,
)
from app.services.orchestration.policy_engine import PolicyViolationError

router = APIRouter(prefix="", tags=["Workflow Orchestration"])


async def _get_channel_for_user(
    db: AsyncSession, channel_id: Optional[UUID], user: User
) -> Channel:
    """Validate tenant isolation and retrieve Channel entity."""
    if channel_id:
        stmt = select(Channel).where(Channel.id == channel_id)
        res = await db.execute(stmt)
        channel = res.scalar_one_or_none()
        if not channel:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")
        if user.role != "SUPER_ADMIN" and channel.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unauthorized access to channel workflows",
            )
        return channel

    stmt = select(Channel).where(Channel.user_id == user.id)
    res = await db.execute(stmt)
    channel = res.scalars().first()
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No channel found for current user",
        )
    return channel


@router.get("", response_model=WorkflowExecutionListResponse)
async def list_workflows(
    channel_id: Optional[UUID] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List workflow executions filtered by channel and status."""
    channel = await _get_channel_for_user(db, channel_id, current_user)

    query = (
        select(WorkflowExecution)
        .where(WorkflowExecution.channel_id == channel.id)
        .options(selectinload(WorkflowExecution.stages))
        .order_by(desc(WorkflowExecution.created_at))
    )

    if status_filter:
        if status_filter not in VALID_WORKFLOW_STATUSES:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status_filter}")
        query = query.where(WorkflowExecution.status == status_filter)

    # Count total
    count_query = select(func.count(WorkflowExecution.id)).where(WorkflowExecution.channel_id == channel.id)
    if status_filter:
        count_query = count_query.where(WorkflowExecution.status == status_filter)
    total = (await db.execute(count_query)).scalar() or 0

    results = (await db.execute(query.offset(offset).limit(limit))).scalars().all()
    return WorkflowExecutionListResponse(
        executions=[WorkflowExecutionResponse.model_validate(e) for e in results],
        total=total,
    )


@router.post("", response_model=WorkflowExecutionResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    payload: WorkflowExecutionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Instantiate a new workflow execution."""
    channel = await _get_channel_for_user(db, payload.channel_id, current_user)

    engine = WorkflowEngine(db)
    try:
        execution = await engine.create_execution(
            channel_id=channel.id,
            template_key=payload.template_key,
            project_id=payload.project_id,
            definition_id=payload.definition_id,
            context_data=payload.context_data,
        )

        if payload.auto_start:
            await engine.start_execution(execution.id)

        await db.commit()

        # Reload with stages
        stmt = (
            select(WorkflowExecution)
            .where(WorkflowExecution.id == execution.id)
            .options(selectinload(WorkflowExecution.stages))
        )
        loaded = (await db.execute(stmt)).scalars().first()
        return WorkflowExecutionResponse.model_validate(loaded)
    except (ValueError, PolicyViolationError) as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{workflow_id}", response_model=WorkflowExecutionResponse)
async def get_workflow(
    workflow_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve complete execution state, stages and current progress."""
    stmt = (
        select(WorkflowExecution)
        .where(WorkflowExecution.id == workflow_id)
        .options(selectinload(WorkflowExecution.stages))
    )
    execution = (await db.execute(stmt)).scalars().first()
    if not execution:
        raise HTTPException(status_code=404, detail="Workflow execution not found")

    await _get_channel_for_user(db, execution.channel_id, current_user)
    return WorkflowExecutionResponse.model_validate(execution)


@router.post("/{workflow_id}/start", response_model=WorkflowExecutionResponse)
async def start_workflow(
    workflow_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Start an eligible workflow execution."""
    stmt = select(WorkflowExecution).where(WorkflowExecution.id == workflow_id)
    execution = (await db.execute(stmt)).scalars().first()
    if not execution:
        raise HTTPException(status_code=404, detail="Workflow execution not found")

    await _get_channel_for_user(db, execution.channel_id, current_user)

    engine = WorkflowEngine(db)
    try:
        updated = await engine.start_execution(workflow_id)
        await db.commit()

        # Reload with stages
        stmt_reload = (
            select(WorkflowExecution)
            .where(WorkflowExecution.id == workflow_id)
            .options(selectinload(WorkflowExecution.stages))
        )
        loaded = (await db.execute(stmt_reload)).scalars().first()
        return WorkflowExecutionResponse.model_validate(loaded)
    except (InvalidStateTransitionError, PolicyViolationError, ValueError) as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{workflow_id}/pause", response_model=WorkflowExecutionResponse)
async def pause_workflow(
    workflow_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Pause an active workflow execution."""
    stmt = select(WorkflowExecution).where(WorkflowExecution.id == workflow_id)
    execution = (await db.execute(stmt)).scalars().first()
    if not execution:
        raise HTTPException(status_code=404, detail="Workflow execution not found")

    await _get_channel_for_user(db, execution.channel_id, current_user)

    engine = WorkflowEngine(db)
    try:
        updated = await engine.pause_execution(workflow_id)
        await db.commit()
        stmt_reload = (
            select(WorkflowExecution)
            .where(WorkflowExecution.id == workflow_id)
            .options(selectinload(WorkflowExecution.stages))
        )
        loaded = (await db.execute(stmt_reload)).scalars().first()
        return WorkflowExecutionResponse.model_validate(loaded)
    except (InvalidStateTransitionError, ValueError) as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{workflow_id}/resume", response_model=WorkflowExecutionResponse)
async def resume_workflow(
    workflow_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Resume a paused workflow execution."""
    stmt = select(WorkflowExecution).where(WorkflowExecution.id == workflow_id)
    execution = (await db.execute(stmt)).scalars().first()
    if not execution:
        raise HTTPException(status_code=404, detail="Workflow execution not found")

    await _get_channel_for_user(db, execution.channel_id, current_user)

    engine = WorkflowEngine(db)
    try:
        updated = await engine.resume_execution(workflow_id)
        await db.commit()
        stmt_reload = (
            select(WorkflowExecution)
            .where(WorkflowExecution.id == workflow_id)
            .options(selectinload(WorkflowExecution.stages))
        )
        loaded = (await db.execute(stmt_reload)).scalars().first()
        return WorkflowExecutionResponse.model_validate(loaded)
    except (InvalidStateTransitionError, ValueError) as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{workflow_id}/cancel", response_model=WorkflowExecutionResponse)
async def cancel_workflow(
    workflow_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a workflow execution."""
    stmt = select(WorkflowExecution).where(WorkflowExecution.id == workflow_id)
    execution = (await db.execute(stmt)).scalars().first()
    if not execution:
        raise HTTPException(status_code=404, detail="Workflow execution not found")

    await _get_channel_for_user(db, execution.channel_id, current_user)

    engine = WorkflowEngine(db)
    try:
        updated = await engine.cancel_execution(workflow_id)
        await db.commit()
        stmt_reload = (
            select(WorkflowExecution)
            .where(WorkflowExecution.id == workflow_id)
            .options(selectinload(WorkflowExecution.stages))
        )
        loaded = (await db.execute(stmt_reload)).scalars().first()
        return WorkflowExecutionResponse.model_validate(loaded)
    except (InvalidStateTransitionError, ValueError) as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{workflow_id}/approve", response_model=WorkflowExecutionResponse)
async def approve_checkpoint(
    workflow_id: UUID,
    checkpoint: str = Query(..., description="Name of checkpoint to approve"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Approve a paused checkpoint and advance execution."""
    stmt = select(WorkflowExecution).where(WorkflowExecution.id == workflow_id)
    execution = (await db.execute(stmt)).scalars().first()
    if not execution:
        raise HTTPException(status_code=404, detail="Workflow execution not found")

    await _get_channel_for_user(db, execution.channel_id, current_user)

    engine = WorkflowEngine(db)
    try:
        updated = await engine.approve_checkpoint(workflow_id, checkpoint)
        await db.commit()
        stmt_reload = (
            select(WorkflowExecution)
            .where(WorkflowExecution.id == workflow_id)
            .options(selectinload(WorkflowExecution.stages))
        )
        loaded = (await db.execute(stmt_reload)).scalars().first()
        return WorkflowExecutionResponse.model_validate(loaded)
    except (InvalidStateTransitionError, ValueError) as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{workflow_id}/events", response_model=List[WorkflowEventResponse])
async def get_workflow_events(
    workflow_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve append-only audit trail for a workflow."""
    stmt = select(WorkflowExecution).where(WorkflowExecution.id == workflow_id)
    execution = (await db.execute(stmt)).scalars().first()
    if not execution:
        raise HTTPException(status_code=404, detail="Workflow execution not found")

    await _get_channel_for_user(db, execution.channel_id, current_user)

    events_stmt = (
        select(WorkflowEvent)
        .where(WorkflowEvent.execution_id == workflow_id)
        .order_by(WorkflowEvent.created_at.asc())
    )
    events = (await db.execute(events_stmt)).scalars().all()
    return [WorkflowEventResponse.model_validate(ev) for ev in events]
