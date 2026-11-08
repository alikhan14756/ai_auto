"""Worker job handlers for Thumbnail Concepts, Composition Rendering, SEO Metadata, and Package Preparation."""

from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import select
from app.core.logging import logger
from app.db.session import AsyncSessionLocal
from app.models.channel import Channel
from app.models.job import AutomationJob
from app.models.project import VideoProject
from app.models.thumbnail import Thumbnail
from app.models.user import User
from app.services.thumbnail_service import ThumbnailService
from app.services.metadata_service import MetadataService
from app.services.publication import PublicationService
from app.workers.handlers.base import (
    BaseJobHandler,
    CancellationChecker,
    HardFailureException,
    JobCancelledException,
    ProgressCallback,
)


class ThumbnailConceptGenerationJobHandler(BaseJobHandler):
    """Generates 3 contrasting thumbnail variants for a project."""

    def __init__(self, session_factory=None):
        self._session_factory = session_factory or AsyncSessionLocal

    async def validate(self, payload: Dict[str, Any]) -> None:
        if not payload or not isinstance(payload, dict):
            raise HardFailureException("Payload must be a non-empty JSON object.")
        if not payload.get("project_id"):
            raise HardFailureException("Missing required parameter: 'project_id'.")
        try:
            UUID(str(payload["project_id"]))
        except (ValueError, TypeError):
            raise HardFailureException(f"Invalid UUID for 'project_id': {payload.get('project_id')}")

    async def execute(
        self,
        job: AutomationJob,
        update_progress: ProgressCallback,
        is_cancelled: CancellationChecker,
    ) -> Dict[str, Any]:
        if await is_cancelled():
            raise JobCancelledException(f"Job {job.id} was cancelled before execution.")

        payload = job.payload or {}
        project_id = UUID(str(payload["project_id"]))
        user_id_raw = payload.get("user_id")

        await update_progress(10, "INITIALIZING_CONCEPTS")

        async with self._session_factory() as db:
            # Query user
            user = None
            if user_id_raw:
                u_stmt = select(User).where(User.id == UUID(str(user_id_raw)))
                u_res = await db.execute(u_stmt)
                user = u_res.scalars().first()

            if not user:
                # Resolve tenant owner directly from project channel
                u_stmt = (
                    select(User)
                    .join(Channel, User.id == Channel.user_id)
                    .join(VideoProject, Channel.id == VideoProject.channel_id)
                    .where(VideoProject.id == project_id)
                )
                u_res = await db.execute(u_stmt)
                user = u_res.scalars().first()
                if not user:
                    raise HardFailureException("No authorized user found for project.")

            await update_progress(35, "GENERATING_CREATIVE_CONCEPTS")

            if await is_cancelled():
                raise JobCancelledException(f"Job {job.id} cancelled during concept generation.")

            thumbnails = await ThumbnailService.generate_concepts_and_render_variants(
                db=db,
                project_id=project_id,
                user=user,
            )

            await update_progress(85, "VALIDATING_THUMBNAIL_DIMENSIONS")

            results = [
                {
                    "thumbnail_id": str(t.id),
                    "variant_code": t.variant_code,
                    "headline_text": t.headline_text,
                    "quality_status": t.quality_status,
                    "file_size_bytes": t.file_size_bytes,
                }
                for t in thumbnails
            ]

            await update_progress(100, "COMPLETED")
            return {
                "project_id": str(project_id),
                "variant_count": len(thumbnails),
                "thumbnails": results,
            }


class ThumbnailCompositionRenderJobHandler(BaseJobHandler):
    """Re-renders an individual thumbnail with edited typography, colors, or layers."""

    def __init__(self, session_factory=None):
        self._session_factory = session_factory or AsyncSessionLocal

    async def validate(self, payload: Dict[str, Any]) -> None:
        if not payload or not isinstance(payload, dict):
            raise HardFailureException("Payload must be a non-empty JSON object.")
        if not payload.get("thumbnail_id"):
            raise HardFailureException("Missing required parameter: 'thumbnail_id'.")
        try:
            UUID(str(payload["thumbnail_id"]))
        except (ValueError, TypeError):
            raise HardFailureException(f"Invalid UUID for 'thumbnail_id': {payload.get('thumbnail_id')}")

    async def execute(
        self,
        job: AutomationJob,
        update_progress: ProgressCallback,
        is_cancelled: CancellationChecker,
    ) -> Dict[str, Any]:
        if await is_cancelled():
            raise JobCancelledException(f"Job {job.id} was cancelled before execution.")

        payload = job.payload or {}
        thumbnail_id = UUID(str(payload["thumbnail_id"]))
        user_id_raw = payload.get("user_id")

        await update_progress(20, "COMPOSING_LAYERS")

        async with self._session_factory() as db:
            user = None
            if user_id_raw:
                u_stmt = select(User).where(User.id == UUID(str(user_id_raw)))
                u_res = await db.execute(u_stmt)
                user = u_res.scalars().first()

            if not user:
                u_stmt = (
                    select(User)
                    .join(Channel, User.id == Channel.user_id)
                    .join(VideoProject, Channel.id == VideoProject.channel_id)
                    .join(Thumbnail, VideoProject.id == Thumbnail.project_id)
                    .where(Thumbnail.id == thumbnail_id)
                )
                u_res = await db.execute(u_stmt)
                user = u_res.scalars().first()
                if not user:
                    raise HardFailureException("No authorized user found for thumbnail.")

            thumb = await ThumbnailService.update_thumbnail_composition(
                db=db,
                thumbnail_id=thumbnail_id,
                user=user,
                headline_text=payload.get("headline_text"),
                subtitle_text=payload.get("subtitle_text"),
                style_preset=payload.get("style_preset"),
                accent_color_hex=payload.get("accent_color_hex"),
                layers=payload.get("layers"),
            )

            await update_progress(100, "COMPLETED")
            return {
                "thumbnail_id": str(thumb.id),
                "variant_code": thumb.variant_code,
                "version": thumb.version,
                "file_size_bytes": thumb.file_size_bytes,
                "quality_status": thumb.quality_status,
            }


