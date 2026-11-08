"""SEO Metadata Domain Service for generating, scoring, updating, and approving YouTube metadata."""

import uuid
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.channel import Channel
from app.models.project import VideoProject
from app.models.script import Script
from app.models.scene import Scene
from app.models.topic import ResearchSource
from app.models.metadata import VideoMetadataDraft
from app.models.thumbnail import Thumbnail
from app.models.user import User
from app.services.seo.metadata_generator import SEOMetadataGenerator
from app.services.seo.scorer import SEOMetadataScorer


class MetadataService:
    """Orchestrates structured YouTube metadata drafting, chaptering, evaluation, and approval."""

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
    async def verify_metadata_ownership(cls, db: AsyncSession, metadata_id: UUID, user: User) -> VideoMetadataDraft:
        """Ensure current user owns the metadata draft."""
        stmt = (
            select(VideoMetadataDraft)
            .join(VideoProject, VideoMetadataDraft.project_id == VideoProject.id)
            .join(Channel, VideoProject.channel_id == Channel.id)
            .where(VideoMetadataDraft.id == metadata_id)
        )
        if user.role != "SUPER_ADMIN":
            stmt = stmt.where(Channel.user_id == user.id)

        res = await db.execute(stmt)
        draft = res.scalars().first()
        if not draft:
            raise PermissionError("Access denied or metadata draft not found.")
        return draft

    @classmethod
    async def generate_project_metadata(
        cls,
        db: AsyncSession,
        project_id: UUID,
        user: User,
        target_keywords: Optional[List[str]] = None,
    ) -> VideoMetadataDraft:
        """Generate complete, verified YouTube SEO metadata package based on project context."""
        project = await cls.verify_project_ownership(db, project_id, user)

        # 1. Fetch script and scenes
        script_stmt = (
            select(Script)
            .where(Script.project_id == project_id)
            .order_by(Script.version.desc())
        )
        script_res = await db.execute(script_stmt)
        script = script_res.scalars().first()
        summary = script.hook if script else project.title

        # Scenes for chapter timestamps
        scenes_stmt = (
            select(Scene)
            .where(Scene.project_id == project_id)
            .order_by(Scene.scene_order.asc())
        )
        scenes_res = await db.execute(scenes_stmt)
        scenes = scenes_res.scalars().all()
        scene_dicts = [
            {
                "title": sc.visual_directive,
                "start_time_seconds": float(idx * (sc.duration_seconds or 5.0)),
                "duration_seconds": float(sc.duration_seconds or 5.0),
            }
            for idx, sc in enumerate(scenes)
        ]

        # 2. Fetch research sources if attached
        sources = []
        if project.topic_id:
            src_stmt = select(ResearchSource).where(ResearchSource.topic_id == project.topic_id)
            src_res = await db.execute(src_stmt)
            sources = [{"title": s.title, "url": s.url} for s in src_res.scalars().all()]

        # 3. Selected thumbnail headline for pairing score
        thumb_stmt = (
            select(Thumbnail)
            .where(Thumbnail.project_id == project_id, Thumbnail.is_selected == True)
        )
        thumb_res = await db.execute(thumb_stmt)
        selected_thumb = thumb_res.scalars().first()
        thumb_headline = selected_thumb.headline_text if selected_thumb else None

        # 4. Generate Metadata Payload
        payload = SEOMetadataGenerator.generate_full_metadata(
            topic_title=project.title,
            script_summary=summary,
            keywords=target_keywords,
            scenes=scene_dicts,
            research_sources=sources,
            total_duration_seconds=float(project.actual_duration_seconds or project.target_duration_seconds or 300.0),
        )

        # 5. Score Metadata
        score_report = SEOMetadataScorer.score_metadata_package(
            title=payload["title"],
            description=payload["description"],
            tags=payload["tags"],
            chapters=payload["chapters"],
            thumbnail_headline=thumb_headline,
            keywords=target_keywords,
        )

        draft = VideoMetadataDraft(
            id=uuid.uuid4(),
            project_id=project.id,
            title=payload["title"],
            title_candidates=payload["title_candidates"],
            description=payload["description"],
            tags=payload["tags"],
            hashtags=payload["hashtags"],
            chapters=payload["chapters"],
            pinned_comment=payload.get("pinned_comment"),
            synthetic_media_disclosure=True,
            seo_score=score_report["seo_score"],
            seo_report=score_report,
            pairing_score=score_report["pairing_score"],
            pairing_report=score_report.get("pairing_analysis") or {},
            version=1,
            is_approved=False,
        )
        db.add(draft)
        await db.commit()
        await db.refresh(draft)

        logger.info(f"Generated SEO metadata draft {draft.id} with score {draft.seo_score}")
        return draft

    @classmethod
    async def update_metadata_draft(
        cls,
        db: AsyncSession,
        metadata_id: UUID,
        user: User,
        title: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        hashtags: Optional[List[str]] = None,
        chapters: Optional[List[Dict[str, Any]]] = None,
        pinned_comment: Optional[str] = None,
    ) -> VideoMetadataDraft:
        """Update draft elements and re-evaluate SEO score."""
        draft = await cls.verify_metadata_ownership(db, metadata_id, user)

        if title is not None:
            draft.title = title
        if description is not None:
            draft.description = description
        if tags is not None:
            draft.tags = tags
        if hashtags is not None:
            draft.hashtags = hashtags
        if chapters is not None:
            draft.chapters = chapters
        if pinned_comment is not None:
            draft.pinned_comment = pinned_comment

        # Re-score
        thumb_stmt = (
            select(Thumbnail)
            .where(Thumbnail.project_id == draft.project_id, Thumbnail.is_selected == True)
        )
        thumb_res = await db.execute(thumb_stmt)
        selected_thumb = thumb_res.scalars().first()
        thumb_headline = selected_thumb.headline_text if selected_thumb else None

        score_report = SEOMetadataScorer.score_metadata_package(
            title=draft.title,
            description=draft.description,
            tags=draft.tags,
            chapters=draft.chapters,
            thumbnail_headline=thumb_headline,
        )

        draft.seo_score = score_report["seo_score"]
        draft.seo_report = score_report
        draft.pairing_score = score_report["pairing_score"]
        draft.pairing_report = score_report.get("pairing_analysis") or {}
        draft.version += 1

        await db.commit()
        await db.refresh(draft)
        return draft

    @classmethod
    async def approve_metadata(cls, db: AsyncSession, metadata_id: UUID, user: User) -> VideoMetadataDraft:
        """Mark metadata draft as approved."""
        draft = await cls.verify_metadata_ownership(db, metadata_id, user)
        draft.is_approved = True
        await db.commit()
        await db.refresh(draft)
        return draft

    @classmethod
    async def get_project_metadata(cls, db: AsyncSession, project_id: UUID, user: User) -> List[VideoMetadataDraft]:
        """List metadata drafts for a project."""
        await cls.verify_project_ownership(db, project_id, user)
        stmt = (
            select(VideoMetadataDraft)
            .where(VideoMetadataDraft.project_id == project_id)
            .order_by(VideoMetadataDraft.created_at.desc())
        )
        res = await db.execute(stmt)
        return res.scalars().all()
