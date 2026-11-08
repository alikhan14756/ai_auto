"""Thumbnail Domain Service for generating concepts, composing layers, and managing variants."""

import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.models.channel import Channel
from app.models.project import VideoProject
from app.models.script import Script
from app.models.thumbnail import Thumbnail
from app.models.user import User
from app.services.thumbnail.composition import ThumbnailComposer
from app.services.thumbnail.concepts import ThumbnailConceptGenerator
from app.services.thumbnail.validator import ThumbnailValidator


class ThumbnailService:
    """Manages the full lifecycle of project thumbnail concepts, rendering, and variant selection."""

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
    async def verify_thumbnail_ownership(cls, db: AsyncSession, thumbnail_id: UUID, user: User) -> Thumbnail:
        """Ensure current user owns the thumbnail."""
        stmt = (
            select(Thumbnail)
            .join(VideoProject, Thumbnail.project_id == VideoProject.id)
            .join(Channel, VideoProject.channel_id == Channel.id)
            .where(Thumbnail.id == thumbnail_id)
        )
        if user.role != "SUPER_ADMIN":
            stmt = stmt.where(Channel.user_id == user.id)

        res = await db.execute(stmt)
        thumb = res.scalars().first()
        if not thumb:
            raise PermissionError("Access denied or thumbnail not found.")
        return thumb

    @classmethod
    async def generate_concepts_and_render_variants(
        cls,
        db: AsyncSession,
        project_id: UUID,
        user: User,
    ) -> List[Thumbnail]:
        """Generate 3 contrasting thumbnail variants (A, B, C) and render base graphics."""
        project = await cls.verify_project_ownership(db, project_id, user)

        # Query latest script if available
        script_stmt = (
            select(Script)
            .where(Script.project_id == project_id)
            .order_by(Script.version.desc())
        )
        script_res = await db.execute(script_stmt)
        script = script_res.scalars().first()

        script_summary = script.hook if script else project.title
        concepts = ThumbnailConceptGenerator.generate_concepts(
            project_title=project.title,
            script_summary=script_summary,
        )

        out_dir = Path(settings.THUMBNAIL_OUTPUT_DIR).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)

        thumbnails: List[Thumbnail] = []

        for idx, concept in enumerate(concepts):
            thumb_id = uuid.uuid4()
            v_code = concept["variant_code"]
            out_filename = f"thumb_{project_id}_{v_code}_{thumb_id.hex[:6]}.png"
            out_path = str(out_dir / out_filename)

            # Procedural Render
            render_res = ThumbnailComposer.render_composition(
                output_path=out_path,
                headline_text=concept["headline_text"],
                subtitle_text=concept.get("subtitle_text"),
                style_preset=concept["style_preset"],
                accent_color_hex=concept["accent_color_hex"],
                layers=concept.get("composition_layers"),
            )

            # Validation Gate
            val_res = ThumbnailValidator.validate_thumbnail(out_path)

            thumb = Thumbnail(
                id=thumb_id,
                project_id=project.id,
                variant_code=v_code,
                storage_path=out_path,
                headline_text=concept["headline_text"],
                accent_color_hex=concept["accent_color_hex"],
                style_preset=concept["style_preset"],
                width=render_res["width"],
                height=render_res["height"],
                file_size_bytes=render_res["file_size_bytes"],
                format="PNG",
                composition_data={"layers": concept.get("composition_layers", [])},
                concept_data=concept,
                quality_status=val_res["status"],
                quality_report=val_res,
                version=1,
                is_selected=(idx == 0),  # Variant A selected by default
            )
            db.add(thumb)
            thumbnails.append(thumb)

        await db.commit()
        for t in thumbnails:
            await db.refresh(t)

        logger.info(f"Generated {len(thumbnails)} thumbnail variants for project {project_id}")
        return thumbnails

    @classmethod
    async def update_thumbnail_composition(
        cls,
        db: AsyncSession,
        thumbnail_id: UUID,
        user: User,
        headline_text: Optional[str] = None,
        subtitle_text: Optional[str] = None,
        style_preset: Optional[str] = None,
        accent_color_hex: Optional[str] = None,
        layers: Optional[List[Dict[str, Any]]] = None,
    ) -> Thumbnail:
        """Edit composition layers, headline typography, and re-render."""
        thumb = await cls.verify_thumbnail_ownership(db, thumbnail_id, user)

        if headline_text is not None:
            thumb.headline_text = headline_text
        if style_preset is not None:
            thumb.style_preset = style_preset
        if accent_color_hex is not None:
            thumb.accent_color_hex = accent_color_hex
        if layers is not None:
            thumb.composition_data = {"layers": layers}

        # Re-render file
        render_res = ThumbnailComposer.render_composition(
            output_path=thumb.storage_path,
            headline_text=thumb.headline_text,
            subtitle_text=subtitle_text,
            style_preset=thumb.style_preset,
            accent_color_hex=thumb.accent_color_hex,
            layers=thumb.composition_data.get("layers"),
        )

        val_res = ThumbnailValidator.validate_thumbnail(thumb.storage_path)

        thumb.file_size_bytes = render_res["file_size_bytes"]
        thumb.quality_status = val_res["status"]
        thumb.quality_report = val_res
        thumb.version += 1

        await db.commit()
        await db.refresh(thumb)
        return thumb

    @classmethod
    async def select_thumbnail(cls, db: AsyncSession, thumbnail_id: UUID, user: User) -> Thumbnail:
        """Mark variant as the project's selected thumbnail."""
        thumb = await cls.verify_thumbnail_ownership(db, thumbnail_id, user)

        # Unselect all other thumbnails for this project
        unselect_stmt = (
            update(Thumbnail)
            .where(Thumbnail.project_id == thumb.project_id)
            .values(is_selected=False)
        )
        await db.execute(unselect_stmt)

        thumb.is_selected = True
        await db.commit()
        await db.refresh(thumb)
        return thumb

    @classmethod
    async def get_project_thumbnails(cls, db: AsyncSession, project_id: UUID, user: User) -> List[Thumbnail]:
        """List all thumbnails for a project."""
        await cls.verify_project_ownership(db, project_id, user)
        stmt = (
            select(Thumbnail)
            .where(Thumbnail.project_id == project_id)
            .order_by(Thumbnail.variant_code.asc())
        )
        res = await db.execute(stmt)
        return res.scalars().all()
