"""Version-aware QA cache invalidation and snapshot tracker."""

import hashlib
import json
from typing import Dict, List, Set
from app.services.qa.constants import QACategory
from app.services.qa.models import QAExecutionContext

# Component change to invalidated categories mapping
INVALIDATION_MAPPING: Dict[str, Set[str]] = {
    "script": {
        QACategory.FACTUAL_ACCURACY.value,
        QACategory.SCRIPT_QUALITY.value,
        QACategory.CAPTION_INTEGRITY.value,
        QACategory.SECURITY_PRIVACY.value,
        QACategory.YOUTUBE_POLICY.value,
    },
    "narration": {
        QACategory.NARRATION_AUDIO.value,
        QACategory.VIDEO_TECHNICAL.value,
        QACategory.CAPTION_INTEGRITY.value,
    },
    "visual_assets": {
        QACategory.VISUAL_ASSETS.value,
        QACategory.COPYRIGHT_LICENSING.value,
        QACategory.VIDEO_TECHNICAL.value,
    },
    "render": {
        QACategory.VIDEO_TECHNICAL.value,
        QACategory.PACKAGE_COMPLETENESS.value,
    },
    "thumbnail": {
        QACategory.THUMBNAIL_QUALITY.value,
        QACategory.PACKAGE_COMPLETENESS.value,
    },
    "metadata": {
        QACategory.METADATA_SEO.value,
        QACategory.SECURITY_PRIVACY.value,
        QACategory.YOUTUBE_POLICY.value,
        QACategory.PACKAGE_COMPLETENESS.value,
    },
}


class QAInvalidationTracker:
    """Computes artifact state hashes and identifies invalidated check categories."""

    @classmethod
    def compute_context_snapshot(cls, ctx: QAExecutionContext) -> Dict[str, str]:
        """Generate component hashes representing the current state of all production artifacts."""
        snapshot = {}

        # 1. Script
        script_txt = (
            getattr(ctx.script, "full_text", getattr(ctx.script, "content", "")) or ""
        ) if ctx.script else ""
        snapshot["script"] = hashlib.sha256(script_txt.encode("utf-8")).hexdigest()[:16]

        # 2. Narration
        audio_ref = str(getattr(ctx.narration_track, "id", "")) if ctx.narration_track else ""
        snapshot["narration"] = hashlib.sha256(audio_ref.encode("utf-8")).hexdigest()[:16]

        # 3. Visuals
        scenes_repr = "".join(
            f"{getattr(s, 'id', '')}:{getattr(s, 'selected_asset_id', getattr(s, 'media_asset_id', ''))}"
            for s in ctx.scenes
        )
        snapshot["visual_assets"] = hashlib.sha256(scenes_repr.encode("utf-8")).hexdigest()[:16]

        # 4. Render
        render_ref = str(getattr(ctx.render_job, "id", "")) if ctx.render_job else ""
        snapshot["render"] = hashlib.sha256(render_ref.encode("utf-8")).hexdigest()[:16]

        # 5. Thumbnail
        thumb_ref = str(getattr(ctx.thumbnail, "id", "")) + str(getattr(ctx.thumbnail, "version", 1)) if ctx.thumbnail else ""
        snapshot["thumbnail"] = hashlib.sha256(thumb_ref.encode("utf-8")).hexdigest()[:16]

        # 6. Metadata
        meta_repr = (getattr(ctx.metadata_draft, "title", "") or "") + (getattr(ctx.metadata_draft, "description", "") or "") if ctx.metadata_draft else ""
        snapshot["metadata"] = hashlib.sha256(meta_repr.encode("utf-8")).hexdigest()[:16]

        return snapshot

    @classmethod
    def get_invalidated_categories(
        cls,
        old_snapshot: Dict[str, str],
        new_snapshot: Dict[str, str],
    ) -> Set[str]:
        """Detect modified components and return the union of all invalidated categories."""
        if not old_snapshot:
            # If no previous run, all categories must be validated
            return {cat.value for cat in QACategory}

        invalidated_cats: Set[str] = set()
        for component, new_hash in new_snapshot.items():
            old_hash = old_snapshot.get(component)
            if old_hash != new_hash:
                invalidated_cats.update(INVALIDATION_MAPPING.get(component, set()))

        return invalidated_cats

    @classmethod
    async def detect_changes(
        cls,
        db,
        project_id,
        recorded_snapshot: Dict[str, str],
        publication_package_id=None,
    ):
        """Assembles context and detects component drift against recorded snapshot."""
        from app.services.qa_service import QAService

        ctx = await QAService.assemble_context(db, project_id, publication_package_id)
        current_snapshot = cls.compute_context_snapshot(ctx)

        changed_components = [
            comp
            for comp, new_h in current_snapshot.items()
            if recorded_snapshot.get(comp) != new_h
        ]

        class DriftResult:
            def __init__(self, has_drift: bool, invalidated_components: List[str]):
                self.has_drift = has_drift
                self.invalidated_components = invalidated_components

        return DriftResult(bool(changed_components), changed_components)
