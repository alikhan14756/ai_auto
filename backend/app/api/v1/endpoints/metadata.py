"""FastAPI router for YouTube SEO Metadata Studio, chaptering, scoring, and approval."""

from typing import Any, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.logging import logger
from app.models.user import User
from app.schemas.job import JobRead
from app.schemas.thumbnail_seo import (
    MetadataDraftResponse,
    MetadataGenerateRequest,
    MetadataUpdateRequest,
)
from app.services.job_queue import JobQueueService
from app.services.metadata_service import MetadataService

router = APIRouter(prefix="/metadata", tags=["YouTube SEO Metadata Studio"])


@router.post("/generate", response_model=MetadataDraftResponse, status_code=status.HTTP_201_CREATED)
async def generate_seo_metadata(
    req: MetadataGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Generate structured YouTube SEO metadata draft with title candidates, chapters, and score."""
    try:
        draft = await MetadataService.generate_project_metadata(
            db=db,
            project_id=req.project_id,
            user=current_user,
        )
        return draft
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.exception(f"Failed to generate SEO metadata: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/queue/generate", response_model=JobRead, status_code=status.HTTP_202_ACCEPTED)
async def queue_seo_metadata_generation(
    req: MetadataGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Enqueue background job for SEO metadata generation."""
    try:
        project = await MetadataService.verify_project_ownership(db, req.project_id, current_user)
        queue_service = JobQueueService(db)
        job, _ = await queue_service.enqueue_job(
            channel_id=project.channel_id,
            job_type="SEO_METADATA_GENERATION",
            payload={"project_id": str(req.project_id), "user_id": str(current_user.id)},
        )
        return job
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/project/{project_id}", response_model=List[MetadataDraftResponse])
async def list_project_metadata_drafts(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """List all SEO metadata drafts for a given video project."""
    try:
        return await MetadataService.get_project_metadata(db, project_id, current_user)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/{metadata_id}", response_model=MetadataDraftResponse)
async def get_metadata_draft(
    metadata_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Get single SEO metadata draft with score and pairing analysis."""
    try:
        return await MetadataService.verify_metadata_ownership(db, metadata_id, current_user)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.patch("/{metadata_id}", response_model=MetadataDraftResponse)
async def update_metadata_draft(
    metadata_id: UUID,
    req: MetadataUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Update title, description, tags, hashtags, chapters, or pinned comment and re-score."""
    try:
        draft = await MetadataService.update_metadata_draft(
            db=db,
            metadata_id=metadata_id,
            user=current_user,
            title=req.title,
            description=req.description,
            tags=req.tags,
            hashtags=req.hashtags,
            chapters=req.chapters,
            pinned_comment=req.pinned_comment,
        )
        return draft
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.exception(f"Failed to update metadata draft: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{metadata_id}/approve", response_model=MetadataDraftResponse)
async def approve_metadata_draft(
    metadata_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Approve an SEO metadata draft for publication."""
    try:
        return await MetadataService.approve_metadata(db, metadata_id, current_user)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
