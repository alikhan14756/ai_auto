"""FastAPI router for Thumbnail Studio, procedural rendering, and quality validation."""

from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.core.logging import logger
from app.models.user import User
from app.schemas.job import JobRead
from app.schemas.thumbnail_seo import (
    ThumbnailConceptGenerateRequest,
    ThumbnailResponse,
    ThumbnailUpdateRequest,
)
from app.services.job_queue import JobQueueService
from app.services.thumbnail.validator import ThumbnailValidator
from app.services.thumbnail_service import ThumbnailService

router = APIRouter(prefix="/thumbnails", tags=["Thumbnail Studio & Composition"])


@router.post("/generate", response_model=List[ThumbnailResponse], status_code=status.HTTP_201_CREATED)
async def generate_thumbnail_concepts(
    req: ThumbnailConceptGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Generate 3 contrasting thumbnail variants (A, B, C) and procedurally render them."""
    target_project_id = req.project_id
    if not target_project_id:
        from app.models.project import VideoProject
        from app.models.channel import Channel
        from sqlalchemy import select
        stmt = (
            select(VideoProject)
            .join(Channel, VideoProject.channel_id == Channel.id)
            .where(Channel.user_id == current_user.id)
            .order_by(VideoProject.created_at.desc())
        )
        res = await db.execute(stmt)
        proj = res.scalars().first()
        if not proj:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No project found. Please provide a valid project_id.",
            )
        target_project_id = proj.id

    try:
        thumbnails = await ThumbnailService.generate_concepts_and_render_variants(
            db=db,
            project_id=target_project_id,
            user=current_user,
        )
        return thumbnails
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.exception(f"Failed to generate thumbnails: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/queue/generate", response_model=JobRead, status_code=status.HTTP_202_ACCEPTED)
async def queue_thumbnail_concept_generation(
    req: ThumbnailConceptGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Enqueue background job for thumbnail generation."""
    try:
        project = await ThumbnailService.verify_project_ownership(db, req.project_id, current_user)
        queue_service = JobQueueService(db)
        job, _ = await queue_service.enqueue_job(
            channel_id=project.channel_id,
            job_type="THUMBNAIL_CONCEPT_GENERATION",
            payload={"project_id": str(req.project_id), "user_id": str(current_user.id)},
        )
        return job
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/project/{project_id}", response_model=List[ThumbnailResponse])
async def list_project_thumbnails(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """List all thumbnail variants for a given video project."""
    try:
        return await ThumbnailService.get_project_thumbnails(db, project_id, current_user)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/{thumbnail_id}", response_model=ThumbnailResponse)
async def get_thumbnail(
    thumbnail_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Get single thumbnail details and quality report."""
    try:
        return await ThumbnailService.verify_thumbnail_ownership(db, thumbnail_id, current_user)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.patch("/{thumbnail_id}", response_model=ThumbnailResponse)
async def update_thumbnail_composition(
    thumbnail_id: UUID,
    req: ThumbnailUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Update thumbnail typography, style preset, or layers and re-render."""
    try:
        layers = req.composition_data.get("layers") if req.composition_data else None
        thumb = await ThumbnailService.update_thumbnail_composition(
            db=db,
            thumbnail_id=thumbnail_id,
            user=current_user,
            headline_text=req.headline_text,
            subtitle_text=req.badge_text,
            style_preset=req.style_preset,
            accent_color_hex=req.accent_color,
            layers=layers,
        )
        if req.is_selected:
            thumb = await ThumbnailService.select_thumbnail(db, thumbnail_id, current_user)
        return thumb
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.exception(f"Failed to update thumbnail composition: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{thumbnail_id}/select", response_model=ThumbnailResponse)
@router.patch("/{thumbnail_id}/approve", response_model=ThumbnailResponse)
@router.post("/{thumbnail_id}/approve", response_model=ThumbnailResponse)
async def select_thumbnail_variant(
    thumbnail_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Mark a thumbnail variant as the approved selection for publication."""
    try:
        try:
            target_uuid = UUID(str(thumbnail_id))
        except ValueError:
            from app.models.thumbnail import Thumbnail
            from app.models.project import VideoProject
            from app.models.channel import Channel
            from sqlalchemy import select
            stmt = (
                select(Thumbnail)
                .join(VideoProject, Thumbnail.project_id == VideoProject.id)
                .join(Channel, VideoProject.channel_id == Channel.id)
                .where(Thumbnail.variant_code == thumbnail_id.upper())
            )
            if current_user.role != "SUPER_ADMIN":
                stmt = stmt.where(Channel.user_id == current_user.id)
            stmt = stmt.order_by(Thumbnail.created_at.desc())
            res = await db.execute(stmt)
            thumb = res.scalars().first()
            if not thumb:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Thumbnail variant '{thumbnail_id}' not found.",
                )
            target_uuid = thumb.id

        return await ThumbnailService.select_thumbnail(db, target_uuid, current_user)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/{thumbnail_id}/file")
async def stream_thumbnail_file(
    thumbnail_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Authenticated endpoint streaming the rendered thumbnail PNG/JPEG."""
    try:
        thumb = await ThumbnailService.verify_thumbnail_ownership(db, thumbnail_id, current_user)
        file_path = Path(thumb.storage_path)
        if not file_path.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thumbnail image file not found on disk.")
        media_type = "image/png" if file_path.suffix.lower() == ".png" else "image/jpeg"
        return FileResponse(
            path=str(file_path),
            media_type=media_type,
            filename=file_path.name,
        )
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post("/validate")
async def validate_thumbnail_file_path(
    payload: Dict[str, str],
    current_user: User = Depends(get_current_user),
) -> Any:
    """Direct validation of a rendered thumbnail file path with directory traversal guard."""
    file_path = payload.get("file_path")
    if not file_path:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing 'file_path'")

    # Path traversal boundary check: must reside inside configured storage or thumbnail directory
    target = Path(file_path).resolve()
    base_dir = Path(settings.THUMBNAIL_OUTPUT_DIR).resolve()
    storage_dir = Path(settings.LOCAL_STORAGE_DIR).resolve()
    if not (target.is_relative_to(base_dir) or target.is_relative_to(storage_dir)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: file path is outside allowed thumbnail storage directory.",
        )

    report = ThumbnailValidator.validate_thumbnail(str(target))
    return report
