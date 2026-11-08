"""FastAPI Endpoints for Visual Storyboard Planning, Media Discovery & Asset Library."""

import io
from typing import List, Optional
from uuid import UUID
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, status
from fastapi.responses import Response, FileResponse
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.project import VideoProject
from app.models.channel import Channel
from app.models.storyboard import Storyboard
from app.models.scene import Scene
from app.models.media import MediaAsset
from app.services.visual_planning import VisualPlanningService
from app.services.visual_asset import VisualAssetService, AssetSecurityError
from app.services.storage import StorageSecurityError
from app.providers.visual.base import (
    VisualProviderError,
    BudgetExceededError,
    RateLimitError,
    ProviderConfigurationError,
    StockSearchResult,
)
from app.schemas.visual import (
    StoryboardResponse,
    StoryboardSceneResponse,
    StoryboardGenerateRequest,
    SceneUpdateRequest,
    SceneReorderRequest,
    AssetAssignRequest,
    StockSearchRequest,
    StockAssetImportRequest,
    ImageGenerateRequest,
    MediaAssetResponse,
    MediaAssetListResponse,
    LicenseUpdateRequest,
)

router = APIRouter(prefix="/visual", tags=["Visual Studio & Media Library"])


async def _verify_project_ownership(db: AsyncSession, project_id: UUID, user: User) -> VideoProject:
    """Ensure current user owns the channel associated with the project."""
    stmt = (
        select(VideoProject)
        .join(Channel, VideoProject.channel_id == Channel.id)
        .where(VideoProject.id == project_id)
    )
    if user.role != "SUPER_ADMIN":
        stmt = stmt.where(Channel.user_id == user.id)

    res = await db.execute(stmt)
    proj = res.scalar_one_or_none()
    if not proj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video project not found or access denied.")
    return proj


async def _verify_channel_ownership(db: AsyncSession, channel_id: UUID, user: User) -> Channel:
    """Ensure current user owns the channel."""
    stmt = select(Channel).where(Channel.id == channel_id)
    if user.role != "SUPER_ADMIN":
        stmt = stmt.where(Channel.user_id == user.id)
    res = await db.execute(stmt)
    ch = res.scalar_one_or_none()
    if not ch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found or access denied.")
    return ch


# ==============================================================================
# STORYBOARD ENDPOINTS
# ==============================================================================

