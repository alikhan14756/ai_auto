"""FastAPI router for Publication Package preparation and verification."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.logging import logger
from app.models.user import User
from app.schemas.job import JobRead
from app.schemas.thumbnail_seo import (
    PublicationPackageCreateRequest,
    PublicationPackageResponse,
)
from app.services.job_queue import JobQueueService
from app.services.publication import PublicationService

router = APIRouter(prefix="/publication-packages", tags=["Publication Packages"])


@router.post("", response_model=PublicationPackageResponse, status_code=status.HTTP_201_CREATED)
async def create_publication_package(
    req: PublicationPackageCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Assemble verified video render, approved thumbnail, and SEO metadata into a publication package."""
    try:
        package = await PublicationService.assemble_package(
            db=db,
            project_id=req.project_id,
            user=current_user,
        )
        return package
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.exception(f"Failed to assemble publication package: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/queue/prepare", response_model=JobRead, status_code=status.HTTP_202_ACCEPTED)
async def queue_publication_package_preparation(
    req: PublicationPackageCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Enqueue background job for assembling publication package."""
    try:
        project = await PublicationService.verify_project_ownership(db, req.project_id, current_user)
        queue_service = JobQueueService(db)
        job, _ = await queue_service.enqueue_job(
            channel_id=project.channel_id,
            job_type="PUBLICATION_PACKAGE_PREPARATION",
            payload={"project_id": str(req.project_id), "user_id": str(current_user.id)},
        )
        return job
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/{package_id}", response_model=PublicationPackageResponse)
async def get_publication_package(
    package_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Get publication package details and manifest."""
    try:
        return await PublicationService.verify_package_ownership(db, package_id, current_user)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post("/{package_id}/approve", response_model=PublicationPackageResponse)
async def approve_publication_package(
    package_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Approve publication package for QA Gate audit and release."""
    try:
        return await PublicationService.approve_package(db, package_id, current_user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
