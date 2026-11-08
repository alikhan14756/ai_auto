"""Background worker handler for DISCOVER_TOPICS jobs."""

import asyncio
from typing import Any, Dict
from uuid import UUID

from app.core.logging import logger
from app.db.session import AsyncSessionLocal
from app.models.job import AutomationJob
from app.providers.ai.factory import get_ai_provider
from app.services.topic_research import TopicResearchService
from app.workers.handlers.base import (
    BaseJobHandler,
    CancellationChecker,
    HardFailureException,
    JobCancelledException,
    ProgressCallback,
)


class TopicResearchJobHandler(BaseJobHandler):
    """Processes asynchronous topic ideation and discovery jobs in the background queue."""

    def __init__(self, session_factory=None):
        self._session_factory = session_factory or AsyncSessionLocal

    async def validate(self, payload: Dict[str, Any]) -> None:
        """Validate input payload before job execution."""
        if not payload or not isinstance(payload, dict):
            raise HardFailureException("Payload must be a non-empty JSON object.")

        channel_id_raw = payload.get("channel_id")
        if not channel_id_raw:
            raise HardFailureException("Missing required parameter: 'channel_id'.")

        try:
            UUID(str(channel_id_raw))
        except (ValueError, TypeError):
            raise HardFailureException(f"Invalid UUID format for 'channel_id': {channel_id_raw}")

        count = payload.get("count", 5)
        if not isinstance(count, int) or count < 1 or count > 20:
            raise HardFailureException(f"Parameter 'count' must be an integer between 1 and 20, got: {count}")

    async def execute(
        self,
        job: AutomationJob,
        update_progress: ProgressCallback,
        is_cancelled: CancellationChecker,
    ) -> Dict[str, Any]:
        """Execute topic discovery pipeline with stage progress reporting."""
        payload = job.payload or {}
        channel_id = UUID(str(payload["channel_id"]))
        niche_override = payload.get("niche_override")
        count = payload.get("count", 5)

        logger.info(f"Executing DISCOVER_TOPICS for job {job.id}, channel {channel_id}")

        # Stage 1: Initializing
        await update_progress(10, "INITIALIZING_RESEARCH")
        if await is_cancelled():
            raise JobCancelledException("Topic discovery job was cancelled by user.")

        # Stage 2: Loading Channel Context & Feeds
        await update_progress(30, "LOADING_CHANNEL_CONTEXT")
        if await is_cancelled():
            raise JobCancelledException("Topic discovery job was cancelled by user.")

        # Stage 3: AI Inference & Ideation
        await update_progress(60, "INVOKING_AI_PROVIDER")
        if await is_cancelled():
            raise JobCancelledException("Topic discovery job was cancelled by user.")

        # Session scoped database execution
        service = TopicResearchService(provider=get_ai_provider())
        async with (self._session_factory)() as session:
            discovered_topics = await service.discover_and_persist_topics(
                channel_id=channel_id,
                db=session,
                niche_override=niche_override,
                count=count,
            )

        # Stage 4: Scoring and Verification
        await update_progress(85, "SCORING_AND_PERSISTING")
        if await is_cancelled():
            raise JobCancelledException("Topic discovery job was cancelled by user.")

        # Stage 5: Finalizing
        await update_progress(100, "COMPLETED")

        top_score = float(discovered_topics[0].opportunity_score) if discovered_topics else 0.0
        return {
            "topics_discovered_count": len(discovered_topics),
            "topic_ids": [str(t.id) for t in discovered_topics],
            "highest_opportunity_score": top_score,
            "channel_id": str(channel_id),
        }
