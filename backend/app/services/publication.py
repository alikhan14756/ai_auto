"""Publication Package Service for bundling verified video renders, thumbnails, and SEO metadata."""

import uuid
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.channel import Channel
from app.models.project import VideoProject
from app.models.render import RenderJob
from app.models.thumbnail import Thumbnail
from app.models.metadata import VideoMetadataDraft
from app.models.publication import PublicationPackage
from app.models.user import User


class PublicationService:
    """Manages preparation and approval of complete publication packages."""

    @classmethod
    async def verify_project_ownership(cls, db: AsyncSession, project_id: UUID, user: User) -> VideoProject:
        """Ensure current user owns the project via channel membership."""
        stmt = (
            select(VideoProject)
            .join(Channel, VideoProject.channel_id == Channel.id)
            .where(VideoProject.id == project_id)
        )
        if user.role != "SUPER_ADMIN":
            stmt = stmt.where(Channel.user_id == user.id)

        res = await db.execute(stmt)
        project = res.scalars().first()
        if not project:
            raise PermissionError("Access denied or project not found.")
        return project

    @classmethod
    async def verify_package_ownership(cls, db: AsyncSession, package_id: UUID, user: User) -> PublicationPackage:
        """Ensure current user owns the publication package."""
        stmt = (
            select(PublicationPackage)
            .join(VideoProject, PublicationPackage.project_id == VideoProject.id)
            .join(Channel, VideoProject.channel_id == Channel.id)
            .where(PublicationPackage.id == package_id)
            .options(
                selectinload(PublicationPackage.render_job),
                selectinload(PublicationPackage.thumbnail),
                selectinload(PublicationPackage.metadata_draft),
            )
        )
        if user.role != "SUPER_ADMIN":
            stmt = stmt.where(Channel.user_id == user.id)

        res = await db.execute(stmt)
        pkg = res.scalars().first()
        if not pkg:
            raise PermissionError("Access denied or publication package not found.")
        return pkg

    @classmethod
    async def assemble_package(
        cls,
        db: AsyncSession,
        project_id: UUID,
        user: User,
    ) -> PublicationPackage:
        """Assemble latest completed render, selected thumbnail, and metadata into a publication package."""
        project = await cls.verify_project_ownership(db, project_id, user)

        # 1. Latest completed render job
        render_stmt = (
            select(RenderJob)
            .where(RenderJob.project_id == project_id, RenderJob.status == "COMPLETED")
            .order_by(RenderJob.created_at.desc())
        )
        render_res = await db.execute(render_stmt)
        render_job = render_res.scalars().first()

        # 2. Selected thumbnail
        thumb_stmt = (
            select(Thumbnail)
            .where(Thumbnail.project_id == project_id, Thumbnail.is_selected == True)
        )
        thumb_res = await db.execute(thumb_stmt)
        thumbnail = thumb_res.scalars().first()

        # 3. Latest metadata draft
        meta_stmt = (
            select(VideoMetadataDraft)
            .where(VideoMetadataDraft.project_id == project_id)
            .order_by(VideoMetadataDraft.is_approved.desc(), VideoMetadataDraft.created_at.desc())
        )
        meta_res = await db.execute(meta_stmt)
        metadata = meta_res.scalars().first()

        # Status determination
        has_all = bool(render_job and thumbnail and metadata)
        status = "READY_FOR_QA" if has_all else "DRAFT"

        manifest = {
            "project_title": project.title,
            "project_format": project.format,
            "has_video_render": bool(render_job),
            "video_render_path": render_job.output_video_path if render_job else None,
            "has_selected_thumbnail": bool(thumbnail),
            "thumbnail_path": thumbnail.storage_path if thumbnail else None,
            "has_metadata": bool(metadata),
            "title": metadata.title if metadata else project.title,
            "synthetic_media_declared": True,
        }

        # Check existing package
        pkg_stmt = select(PublicationPackage).where(PublicationPackage.project_id == project_id)
        pkg_res = await db.execute(pkg_stmt)
        package = pkg_res.scalars().first()

        if package:
            package.render_job_id = render_job.id if render_job else None
            package.thumbnail_id = thumbnail.id if thumbnail else None
            package.metadata_id = metadata.id if metadata else None
            package.status = status
            package.package_manifest = manifest
        else:
            package = PublicationPackage(
                id=uuid.uuid4(),
                project_id=project.id,
                render_job_id=render_job.id if render_job else None,
                thumbnail_id=thumbnail.id if thumbnail else None,
                metadata_id=metadata.id if metadata else None,
                status=status,
                package_manifest=manifest,
            )
            db.add(package)

        await db.commit()
        return await cls.verify_package_ownership(db, package.id, user)

    @classmethod
    async def approve_package(cls, db: AsyncSession, package_id: UUID, user: User) -> PublicationPackage:
        """Approve publication package for downstream QA and release."""
        package = await cls.verify_package_ownership(db, package_id, user)
        if package.status != "READY_FOR_QA":
            raise ValueError(
                f"Cannot approve package with status '{package.status}'. "
                "Package must be in 'READY_FOR_QA' status with video render, selected thumbnail, and metadata complete."
            )
        package.status = "APPROVED"
        await db.commit()
        await db.refresh(package)
        return package