class SEOMetadataGenerationJobHandler(BaseJobHandler):
    """Generates structured titles, descriptions, chapters, and tags for a project."""

    def __init__(self, session_factory=None):
        self._session_factory = session_factory or AsyncSessionLocal

    async def validate(self, payload: Dict[str, Any]) -> None:
        if not payload or not isinstance(payload, dict):
            raise HardFailureException("Payload must be a non-empty JSON object.")
        if not payload.get("project_id"):
            raise HardFailureException("Missing required parameter: 'project_id'.")
        try:
            UUID(str(payload["project_id"]))
        except (ValueError, TypeError):
            raise HardFailureException(f"Invalid UUID for 'project_id': {payload.get('project_id')}")

    async def execute(
        self,
        job: AutomationJob,
        update_progress: ProgressCallback,
        is_cancelled: CancellationChecker,
    ) -> Dict[str, Any]:
        if await is_cancelled():
            raise JobCancelledException(f"Job {job.id} was cancelled before execution.")

        payload = job.payload or {}
        project_id = UUID(str(payload["project_id"]))
        user_id_raw = payload.get("user_id")
        keywords = payload.get("keywords")

        await update_progress(15, "EXTRACTING_VIDEO_CONTEXT")

        async with self._session_factory() as db:
            user = None
            if user_id_raw:
                u_stmt = select(User).where(User.id == UUID(str(user_id_raw)))
                u_res = await db.execute(u_stmt)
                user = u_res.scalars().first()

            if not user:
                u_stmt = (
                    select(User)
                    .join(Channel, User.id == Channel.user_id)
                    .join(VideoProject, Channel.id == VideoProject.channel_id)
                    .where(VideoProject.id == project_id)
                )
                u_res = await db.execute(u_stmt)
                user = u_res.scalars().first()
                if not user:
                    raise HardFailureException("No authorized user found for project.")

            await update_progress(45, "SYNTHESIZING_METADATA_AND_CHAPTERS")

            draft = await MetadataService.generate_project_metadata(
                db=db,
                project_id=project_id,
                user=user,
                target_keywords=keywords,
            )

            await update_progress(85, "EVALUATING_SEO_AND_PAIRING")

            await update_progress(100, "COMPLETED")
            return {
                "metadata_id": str(draft.id),
                "title": draft.title,
                "seo_score": draft.seo_score,
                "pairing_score": draft.pairing_score,
                "chapter_count": len(draft.chapters),
            }


class PublicationPackagePreparationJobHandler(BaseJobHandler):
    """Bundles completed render, thumbnail, and metadata into a publication package."""

    def __init__(self, session_factory=None):
        self._session_factory = session_factory or AsyncSessionLocal

    async def validate(self, payload: Dict[str, Any]) -> None:
        if not payload or not isinstance(payload, dict):
            raise HardFailureException("Payload must be a non-empty JSON object.")
        if not payload.get("project_id"):
            raise HardFailureException("Missing required parameter: 'project_id'.")
        try:
            UUID(str(payload["project_id"]))
        except (ValueError, TypeError):
            raise HardFailureException(f"Invalid UUID for 'project_id': {payload.get('project_id')}")

    async def execute(
        self,
        job: AutomationJob,
        update_progress: ProgressCallback,
        is_cancelled: CancellationChecker,
    ) -> Dict[str, Any]:
        if await is_cancelled():
            raise JobCancelledException(f"Job {job.id} was cancelled before execution.")

        payload = job.payload or {}
        project_id = UUID(str(payload["project_id"]))
        user_id_raw = payload.get("user_id")

        await update_progress(25, "ASSEMBLING_COMPONENTS")

        async with self._session_factory() as db:
            user = None
            if user_id_raw:
                u_stmt = select(User).where(User.id == UUID(str(user_id_raw)))
                u_res = await db.execute(u_stmt)
                user = u_res.scalars().first()

            if not user:
                u_stmt = (
                    select(User)
                    .join(Channel, User.id == Channel.user_id)
                    .join(VideoProject, Channel.id == VideoProject.channel_id)
                    .where(VideoProject.id == project_id)
                )
                u_res = await db.execute(u_stmt)
                user = u_res.scalars().first()
                if not user:
                    raise HardFailureException("No authorized user found for project.")

            pkg = await PublicationService.assemble_package(
                db=db,
                project_id=project_id,
                user=user,
            )

            await update_progress(100, "COMPLETED")
            return {
                "package_id": str(pkg.id),
                "status": pkg.status,
                "manifest": pkg.package_manifest,
            }
