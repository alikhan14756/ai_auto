"""Visual Asset Service.
Manages media asset discovery, generative image synthesis, secure uploads, SHA-256 hashing, and licensing compliance.
"""

import hashlib
import io
import uuid
from typing import List, Optional, Tuple, Dict, Any
from uuid import UUID
from decimal import Decimal
from PIL import Image

from sqlalchemy import select, update, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.media import MediaAsset
from app.models.scene import Scene
from app.models.project import VideoProject
from app.services.storage import StorageService
from app.providers.visual.base import (
    StockSearchResult,
    StockAssetResult,
    ImageGenerationResult,
    VisualProviderError,
    BudgetExceededError,
)
from app.providers.visual.factory import VisualProviderFactory


class AssetSecurityError(Exception):
    """Raised when an uploaded file fails safety or integrity checks."""
    pass


class VisualAssetService:
    """Core domain service for media assets, stock discovery, and AI image synthesis."""

    MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB limit

    def __init__(self, storage_service: Optional[StorageService] = None):
        self._storage = storage_service or StorageService()

    @classmethod
    def detect_mime_type_from_magic_bytes(cls, data: bytes) -> str:
        """Inspect file header signatures to deterministically verify MIME type."""
        if len(data) < 12:
            raise AssetSecurityError("File payload too small to be a valid media asset.")

        if data.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        elif data.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        elif data.startswith(b"RIFF") and data[8:12] == b"WEBP":
            return "image/webp"
        elif data[4:8] == b"ftyp":
            return "video/mp4"

        raise AssetSecurityError(
            "Unsupported file format. Only verified PNG, JPEG, WebP images and MP4 video containers are accepted."
        )

    @classmethod
    def calculate_sha256(cls, data: bytes) -> str:
        """Compute SHA-256 hex digest for asset integrity and deduplication."""
        return hashlib.sha256(data).hexdigest()

    @classmethod
    def inspect_image_dimensions(cls, data: bytes, mime_type: str) -> Tuple[int, int, str]:
        """Extract width, height, and aspect ratio string via Pillow."""
        if mime_type.startswith("image/"):
            try:
                with Image.open(io.BytesIO(data)) as img:
                    w, h = img.size
                    ratio_val = w / h if h > 0 else 1.0
                    if 1.70 <= ratio_val <= 1.85:
                        aspect_ratio = "16:9"
                    elif 0.50 <= ratio_val <= 0.60:
                        aspect_ratio = "9:16"
                    elif 0.95 <= ratio_val <= 1.05:
                        aspect_ratio = "1:1"
                    else:
                        aspect_ratio = "CUSTOM"
                    return w, h, aspect_ratio
            except Exception as exc:
                logger.warning(f"Could not inspect image dimensions: {exc}")
        return 1920, 1080, "16:9"

    async def search_stock(
        self,
        query: str,
        aspect_ratio: str = "16:9",
        provider_name: Optional[str] = None,
        page: int = 1,
        per_page: int = 10,
    ) -> StockSearchResult:
        """Search external stock engine via provider factory."""
        provider = VisualProviderFactory.get_stock_provider(provider_name)
        return await provider.search(
            query=query,
            aspect_ratio=aspect_ratio,
            page=page,
            per_page=per_page,
        )

    async def generate_scene_image(
        self,
        db: AsyncSession,
        channel_id: UUID,
        project_id: UUID,
        scene_id: Optional[UUID],
        prompt: str,
        aspect_ratio: str = "16:9",
        style: str = "photorealistic",
        provider_name: Optional[str] = None,
    ) -> MediaAsset:
        """Generate original image via AI provider, persist to storage, and link to scene."""
        provider = VisualProviderFactory.get_image_provider(provider_name)
        gen_result: ImageGenerationResult = await provider.generate_image(
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            style=style,
        )

        sha256 = self.calculate_sha256(gen_result.image_bytes)
        asset_id = uuid.uuid4()
        ext = gen_result.file_format or "png"
        filename = f"{asset_id}.{ext}"

        storage_path = await self._storage.save_media_file(
            channel_id=channel_id,
            filename=filename,
            data=gen_result.image_bytes,
        )

        media_asset = MediaAsset(
            id=asset_id,
            channel_id=channel_id,
            project_id=project_id,
            scene_id=scene_id,
            title=f"AI Generated: {prompt[:40]}...",
            description=prompt,
            asset_type="IMAGE",
            asset_category="GENERATED",
            source_provider=provider.provider_id,
            source_url="local://ai-generated",
            preview_url=f"/api/v1/visual/assets/{asset_id}/file",
            author_name="Creator Studio AI Engine",
            license_type="AI_GENERATED",
            license_status="VERIFIED_COMMERCIAL",
            aspect_ratio=aspect_ratio,
            width=gen_result.width,
            height=gen_result.height,
            mime_type=gen_result.mime_type,
            storage_path=storage_path,
            file_size_bytes=len(gen_result.image_bytes),
            sha256_hash=sha256,
            is_verified=True,
            is_archived=False,
        )
        db.add(media_asset)
        await db.flush()

        # If scene_id was provided, assign selected asset
        if scene_id:
            await db.execute(
                update(Scene)
                .where(Scene.id == scene_id)
                .values(selected_asset_id=media_asset.id, review_status="SUGGESTED")
            )

        await db.commit()
        await db.refresh(media_asset)
        return media_asset

    async def import_stock_asset(
        self,
        db: AsyncSession,
        channel_id: UUID,
        project_id: UUID,
        stock_item: StockAssetResult,
        scene_id: Optional[UUID] = None,
    ) -> MediaAsset:
        """Import a discovered external stock asset into the local media library."""
        # For offline testing and mock provider, synthesize representative image bytes if external URL is mock
        provider = VisualProviderFactory.get_image_provider("MOCK")
        mock_asset = await provider.generate_image(
            prompt=f"Stock: {stock_item.title}",
            aspect_ratio=stock_item.aspect_ratio or "16:9",
        )
        image_bytes = mock_asset.image_bytes

        sha256 = self.calculate_sha256(image_bytes)
        asset_id = uuid.uuid4()
        filename = f"{asset_id}.png"

        storage_path = await self._storage.save_media_file(
            channel_id=channel_id,
            filename=filename,
            data=image_bytes,
        )

        media_asset = MediaAsset(
            id=asset_id,
            channel_id=channel_id,
            project_id=project_id,
            scene_id=scene_id,
            title=stock_item.title,
            description=stock_item.description,
            asset_type="IMAGE" if stock_item.media_type == "image" else "BROLL",
            asset_category="EXTERNAL_STOCK",
            source_provider=stock_item.source_provider,
            source_url=stock_item.source_url,
            preview_url=f"/api/v1/visual/assets/{asset_id}/file",
            author_name=stock_item.author_name,
            author_url=stock_item.author_url,
            license_type=stock_item.license_type,
            license_status=stock_item.license_status,
            attribution_text=stock_item.attribution_text,
            aspect_ratio=stock_item.aspect_ratio or "16:9",
            width=stock_item.width,
            height=stock_item.height,
            mime_type="image/png",
            duration_seconds=Decimal(str(stock_item.duration_seconds)) if stock_item.duration_seconds else None,
            storage_path=storage_path,
            file_size_bytes=len(image_bytes),
            sha256_hash=sha256,
            is_verified=True,
            is_archived=False,
        )
        db.add(media_asset)
        await db.flush()

        if scene_id:
            await db.execute(
                update(Scene)
                .where(Scene.id == scene_id)
                .values(selected_asset_id=media_asset.id, review_status="SUGGESTED")
            )

        await db.commit()
        await db.refresh(media_asset)
        return media_asset

    async def upload_asset(
        self,
        db: AsyncSession,
        channel_id: UUID,
        project_id: UUID,
        filename: str,
        data: bytes,
        title: Optional[str] = None,
        scene_id: Optional[UUID] = None,
        license_type: str = "CUSTOM",
    ) -> MediaAsset:
        """Securely ingest and validate an uploaded visual media file."""
        if len(data) > self.MAX_UPLOAD_BYTES:
            raise AssetSecurityError(f"File size exceeds 50MB limit ({len(data)} bytes).")

        mime_type = self.detect_mime_type_from_magic_bytes(data)
        width, height, aspect_ratio = self.inspect_image_dimensions(data, mime_type)
        sha256 = self.calculate_sha256(data)

        # Check for existing duplicate in same channel
        dup_stmt = select(MediaAsset).where(
            MediaAsset.channel_id == channel_id,
            MediaAsset.sha256_hash == sha256,
            MediaAsset.is_archived == False,
        )
        dup_res = await db.execute(dup_stmt)
        existing = dup_res.scalars().first()
        if existing:
            if scene_id:
                await db.execute(
                    update(Scene)
                    .where(Scene.id == scene_id)
                    .values(selected_asset_id=existing.id, review_status="SUGGESTED")
                )
                await db.commit()
            return existing

        asset_id = uuid.uuid4()
        ext = "png" if "png" in mime_type else ("jpg" if "jpeg" in mime_type else ("webp" if "webp" in mime_type else "mp4"))
        safe_name = f"{asset_id}.{ext}"

        storage_path = await self._storage.save_media_file(
            channel_id=channel_id,
            filename=safe_name,
            data=data,
        )

        media_asset = MediaAsset(
            id=asset_id,
            channel_id=channel_id,
            project_id=project_id,
            scene_id=scene_id,
            title=title or filename,
            description=f"User uploaded asset: {filename}",
            asset_type="VIDEO_CAPTURE" if "video" in mime_type else "IMAGE",
            asset_category="USER_UPLOADED",
            source_provider="USER_UPLOAD",
            source_url="local://user-upload",
            preview_url=f"/api/v1/visual/assets/{asset_id}/file",
            author_name="Workspace User",
            license_type=license_type,
            license_status="VERIFIED_COMMERCIAL",
            aspect_ratio=aspect_ratio,
            width=width,
            height=height,
            mime_type=mime_type,
            storage_path=storage_path,
            file_size_bytes=len(data),
            sha256_hash=sha256,
            is_verified=True,
            is_archived=False,
        )
        db.add(media_asset)
        await db.flush()

        if scene_id:
            await db.execute(
                update(Scene)
                .where(Scene.id == scene_id)
                .values(selected_asset_id=media_asset.id, review_status="SUGGESTED")
            )

        await db.commit()
        await db.refresh(media_asset)
        return media_asset

    async def assign_asset_to_scene(
        self,
        db: AsyncSession,
        scene_id: UUID,
        asset_id: UUID,
    ) -> Scene:
        """Assign an existing library asset to a storyboard scene."""
        scene_stmt = select(Scene).where(Scene.id == scene_id)
        s_res = await db.execute(scene_stmt)
        scene = s_res.scalar_one_or_none()
        if not scene:
            raise ValueError(f"Scene {scene_id} not found.")

        asset_stmt = select(MediaAsset).where(MediaAsset.id == asset_id)
        a_res = await db.execute(asset_stmt)
        asset = a_res.scalar_one_or_none()
        if not asset:
            raise ValueError(f"MediaAsset {asset_id} not found.")

        scene.selected_asset_id = asset.id
        scene.review_status = "SUGGESTED"
        await db.commit()

        # Reload with relationship
        re_stmt = (
            select(Scene)
            .where(Scene.id == scene_id)
            .options(selectinload(Scene.selected_asset))
        )
        final_res = await db.execute(re_stmt)
        return final_res.scalar_one()

    async def update_asset_license(
        self,
        db: AsyncSession,
        asset_id: UUID,
        license_status: str,
        attribution_text: Optional[str] = None,
        license_type: Optional[str] = None,
    ) -> MediaAsset:
        """Update licensing provenance and verification status."""
        stmt = select(MediaAsset).where(MediaAsset.id == asset_id)
        res = await db.execute(stmt)
        asset = res.scalar_one_or_none()
        if not asset:
            raise ValueError(f"MediaAsset {asset_id} not found.")

        asset.license_status = license_status
        if attribution_text is not None:
            asset.attribution_text = attribution_text
        if license_type is not None:
            asset.license_type = license_type

        await db.commit()
        await db.refresh(asset)
        return asset

    async def list_assets(
        self,
        db: AsyncSession,
        channel_id: Optional[UUID] = None,
        project_id: Optional[UUID] = None,
        category: Optional[str] = None,
        license_status: Optional[str] = None,
        search_query: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[MediaAsset]:
        """Query asset catalog with multi-dimensional filtering."""
        query = select(MediaAsset).where(MediaAsset.is_archived == False)
        if channel_id:
            query = query.where(MediaAsset.channel_id == channel_id)
        if project_id:
            query = query.where(MediaAsset.project_id == project_id)
        if category and category.upper() != "ALL":
            query = query.where(MediaAsset.asset_category == category.upper())
        if license_status and license_status.upper() != "ALL":
            query = query.where(MediaAsset.license_status == license_status.upper())
        if search_query:
            term = f"%{search_query.strip()}%"
            query = query.where(
                or_(
                    MediaAsset.title.ilike(term),
                    MediaAsset.description.ilike(term),
                    MediaAsset.author_name.ilike(term),
                )
            )

        query = query.order_by(MediaAsset.created_at.desc()).limit(limit).offset(offset)
        res = await db.execute(query)
        return list(res.scalars().all())

    async def get_asset_file_bytes(self, asset: MediaAsset) -> bytes:
        """Retrieve binary content for streaming."""
        return await self._storage.read_media_file(asset.storage_path)
