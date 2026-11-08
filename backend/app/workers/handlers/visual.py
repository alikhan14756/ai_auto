"""Background worker handlers for Visual Planning, Asset Discovery, and Image Generation jobs."""

from typing import Any, Dict
from uuid import UUID

from app.core.logging import logger
from app.db.session import AsyncSessionLocal
from app.models.job import AutomationJob
from app.services.visual_planning import VisualPlanningService
from app.services.visual_asset import VisualAssetService
from app.workers.handlers.base import (
    BaseJobHandler,
    CancellationChecker,
    HardFailureException,
    JobCancelledException,
    ProgressCallback,
)


class StoryboardGenerationJobHandler(BaseJobHandler):
    """Processes asynchronous storyboard generation and scene sequencing."""

    def __init__(self, session_factory=None):
        self._session_factory = session_factory or AsyncSessionLocal

    async def validate(self, payload: Dict[str, Any]) -> None:
        if not payload or not isinstance(payload, dict):
            raise HardFailureException("Payload must be a non-empty JSON object.")
        project_id_raw = payload.get("project_id")
        if not project_id_raw:
            raise HardFailureException("Missing required parameter: 'project_id'.")
        try:
            UUID(str(project_id_raw))
        except (ValueError, TypeError):
            raise HardFailureException(f"Invalid UUID for 'project_id': {project_id_raw}")

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

        await update_progress(10, "INITIALIZING", "Loading project and script scenes")
        planner = VisualPlanningService()

        async with self._session_factory() as db:
            if await is_cancelled():
                raise JobCancelledException(f"Job {job.id} cancelled during initialization.")

            await update_progress(40, "ANALYZING_SCRIPT_AND_TIMINGS", "Correlating narration audio durations")

            if await is_cancelled():
                raise JobCancelledException(f"Job {job.id} cancelled before storyboard generation.")

            await update_progress(70, "DERIVING_SCENE_ARCHETYPES", "Classifying visual directives and generating prompts")

            storyboard = await planner.generate_storyboard(db=db, project_id=project_id)

            await update_progress(100, "COMPLETED", "Storyboard generated and validated successfully")

            return {
                "storyboard_id": str(storyboard.id),
                "project_id": str(storyboard.project_id),
                "version": storyboard.version,
                "aspect_ratio": storyboard.aspect_ratio,
                "scene_count": storyboard.scene_count,
                "status": storyboard.status,
            }


class VisualAssetSearchJobHandler(BaseJobHandler):
    """Processes background stock asset searches across external media providers."""

    def __init__(self, session_factory=None):
        self._session_factory = session_factory or AsyncSessionLocal

    async def validate(self, payload: Dict[str, Any]) -> None:
        if not payload or not isinstance(payload, dict):
            raise HardFailureException("Payload must be a non-empty JSON object.")
        if not payload.get("query"):
            raise HardFailureException("Missing required parameter: 'query'.")

    async def execute(
        self,
        job: AutomationJob,
        update_progress: ProgressCallback,
        is_cancelled: CancellationChecker,
    ) -> Dict[str, Any]:
        if await is_cancelled():
            raise JobCancelledException(f"Job {job.id} was cancelled before execution.")

        payload = job.payload or {}
        query = str(payload["query"])
        aspect_ratio = str(payload.get("aspect_ratio", "16:9"))
        provider_name = payload.get("provider")

        await update_progress(20, "INITIALIZING", "Preparing stock provider search")
        service = VisualAssetService()

        if await is_cancelled():
            raise JobCancelledException(f"Job {job.id} cancelled before search.")

        await update_progress(60, "QUERYING_PROVIDERS", f"Searching external stock archives for '{query}'")
        search_res = await service.search_stock(
            query=query,
            aspect_ratio=aspect_ratio,
            provider_name=provider_name,
            page=int(payload.get("page", 1)),
            per_page=int(payload.get("per_page", 10)),
        )

        await update_progress(100, "COMPLETED", f"Found {search_res.total_results} matching stock assets")

        return {
            "query": query,
            "total_results": search_res.total_results,
            "count": len(search_res.assets),
            "assets": [a.model_dump() for a in search_res.assets],
        }


class ImageGenerationJobHandler(BaseJobHandler):
    """Processes asynchronous AI image generation for scene storyboards."""

    def __init__(self, session_factory=None):
        self._session_factory = session_factory or AsyncSessionLocal

    async def validate(self, payload: Dict[str, Any]) -> None:
        if not payload or not isinstance(payload, dict):
            raise HardFailureException("Payload must be a non-empty JSON object.")
        for req_field in ["channel_id", "project_id", "prompt"]:
            if not payload.get(req_field):
                raise HardFailureException(f"Missing required parameter: '{req_field}'.")
        for uuid_field in ["channel_id", "project_id"]:
            try:
                UUID(str(payload[uuid_field]))
            except (ValueError, TypeError):
                raise HardFailureException(f"Invalid UUID for '{uuid_field}': {payload[uuid_field]}")
        if payload.get("scene_id"):
            try:
                UUID(str(payload["scene_id"]))
            except (ValueError, TypeError):
                raise HardFailureException(f"Invalid UUID for 'scene_id': {payload['scene_id']}")

    async def execute(
        self,
        job: AutomationJob,
        update_progress: ProgressCallback,
        is_cancelled: CancellationChecker,
    ) -> Dict[str, Any]:
        if await is_cancelled():
            raise JobCancelledException(f"Job {job.id} was cancelled before execution.")

        payload = job.payload or {}
        channel_id = UUID(str(payload["channel_id"]))
        project_id = UUID(str(payload["project_id"]))
        scene_id = UUID(str(payload["scene_id"])) if payload.get("scene_id") else None
        prompt = str(payload["prompt"])
        aspect_ratio = str(payload.get("aspect_ratio", "16:9"))
        style = str(payload.get("style", "photorealistic"))
        provider_name = payload.get("provider")

        await update_progress(20, "INITIALIZING", "Initializing AI image generation")
        service = VisualAssetService()

        if await is_cancelled():
            raise JobCancelledException(f"Job {job.id} cancelled before synthesis.")

        await update_progress(60, "SYNTHESIZING_IMAGE", "Executing generative canvas synthesis")

        async with self._session_factory() as db:
            asset = await service.generate_scene_image(
                db=db,
                channel_id=channel_id,
                project_id=project_id,
                scene_id=scene_id,
                prompt=prompt,
                aspect_ratio=aspect_ratio,
                style=style,
                provider_name=provider_name,
            )

            await update_progress(100, "COMPLETED", "Image generated, hashed, and assigned to storyboard")

            return {
                "asset_id": str(asset.id),
                "channel_id": str(asset.channel_id),
                "project_id": str(asset.project_id),
                "scene_id": str(asset.scene_id) if asset.scene_id else None,
                "storage_path": asset.storage_path,
                "sha256_hash": asset.sha256_hash,
                "width": asset.width,
                "height": asset.height,
            }
