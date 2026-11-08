"""Worker handlers for YouTube Analytics synchronization and reconciliation jobs."""

import datetime
from typing import Dict, Any, List
from uuid import UUID
from sqlalchemy import select

from app.core.logging import logger
from app.db.session import AsyncSessionLocal
from app.models.channel import Channel
from app.models.job import AutomationJob
from app.models.publishing import YouTubeVideo, PublishingJob
from app.services.youtube.analytics_service import YouTubeAnalyticsService
from app.workers.handlers.base import (
    BaseJobHandler,
    HardFailureException,
    JobCancelledException,
    ProgressCallback,
    CancellationChecker,
)


class YouTubeChannelAnalyticsSyncJobHandler(BaseJobHandler):
    """Syncs channel-level daily analytics snapshots over a date window."""

    def __init__(self, session_factory=None):
        self._session_factory = session_factory or AsyncSessionLocal

    async def validate(self, payload: Dict[str, Any]) -> None:
        if not payload or not isinstance(payload, dict):
            raise HardFailureException("Payload must be a dictionary.")
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
        start_date = payload.get("start_date") or (datetime.date.today() - datetime.timedelta(days=28)).isoformat()
        end_date = payload.get("end_date") or datetime.date.today().isoformat()

        async with self._session_factory() as db:
            ch_stmt = select(Channel).where(Channel.id == channel_id)
            res = await db.execute(ch_stmt)
            channel = res.scalar_one_or_none()
            if not channel:
                raise HardFailureException(f"Channel {channel_id} not found.")

            await update_progress(20, "Querying YouTube Analytics API")
            snapshots = await YouTubeAnalyticsService.sync_channel_daily_snapshots(
                db=db,
                channel=channel,
                start_date=start_date,
                end_date=end_date,
            )
            await update_progress(80, "Committing channel analytics snapshots")
            await db.commit()

            return {
                "channel_id": str(channel_id),
                "snapshots_synced": len(snapshots),
                "start_date": start_date,
                "end_date": end_date,
            }


class YouTubeVideoAnalyticsSyncJobHandler(BaseJobHandler):
    """Syncs video-level performance metrics for published videos."""

    def __init__(self, session_factory=None):
        self._session_factory = session_factory or AsyncSessionLocal

    async def validate(self, payload: Dict[str, Any]) -> None:
        if not payload or not isinstance(payload, dict):
            raise HardFailureException("Payload must be a dictionary.")
        if not payload.get("channel_id"):
            raise HardFailureException("Missing required parameter: 'channel_id'.")

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
        start_date = payload.get("start_date") or (datetime.date.today() - datetime.timedelta(days=28)).isoformat()
        end_date = payload.get("end_date") or datetime.date.today().isoformat()

        async with self._session_factory() as db:
            res = await db.execute(select(Channel).where(Channel.id == channel_id))
            channel = res.scalar_one_or_none()
            if not channel:
                raise HardFailureException(f"Channel {channel_id} not found.")

            await update_progress(30, "Querying video analytics breakdown")
            snaps = await YouTubeAnalyticsService.sync_video_snapshots(
                db=db,
                channel=channel,
                start_date=start_date,
                end_date=end_date,
            )
            await update_progress(90, "Finalizing video snapshots")
            await db.commit()

            return {
                "channel_id": str(channel_id),
                "videos_synced": len(snaps),
            }


class YouTubeRetentionAnalyticsSyncJobHandler(BaseJobHandler):
    """Syncs second-by-second and 30s audience retention curves."""

    def __init__(self, session_factory=None):
        self._session_factory = session_factory or AsyncSessionLocal

    async def validate(self, payload: Dict[str, Any]) -> None:
        if not payload or not isinstance(payload, dict):
            raise HardFailureException("Payload must be a dictionary.")
        if not payload.get("channel_id"):
            raise HardFailureException("Missing required parameter: 'channel_id'.")

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
        video_ids = payload.get("video_ids") or []

        async with self._session_factory() as db:
            res = await db.execute(select(Channel).where(Channel.id == channel_id))
            channel = res.scalar_one_or_none()
            if not channel:
                raise HardFailureException(f"Channel {channel_id} not found.")

            if not video_ids:
                # Default to fetching published video IDs scoped strictly to this channel
                v_res = await db.execute(
                    select(YouTubeVideo.youtube_video_id)
                    .join(PublishingJob, YouTubeVideo.publishing_job_id == PublishingJob.id)
                    .where(PublishingJob.channel_id == channel_id)
                    .limit(10)
                )
                video_ids = [row[0] for row in v_res.all()]

            if not video_ids:
                video_ids = ["mock_vid_ai_agents_101"]

            await update_progress(40, f"Querying retention curves for {len(video_ids)} videos")
            ret_snaps = await YouTubeAnalyticsService.sync_audience_retention(
                db=db,
                channel=channel,
                video_ids=video_ids,
            )
            await db.commit()

            return {
                "channel_id": str(channel_id),
                "curves_synced": len(ret_snaps),
            }


class YouTubeTrafficAnalyticsSyncJobHandler(BaseJobHandler):
    """Syncs viewer discovery and traffic source distributions."""

    def __init__(self, session_factory=None):
        self._session_factory = session_factory or AsyncSessionLocal

    async def validate(self, payload: Dict[str, Any]) -> None:
        if not payload or not isinstance(payload, dict):
            raise HardFailureException("Payload must be a dictionary.")
        if not payload.get("channel_id"):
            raise HardFailureException("Missing required parameter: 'channel_id'.")

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
        start_date = payload.get("start_date") or (datetime.date.today() - datetime.timedelta(days=28)).isoformat()
        end_date = payload.get("end_date") or datetime.date.today().isoformat()

        async with self._session_factory() as db:
            res = await db.execute(select(Channel).where(Channel.id == channel_id))
            channel = res.scalar_one_or_none()
            if not channel:
                raise HardFailureException(f"Channel {channel_id} not found.")

            await update_progress(50, "Fetching discovery traffic sources")
            traf_snaps = await YouTubeAnalyticsService.sync_traffic_sources(
                db=db,
                channel=channel,
                start_date=start_date,
                end_date=end_date,
            )
            await db.commit()

            return {
                "channel_id": str(channel_id),
                "traffic_sources_synced": len(traf_snaps),
            }


class YouTubeAnalyticsReconciliationJobHandler(BaseJobHandler):
    """Executes a full multi-dimensional analytics reconciliation and updates sync runs."""

    def __init__(self, session_factory=None):
        self._session_factory = session_factory or AsyncSessionLocal

    async def validate(self, payload: Dict[str, Any]) -> None:
        if not payload or not isinstance(payload, dict):
            raise HardFailureException("Payload must be a dictionary.")
        if not payload.get("channel_id"):
            raise HardFailureException("Missing required parameter: 'channel_id'.")

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
        start_date = payload.get("start_date")
        end_date = payload.get("end_date")

        async with self._session_factory() as db:
            res = await db.execute(select(Channel).where(Channel.id == channel_id))
            channel = res.scalar_one_or_none()
            if not channel:
                raise HardFailureException(f"Channel {channel_id} not found.")

            await update_progress(10, "Starting full analytics reconciliation")
            sync_run = await YouTubeAnalyticsService.run_full_sync(
                db=db,
                channel=channel,
                start_date=start_date,
                end_date=end_date,
            )
            await update_progress(100, f"Reconciliation complete: {sync_run.records_synced} records")

            return {
                "channel_id": str(channel_id),
                "sync_run_id": str(sync_run.id),
                "records_synced": sync_run.records_synced,
                "status": sync_run.status,
                "duration_ms": sync_run.duration_ms,
            }
