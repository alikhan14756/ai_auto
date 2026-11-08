"""Worker handlers for YouTube video upload, resumption, and channel sync jobs."""

import uuid
from typing import Dict, Any, Optional
from uuid import UUID
from sqlalchemy import select

from app.core.logging import logger
from app.db.session import AsyncSessionLocal
from app.models.channel import Channel
from app.models.job import AutomationJob
from app.models.publishing import PublishingJob
from app.services.youtube.publishing_service import YouTubePublishingService
from app.services.youtube.oauth import YouTubeOAuthService
from app.workers.handlers.base import (
    BaseJobHandler,
    HardFailureException,
    JobCancelledException,
    ProgressCallback,
    CancellationChecker,
)


class YouTubeVideoUploadJobHandler(BaseJobHandler):
    """Executes or resumes chunked resumable media upload to YouTube."""

    def __init__(self, session_factory=None):
        self._session_factory = session_factory or AsyncSessionLocal

    async def validate(self, payload: Dict[str, Any]) -> None:
        if not payload or not isinstance(payload, dict):
            raise HardFailureException("Payload must be a non-empty dictionary.")
        if not payload.get("publishing_job_id"):
            raise HardFailureException("Missing required parameter: 'publishing_job_id'.")
        try:
            UUID(str(payload["publishing_job_id"]))
        except (ValueError, TypeError):
            raise HardFailureException(f"Invalid UUID for 'publishing_job_id': {payload.get('publishing_job_id')}")

    async def execute(
        self,
        job: AutomationJob,
        update_progress: ProgressCallback,
        is_cancelled: CancellationChecker,
    ) -> Dict[str, Any]:
        if await is_cancelled():
            raise JobCancelledException(f"Job {job.id} was cancelled before execution.")

        payload = job.payload or {}
        pub_job_id = UUID(str(payload["publishing_job_id"]))

        await update_progress(10, "INITIALIZING_UPLOAD_SESSION")
        if await is_cancelled():
            raise JobCancelledException(f"Job {job.id} was cancelled.")

        logger.info(f"[YouTubeWorker] Executing YouTube video upload for publishing_job: {pub_job_id}")

        async with self._session_factory() as session:
            await update_progress(25, "STREAMING_RESUMABLE_CHUNKS")
            try:
                pub_job = await YouTubePublishingService.execute_publishing_job(session, pub_job_id)
            except ValueError as val_err:
                logger.error(f"[YouTubeWorker] Non-retryable error in upload: {val_err}")
                raise HardFailureException(str(val_err)) from val_err

            await update_progress(90, "FINALIZING_YOUTUBE_METADATA")
            if await is_cancelled():
                raise JobCancelledException(f"Job {job.id} was cancelled.")

            yt_vid = pub_job.youtube_video
            await update_progress(100, "COMPLETED")

            return {
                "publishing_job_id": str(pub_job.id),
                "status": pub_job.status,
                "current_stage": pub_job.current_stage,
                "bytes_uploaded": pub_job.bytes_uploaded,
                "total_bytes": pub_job.total_bytes,
                "youtube_video_id": yt_vid.youtube_video_id if yt_vid else None,
                "published_video_url": yt_vid.published_video_url if yt_vid else None,
            }


class YouTubeChannelSyncJobHandler(BaseJobHandler):
    """Synchronizes YouTube channel statistics and verification status."""

    def __init__(self, session_factory=None):
        self._session_factory = session_factory or AsyncSessionLocal

    async def validate(self, payload: Dict[str, Any]) -> None:
        if not payload or not isinstance(payload, dict):
            raise HardFailureException("Payload must be a non-empty dictionary.")
        if not payload.get("channel_id"):
            raise HardFailureException("Missing required parameter: 'channel_id'.")
        try:
            UUID(str(payload["channel_id"]))
        except (ValueError, TypeError):
            raise HardFailureException(f"Invalid UUID for 'channel_id': {payload.get('channel_id')}")

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

        await update_progress(20, "CONNECTING_YOUTUBE_API")

        async with self._session_factory() as session:
            res = await session.execute(select(Channel).where(Channel.id == channel_id))
            channel = res.scalar_one_or_none()
            if not channel:
                raise HardFailureException(f"Channel {channel_id} not found")

            if not channel.oauth_refresh_token_encrypted:
                raise HardFailureException(f"Channel {channel.title} is not connected to YouTube OAuth")

            await update_progress(50, "FETCHING_CHANNEL_ANALYTICS")
            try:
                access_token, _ = await YouTubeOAuthService.refresh_access_token(
                    channel.oauth_refresh_token_encrypted
                )
                profile = await YouTubeOAuthService.fetch_channel_profile(access_token)

                channel.title = profile.get("title", channel.title)
                channel.description = profile.get("description", channel.description)
                channel.custom_url = profile.get("custom_url", channel.custom_url)
                channel.thumbnail_url = profile.get("thumbnail_url", channel.thumbnail_url)
                channel.subscriber_count = profile.get("subscriber_count", channel.subscriber_count)
                await session.commit()

                await update_progress(100, "COMPLETED")
                return {
                    "channel_id": str(channel.id),
                    "youtube_channel_id": channel.youtube_channel_id,
                    "title": channel.title,
                    "subscriber_count": channel.subscriber_count,
                }
            except Exception as exc:
                logger.error(f"[YouTubeWorker] Channel sync failed: {exc}")
                raise HardFailureException(str(exc)) from exc
