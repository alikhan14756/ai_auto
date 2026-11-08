"""Video Project production endpoints with multi-tenant isolation."""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.models.channel import Channel
from app.models.project import VideoProject
from app.schemas.project import (
    VideoProjectCreate,
    VideoProjectUpdate,
    VideoProjectRead,
)
from app.api.deps import get_current_user
from app.core.security import ROLE_SUPER_ADMIN

router = APIRouter()


async def verify_project_tenant_access(
    project_id: uuid.UUID,
    current_user: User,
    db: AsyncSession,
) -> VideoProject:
    """Helper to verify that a project exists and belongs to a channel owned by current_user."""
    stmt = (
        select(VideoProject)
        .join(Channel, VideoProject.channel_id == Channel.id)
        .where(VideoProject.id == project_id)
    )
    result = await db.execute(stmt)
    project = result.scalars().first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video project not found",
        )

    # Check ownership of channel
    channel_stmt = select(Channel).where(Channel.id == project.channel_id)
    channel_res = await db.execute(channel_stmt)
    channel = channel_res.scalars().first()

    if not channel or (channel.user_id != current_user.id and current_user.role != ROLE_SUPER_ADMIN):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video project not found",
        )

    return project


@router.get("", response_model=List[VideoProjectRead], summary="List projects for channel")
async def list_projects(
    channel_id: uuid.UUID = Query(..., description="Target Channel ID to list projects for"),
    state: Optional[str] = Query(None, description="Optional filter by lifecycle state"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[VideoProject]:
    """Retrieve video projects for a specified channel with tenant isolation."""
    # Verify user owns channel
    ch_stmt = select(Channel).where(Channel.id == channel_id)
    ch_res = await db.execute(ch_stmt)
    channel = ch_res.scalars().first()

    if not channel or (channel.user_id != current_user.id and current_user.role != ROLE_SUPER_ADMIN):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel workspace not found",
        )

    query = select(VideoProject).where(VideoProject.channel_id == channel_id)
    if state:
        query = query.where(VideoProject.state == state)
    query = query.order_by(VideoProject.created_at.desc())

    result = await db.execute(query)
    return list(result.scalars().all())


@router.post("", response_model=VideoProjectRead, status_code=status.HTTP_201_CREATED, summary="Create video project")
async def create_project(
    project_in: VideoProjectCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VideoProject:
    """Create a new video project in the specified channel."""
    # Verify user owns channel
    ch_stmt = select(Channel).where(Channel.id == project_in.channel_id)
    ch_res = await db.execute(ch_stmt)
    channel = ch_res.scalars().first()

    if not channel or (channel.user_id != current_user.id and current_user.role != ROLE_SUPER_ADMIN):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel workspace not found",
        )

    project = VideoProject(
        channel_id=project_in.channel_id,
        topic_id=project_in.topic_id,
        title=project_in.title,
        format=project_in.format,
        state="IDEA",
        target_duration_seconds=project_in.target_duration_seconds,
        revision_number=1,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


@router.get("/{project_id}", response_model=VideoProjectRead, summary="Get project details")
async def get_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VideoProject:
    """Retrieve details of a single video project with tenant isolation verified."""
    return await verify_project_tenant_access(project_id, current_user, db)


@router.patch("/{project_id}", response_model=VideoProjectRead, summary="Update video project")
async def update_project(
    project_id: uuid.UUID,
    update_data: VideoProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VideoProject:
    """Update metadata and lifecycle state of a video project."""
    project = await verify_project_tenant_access(project_id, current_user, db)

    if update_data.title is not None:
        project.title = update_data.title
    if update_data.format is not None:
        project.format = update_data.format
    if update_data.state is not None:
        project.state = update_data.state
    if update_data.target_duration_seconds is not None:
        project.target_duration_seconds = update_data.target_duration_seconds
    if update_data.actual_duration_seconds is not None:
        project.actual_duration_seconds = update_data.actual_duration_seconds

    await db.commit()
    await db.refresh(project)
    return project