@router.post("/storyboards/generate", response_model=StoryboardResponse)
async def generate_storyboard(
    req: StoryboardGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate or synchronize a visual storyboard for an approved script."""
    await _verify_project_ownership(db, req.project_id, current_user)
    planner = VisualPlanningService()
    try:
        storyboard = await planner.generate_storyboard(db, req.project_id)
        return storyboard
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        logger.error(f"Storyboard generation error: {exc}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to generate storyboard: {exc}")


@router.get("/storyboards/project/{project_id}", response_model=StoryboardResponse)
async def get_project_storyboard(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve the current storyboard and scenes for a project."""
    await _verify_project_ownership(db, project_id, current_user)

    stmt = (
        select(Storyboard)
        .where(Storyboard.project_id == project_id)
        .options(
            selectinload(Storyboard.scenes).selectinload(Scene.selected_asset),
            selectinload(Storyboard.script),
            selectinload(Storyboard.narration_track),
        )
        .order_by(Storyboard.version.desc())
    )
    res = await db.execute(stmt)
    sb = res.scalars().first()
    if not sb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Storyboard not found for this project.")
    return sb


@router.put("/storyboards/{storyboard_id}/scenes/{scene_id}", response_model=StoryboardSceneResponse)
async def update_storyboard_scene(
    storyboard_id: UUID,
    scene_id: UUID,
    req: SceneUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update scene visual directives, purpose, keywords, transition, or review status."""
    sb_res = await db.execute(select(Storyboard).where(Storyboard.id == storyboard_id))
    sb = sb_res.scalar_one_or_none()
    if not sb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Storyboard not found.")
    await _verify_project_ownership(db, sb.project_id, current_user)

    # Validate scene belongs to storyboard
    s_stmt = select(Scene).where(Scene.id == scene_id, Scene.storyboard_id == storyboard_id, Scene.project_id == sb.project_id)
    s_res = await db.execute(s_stmt)
    if not s_res.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scene not found in this storyboard.")

    planner = VisualPlanningService()
    try:
        updated = await planner.update_scene(db, scene_id, req.model_dump(exclude_unset=True))
        return updated
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/storyboards/{storyboard_id}/scenes/{scene_id}/assign-asset", response_model=StoryboardSceneResponse)
async def assign_asset_to_scene(
    storyboard_id: UUID,
    scene_id: UUID,
    req: AssetAssignRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Assign an existing library media asset to a storyboard scene with cross-tenant authorization."""
    sb_res = await db.execute(select(Storyboard).where(Storyboard.id == storyboard_id))
    sb = sb_res.scalar_one_or_none()
    if not sb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Storyboard not found.")
    project = await _verify_project_ownership(db, sb.project_id, current_user)

    # Verify scene belongs to storyboard
    s_stmt = select(Scene).where(Scene.id == scene_id, Scene.storyboard_id == storyboard_id, Scene.project_id == sb.project_id)
    s_res = await db.execute(s_stmt)
    if not s_res.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scene not found in this storyboard.")

    # Verify asset belongs to channel
    a_stmt = select(MediaAsset).where(MediaAsset.id == req.asset_id, MediaAsset.channel_id == project.channel_id)
    a_res = await db.execute(a_stmt)
    if not a_res.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media asset not found in channel workspace.")

    service = VisualAssetService()
    try:
        updated_scene = await service.assign_asset_to_scene(db, scene_id=scene_id, asset_id=req.asset_id)
        return updated_scene
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/storyboards/{storyboard_id}/scenes/{scene_id}/generate-image", response_model=MediaAssetResponse)
async def generate_scene_image(
    storyboard_id: UUID,
    scene_id: UUID,
    req: ImageGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Synthesize an original AI image for a scene and assign it immediately."""
    await _verify_project_ownership(db, req.project_id, current_user)

    # Verify scene belongs to project
    s_stmt = select(Scene).where(Scene.id == scene_id, Scene.project_id == req.project_id)
    s_res = await db.execute(s_stmt)
    if not s_res.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scene not found in project.")

    service = VisualAssetService()
    try:
        asset = await service.generate_scene_image(
            db=db,
            channel_id=req.channel_id,
            project_id=req.project_id,
            scene_id=scene_id,
            prompt=req.prompt,
            aspect_ratio=req.aspect_ratio,
            style=req.style,
            provider_name=req.provider,
        )
        return asset
    except BudgetExceededError as exc:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=str(exc))
    except RateLimitError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc))
    except (ProviderConfigurationError, VisualProviderError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/storyboards/{storyboard_id}/scenes/reorder", response_model=List[StoryboardSceneResponse])
async def reorder_storyboard_scenes(
    storyboard_id: UUID,
    req: SceneReorderRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reorder scenes in a storyboard."""
    sb_res = await db.execute(select(Storyboard).where(Storyboard.id == storyboard_id))
    sb = sb_res.scalar_one_or_none()
    if not sb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Storyboard not found.")
    await _verify_project_ownership(db, sb.project_id, current_user)

    planner = VisualPlanningService()
    reordered = await planner.reorder_scenes(db, storyboard_id, req.ordered_scene_ids)
    return reordered


@router.post("/storyboards/{storyboard_id}/approve", response_model=StoryboardResponse)
async def approve_storyboard(
    storyboard_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Approve full storyboard and advance project workflow state with licensing verification."""
    sb_res = await db.execute(select(Storyboard).where(Storyboard.id == storyboard_id))
    sb = sb_res.scalar_one_or_none()
    if not sb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Storyboard not found.")
    await _verify_project_ownership(db, sb.project_id, current_user)

    planner = VisualPlanningService()
    try:
        approved = await planner.approve_storyboard(db, storyboard_id)
        return approved
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


# ==============================================================================
# ASSET DISCOVERY & SEARCH
# ==============================================================================

@router.post("/assets/search", response_model=StockSearchResult)
async def search_stock_media(
    req: StockSearchRequest,
    current_user: User = Depends(get_current_user),
):
    """Query external or mock media providers for stock assets."""
    service = VisualAssetService()
    try:
        results = await service.search_stock(
            query=req.query,
            aspect_ratio=req.aspect_ratio,
            provider_name=req.provider,
            page=req.page,
            per_page=req.per_page,
        )
        return results
    except RateLimitError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc))
    except (ProviderConfigurationError, VisualProviderError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/assets/import-external", response_model=MediaAssetResponse)
async def import_external_asset(
    req: StockAssetImportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Import a discovered stock asset into the project's media library."""
    await _verify_project_ownership(db, req.project_id, current_user)
    if req.scene_id:
        s_res = await db.execute(select(Scene).where(Scene.id == req.scene_id, Scene.project_id == req.project_id))
        if not s_res.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scene not found in project.")

    service = VisualAssetService()
    asset = await service.import_stock_asset(
        db=db,
        channel_id=req.channel_id,
        project_id=req.project_id,
        stock_item=req.stock_item,
        scene_id=req.scene_id,
    )
    return asset


# ==============================================================================
# ASSET LIBRARY & MANAGEMENT
# ==============================================================================

@router.get("/assets", response_model=MediaAssetListResponse)
async def list_media_assets(
    channel_id: Optional[UUID] = Query(None),
    project_id: Optional[UUID] = Query(None),
    category: Optional[str] = Query(None),
    license_status: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List assets with multi-tenant workspace isolation."""
    # Multi-tenant isolation: verify and limit to user channels
    if current_user.role != "SUPER_ADMIN":
        user_ch_res = await db.execute(select(Channel.id).where(Channel.user_id == current_user.id))
        owned_channel_ids = [r[0] for r in user_ch_res.all()]
        if not owned_channel_ids:
            return MediaAssetListResponse(total=0, assets=[])

        if channel_id:
            if channel_id not in owned_channel_ids:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found or access denied.")
        if project_id:
            await _verify_project_ownership(db, project_id, current_user)

    service = VisualAssetService()
    assets = await service.list_assets(
        db=db,
        channel_id=channel_id,
        project_id=project_id,
        category=category,
        license_status=license_status,
        search_query=q,
        limit=limit,
        offset=offset,
    )
    return MediaAssetListResponse(total=len(assets), assets=assets)


@router.post("/assets/upload", response_model=MediaAssetResponse)
async def upload_media_asset(
    channel_id: UUID = Form(...),
    project_id: UUID = Form(...),
    title: Optional[str] = Form(None),
    scene_id: Optional[UUID] = Form(None),
    license_type: str = Form("CUSTOM"),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Securely upload custom media asset with magic byte inspection."""
    await _verify_project_ownership(db, project_id, current_user)
    if scene_id:
        s_res = await db.execute(select(Scene).where(Scene.id == scene_id, Scene.project_id == project_id))
        if not s_res.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scene not found in project.")

    content = await file.read()
    service = VisualAssetService()
    try:
        asset = await service.upload_asset(
            db=db,
            channel_id=channel_id,
            project_id=project_id,
            filename=file.filename or "upload.png",
            data=content,
            title=title,
            scene_id=scene_id,
            license_type=license_type,
        )
        return asset
    except AssetSecurityError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/assets/{asset_id}", response_model=MediaAssetResponse)
async def get_media_asset(
    asset_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get metadata for a specific media asset with ownership check."""
    stmt = (
        select(MediaAsset)
        .join(Channel, MediaAsset.channel_id == Channel.id)
        .where(MediaAsset.id == asset_id, MediaAsset.is_archived == False)
    )
    if current_user.role != "SUPER_ADMIN":
        stmt = stmt.where(Channel.user_id == current_user.id)

    res = await db.execute(stmt)
    asset = res.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media asset not found or access denied.")
    return asset


@router.patch("/assets/{asset_id}/license", response_model=MediaAssetResponse)
async def update_asset_license_status(
    asset_id: UUID,
    req: LicenseUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update licensing compliance and attribution information with ownership check."""
    stmt = (
        select(MediaAsset)
        .join(Channel, MediaAsset.channel_id == Channel.id)
        .where(MediaAsset.id == asset_id)
    )
    if current_user.role != "SUPER_ADMIN":
        stmt = stmt.where(Channel.user_id == current_user.id)

    res = await db.execute(stmt)
    asset = res.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media asset not found or access denied.")

    service = VisualAssetService()
    try:
        updated = await service.update_asset_license(
            db=db,
            asset_id=asset_id,
            license_status=req.license_status,
            attribution_text=req.attribution_text,
            license_type=req.license_type,
        )
        return updated
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.delete("/assets/{asset_id}")
async def archive_media_asset(
    asset_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Archive a media asset from active views with ownership check."""
    stmt = (
        select(MediaAsset)
        .join(Channel, MediaAsset.channel_id == Channel.id)
        .where(MediaAsset.id == asset_id)
    )
    if current_user.role != "SUPER_ADMIN":
        stmt = stmt.where(Channel.user_id == current_user.id)

    res = await db.execute(stmt)
    asset = res.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media asset not found or access denied.")

    asset.is_archived = True
    await db.commit()
    return {"message": "Asset archived successfully", "asset_id": str(asset_id)}


@router.get("/assets/{asset_id}/file")
async def get_media_asset_file(
    asset_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Serve secure binary asset content with verified MIME type and authentication."""
    stmt = (
        select(MediaAsset)
        .join(Channel, MediaAsset.channel_id == Channel.id)
        .where(MediaAsset.id == asset_id)
    )
    if current_user.role != "SUPER_ADMIN":
        stmt = stmt.where(Channel.user_id == current_user.id)

    res = await db.execute(stmt)
    asset = res.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media asset not found or access denied.")

    service = VisualAssetService()
    try:
        abs_path = service._storage.get_absolute_path(asset.storage_path)
        if not abs_path.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media binary file missing from storage.")
        return FileResponse(path=str(abs_path), media_type=asset.mime_type, filename=abs_path.name)
    except StorageSecurityError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Security violation in asset path.")
    except Exception as exc:
        logger.error(f"Error serving asset file: {exc}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not read media file.")
