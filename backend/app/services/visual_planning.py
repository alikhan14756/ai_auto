"""Visual Storyboard Planning Service.
Analyzes approved scripts, incorporates voiceover timing, and generates structured visual storyboards.
"""

import re
from typing import List, Optional, Dict, Any
from uuid import UUID
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.project import VideoProject
from app.models.script import Script
from app.models.scene import Scene
from app.models.voice import NarrationTrack, Voiceover
from app.models.storyboard import Storyboard
from app.models.media import MediaAsset


class VisualPlanningService:
    """Orchestrates storyboard generation, visual archetype classification, and scene sequencing."""

    STOPWORDS = {
        "the", "a", "an", "in", "on", "at", "to", "for", "with", "by", "about",
        "and", "or", "but", "so", "this", "that", "these", "those", "is", "are",
        "was", "were", "be", "been", "being", "have", "has", "had", "do", "does",
        "did", "will", "would", "shall", "should", "can", "could", "may", "might",
        "we", "you", "they", "it", "he", "she", "our", "your", "their", "its",
        "of", "from", "up", "down", "out", "over", "under", "again", "further",
        "then", "once", "here", "there", "when", "where", "why", "how", "all",
        "video", "build", "show", "here", "let", "lets", "make", "using", "today",
    }

    @classmethod
    def extract_keywords(cls, text: str, max_keywords: int = 5) -> List[str]:
        """Extract high-signal technical and topical keywords from text."""
        clean = re.sub(r"[^\w\s-]", " ", text.lower())
        tokens = [t.strip() for t in clean.split() if len(t.strip()) > 2]
        filtered = [t for t in tokens if t not in cls.STOPWORDS]
        # Preserve order while deduplicating
        seen = set()
        unique = []
        for word in filtered:
            if word not in seen:
                seen.add(word)
                unique.append(word)
        return unique[:max_keywords]

    @classmethod
    def infer_visual_purpose_and_type(
        cls,
        scene_index: int,
        total_scenes: int,
        directive: str,
        narration: str,
    ) -> Dict[str, str]:
        """Classify scene purpose, suggested asset type, and transition hint."""
        text_corpus = f"{directive} {narration}".lower()

        # Purpose classification
        if scene_index == 1:
            purpose = "HOOK_ENGAGEMENT"
            transition = "CUT"
        elif scene_index == total_scenes:
            purpose = "SUMMARY"
            transition = "FADE"
        elif any(k in text_corpus for k in ["code", "terminal", "function", "syntax", "editor", "implementation"]):
            purpose = "DEMONSTRATION"
            transition = "CUT"
        elif any(k in text_corpus for k in ["compare", "vs", "versus", "benchmark", "performance", "metrics"]):
            purpose = "COMPARISON"
            transition = "SLIDE_LEFT"
        else:
            purpose = "CONCEPT_EXPLANATION"
            transition = "ZOOM_IN"

        # Asset type classification
        if any(k in text_corpus for k in ["terminal", "python", "javascript", "code", "typescript", "cli", "syntax"]):
            asset_type = "CODE_DEMONSTRATION"
        elif any(k in text_corpus for k in ["interface", "dashboard", "browser", "website", "ui", "screen", "click"]):
            asset_type = "SOFTWARE_INTERFACE"
        elif any(k in text_corpus for k in ["architecture", "flowchart", "pipeline", "system", "diagram", "topology"]):
            asset_type = "DIAGRAM"
        elif any(k in text_corpus for k in ["chart", "retention", "graph", "analytics", "statistics"]):
            asset_type = "CHART"
        elif any(k in text_corpus for k in ["b-roll", "broll", "workspace", "studio", "desk", "lifestyle", "nature"]):
            asset_type = "STOCK_FOOTAGE"
        elif any(k in text_corpus for k in ["illustration", "vector", "abstract", "icon", "mascot"]):
            asset_type = "ILLUSTRATION"
        else:
            asset_type = "GENERATED_IMAGE"

        return {
            "visual_purpose": purpose,
            "suggested_asset_type": asset_type,
            "transition": transition,
        }

    @classmethod
    def compose_image_prompt(
        cls,
        directive: str,
        narration: str,
        keywords: List[str],
        aspect_ratio: str,
        asset_type: str,
    ) -> str:
        """Construct a high-clarity generative prompt tailored for tech audiences and aspect ratios."""
        kw_str = ", ".join(keywords) if keywords else "technology, software"
        ratio_desc = "horizontal 16:9 landscape framing" if aspect_ratio == "16:9" else "vertical 9:16 portrait framing for mobile"

        base_prompt = f"Professional tech digital visual for YouTube: {directive}. "
        if asset_type == "CODE_DEMONSTRATION":
            base_prompt += "Clean modern dark-mode code editor interface showing clear syntax highlighting, dark slate background #090A0D, vivid ember accent accents. "
        elif asset_type == "DIAGRAM":
            base_prompt += "Crisp isometric architectural flowchart and system microservices node graph, minimalist neon data lines. "
        elif asset_type == "SOFTWARE_INTERFACE":
            base_prompt += "Modern minimalist web SaaS application interface, sleek dark glassmorphism card layout, typography. "
        else:
            base_prompt += f"Atmospheric developer workspace aesthetic, glowing monitors, cinematic lighting, focused tech ambiance. Key themes: {kw_str}. "

        base_prompt += f"Framing: {ratio_desc}, ultra-sharp 4K, no text misspellings, no blurry artifacts."
        return base_prompt

    async def generate_storyboard(
        self,
        db: AsyncSession,
        project_id: UUID,
        force_overwrite: bool = False,
    ) -> Storyboard:
        """Generate or synchronize a storyboard container and scene visual directives."""
        # 1. Load project with existing scenes, scripts, and narration tracks
        stmt = (
            select(VideoProject)
            .where(VideoProject.id == project_id)
            .options(
                selectinload(VideoProject.scripts),
                selectinload(VideoProject.scenes),
                selectinload(VideoProject.narration_tracks),
                selectinload(VideoProject.voiceovers),
            )
        )
        res = await db.execute(stmt)
        project = res.scalar_one_or_none()
        if not project:
            raise ValueError(f"VideoProject {project_id} not found.")

        # Determine target aspect ratio
        aspect_ratio = "9:16" if project.format == "SHORTS" else "16:9"

        # Find latest script and approved narration track
        latest_script = project.scripts[-1] if project.scripts else None
        active_track = next((t for t in reversed(project.narration_tracks) if t.is_approved), None)
        if not active_track and project.narration_tracks:
            active_track = project.narration_tracks[-1]

        # Map scene_id to actual voiceover duration
        voiceover_durations: Dict[str, Decimal] = {}
        if project.voiceovers:
            for vo in project.voiceovers:
                if vo.duration_seconds:
                    voiceover_durations[str(vo.scene_id)] = Decimal(str(vo.duration_seconds))

        # Check for existing storyboard
        sb_stmt = (
            select(Storyboard)
            .where(Storyboard.project_id == project_id)
            .options(selectinload(Storyboard.scenes).selectinload(Scene.selected_asset))
            .order_by(Storyboard.version.desc())
        )
        sb_res = await db.execute(sb_stmt)
        storyboard = sb_res.scalars().first()

        if not storyboard:
            storyboard = Storyboard(
                project_id=project_id,
                script_id=latest_script.id if latest_script else None,
                narration_track_id=active_track.id if active_track else None,
                version=1,
                status="DRAFT",
                aspect_ratio=aspect_ratio,
                scene_count=0,
                approved_scene_count=0,
            )
            db.add(storyboard)
            await db.flush()
        else:
            storyboard.aspect_ratio = aspect_ratio
            if latest_script:
                storyboard.script_id = latest_script.id
            if active_track:
                storyboard.narration_track_id = active_track.id

        # 2. Process Scenes
        scenes: List[Scene] = sorted(project.scenes, key=lambda s: s.scene_order)
        total_scenes = len(scenes)

        for idx, scene in enumerate(scenes, start=1):
            scene.storyboard_id = storyboard.id

            # Classify purpose, asset type, and transition if not already configured or force_overwrite
            classified = self.infer_visual_purpose_and_type(
                scene_index=idx,
                total_scenes=total_scenes,
                directive=scene.visual_directive,
                narration=scene.narration_text,
            )

            if force_overwrite or not scene.visual_purpose or scene.visual_purpose == "CONCEPT_EXPLANATION":
                scene.visual_purpose = classified["visual_purpose"]
            if force_overwrite or not scene.suggested_asset_type or scene.suggested_asset_type == "GENERATED_IMAGE":
                scene.suggested_asset_type = classified["suggested_asset_type"]
            if force_overwrite or not scene.transition:
                scene.transition = classified["transition"]

            # Keywords and prompt
            if force_overwrite or not scene.search_keywords or len(scene.search_keywords) == 0:
                keywords = self.extract_keywords(f"{scene.narration_text} {scene.visual_directive}")
                scene.search_keywords = keywords
            else:
                keywords = scene.search_keywords

            if force_overwrite or not scene.image_prompt:
                scene.image_prompt = self.compose_image_prompt(
                    directive=scene.visual_directive,
                    narration=scene.narration_text,
                    keywords=keywords,
                    aspect_ratio=aspect_ratio,
                    asset_type=scene.suggested_asset_type or classified["suggested_asset_type"],
                )

            # Timing alignment: Use actual voiceover duration if present, else fallback
            vo_dur = voiceover_durations.get(str(scene.id))
            if vo_dur and vo_dur > Decimal("0"):
                scene.duration_seconds = vo_dur
            elif not scene.duration_seconds or scene.duration_seconds == Decimal("0"):
                words = len(scene.narration_text.split())
                est_seconds = max(2.5, round(words / (140.0 / 60.0), 2))
                scene.duration_seconds = Decimal(str(est_seconds))

            if not scene.review_status:
                scene.review_status = "DRAFT"

        storyboard.scene_count = len(scenes)
        storyboard.approved_scene_count = sum(1 for s in scenes if s.review_status == "APPROVED")

        await db.commit()

        # Reload with relationships
        full_stmt = (
            select(Storyboard)
            .where(Storyboard.id == storyboard.id)
            .options(
                selectinload(Storyboard.scenes).selectinload(Scene.selected_asset),
                selectinload(Storyboard.script),
                selectinload(Storyboard.narration_track),
            )
        )
        final_res = await db.execute(full_stmt)
        return final_res.scalar_one()

    async def update_scene(
        self,
        db: AsyncSession,
        scene_id: UUID,
        updates: Dict[str, Any],
    ) -> Scene:
        """Update specific scene visual directives, purpose, keywords, or review status."""
        stmt = (
            select(Scene)
            .where(Scene.id == scene_id)
            .options(selectinload(Scene.selected_asset))
        )
        res = await db.execute(stmt)
        scene = res.scalar_one_or_none()
        if not scene:
            raise ValueError(f"Scene {scene_id} not found.")

        allowed_fields = {
            "visual_directive",
            "visual_purpose",
            "suggested_asset_type",
            "search_keywords",
            "image_prompt",
            "transition",
            "review_status",
            "selected_asset_id",
            "duration_seconds",
        }
        for field, val in updates.items():
            if field in allowed_fields and val is not None:
                setattr(scene, field, val)

        await db.commit()
        await db.refresh(scene)
        return scene

    async def reorder_scenes(
        self,
        db: AsyncSession,
        storyboard_id: UUID,
        ordered_scene_ids: List[UUID],
    ) -> List[Scene]:
        """Reorder scenes within a storyboard."""
        for new_order, s_id in enumerate(ordered_scene_ids, start=1):
            await db.execute(
                update(Scene)
                .where(Scene.id == s_id, Scene.storyboard_id == storyboard_id)
                .values(scene_order=new_order)
            )
        await db.commit()

        res = await db.execute(
            select(Scene)
            .where(Scene.storyboard_id == storyboard_id)
            .options(selectinload(Scene.selected_asset))
            .order_by(Scene.scene_order)
        )
        return list(res.scalars().all())

    async def approve_storyboard(
        self,
        db: AsyncSession,
        storyboard_id: UUID,
    ) -> Storyboard:
        """Approve storyboard and advance project workflow state."""
        stmt = (
            select(Storyboard)
            .where(Storyboard.id == storyboard_id)
            .options(
                selectinload(Storyboard.scenes).selectinload(Scene.selected_asset),
                selectinload(Storyboard.project),
            )
        )
        res = await db.execute(stmt)
        storyboard = res.scalar_one_or_none()
        if not storyboard:
            raise ValueError(f"Storyboard {storyboard_id} not found.")

        # Check licensing compliance of assigned assets
        for s in storyboard.scenes:
            asset = s.selected_asset
            if not asset and s.selected_asset_id:
                a_res = await db.execute(select(MediaAsset).where(MediaAsset.id == s.selected_asset_id))
                asset = a_res.scalar_one_or_none()
            if asset:
                if asset.license_status == "RESTRICTED":
                    raise ValueError(
                        f"Cannot approve storyboard: Scene {s.scene_order} has RESTRICTED asset '{asset.title}'."
                    )
                if asset.license_status == "LICENSE_REVIEW_REQUIRED":
                    raise ValueError(
                        f"Cannot approve storyboard: Scene {s.scene_order} requires license review ({asset.title}). Clear license before approval."
                    )

        # Mark all scenes approved
        for s in storyboard.scenes:
            s.review_status = "APPROVED"

        storyboard.status = "APPROVED"
        storyboard.approved_scene_count = len(storyboard.scenes)

        if storyboard.project:
            storyboard.project.state = "STORYBOARD_APPROVED"

        await db.commit()
        return storyboard
