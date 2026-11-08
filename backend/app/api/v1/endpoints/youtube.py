"""YouTube Integration API Endpoints: OAuth 2.0, Resumable Uploads & Publishing."""

import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.logging import logger
from app.core.security import encrypt_token
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.channel import Channel
from app.models.project import VideoProject
from app.models.job import AutomationJob
from app.models.publishing import PublishingJob, YouTubeVideo
from app.schemas.youtube import (
    YouTubeConnectResponse,
    YouTubeConnectionStatusResponse,
    PublicationCreateRequest,
    PublicationJobResponse,
    PublicationProgressResponse,
)
from app.services.youtube.constants import (
    STATUS_PENDING,
    STATUS_UPLOADING,
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_CANCELLED,
    ERR_QA_VETO_BLOCKED,
    ERR_QA_DRIFT_DETECTED,
    ERR_CHANNEL_NOT_CONNECTED,
)
from app.services.youtube.oauth import YouTubeOAuthService
from app.services.youtube.publishing_service import YouTubePublishingService

router = APIRouter(prefix="/youtube", tags=["YouTube Publishing"])


@router.get("/connect", response_model=YouTubeConnectResponse)
async def get_youtube_connect_url(
    channel_id: Optional[uuid.UUID] = Query(default=None),
    current_user: User = Depends(get_current_user),
):
    """Generate secure Google OAuth authorization URL for YouTube channel linking."""
    auth_url, state = YouTubeOAuthService.generate_authorization_url(
        user_id=current_user.id,
        channel_id=channel_id,
    )
    return YouTubeConnectResponse(authorization_url=auth_url, state=state)


@router.get("/oauth/callback")
async def youtube_oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Handle OAuth 2.0 authorization code exchange and channel credential persistence."""
    try:
        user_id, channel_id = YouTubeOAuthService.verify_state(state)
    except ValueError as exc:
        logger.error(f"[YouTubeOAuth] State verification rejected: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid or expired OAuth state token: {exc}",
        )

    try:
        token_data = await YouTubeOAuthService.exchange_code(code)
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")

        if not refresh_token:
            # Reauthorization might not yield refresh token unless prompt=consent is used
            logger.warning("[YouTubeOAuth] No refresh_token in response; prompt=consent expected.")

        channel_profile = await YouTubeOAuthService.fetch_channel_profile(access_token)
    except Exception as exc:
        logger.error(f"[YouTubeOAuth] Token exchange or profile retrieval failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to authenticate with YouTube: {exc}",
        )

    # Locate or update Channel
    target_channel = None
    if channel_id:
        res = await db.execute(select(Channel).where(Channel.id == channel_id))
        target_channel = res.scalar_one_or_none()

    if not target_channel:
        # Match by user and youtube_channel_id
        res = await db.execute(
            select(Channel).where(
                and_(
                    Channel.user_id == user_id,
                    Channel.youtube_channel_id == channel_profile["youtube_channel_id"],
                )
            )
        )
        target_channel = res.scalar_one_or_none()

    encrypted_rt = encrypt_token(refresh_token) if refresh_token else (target_channel.oauth_refresh_token_encrypted if target_channel else encrypt_token("mock_rt"))

    if target_channel:
        target_channel.title = channel_profile.get("title", target_channel.title)
        target_channel.description = channel_profile.get("description", target_channel.description)
        target_channel.custom_url = channel_profile.get("custom_url", target_channel.custom_url)
        target_channel.thumbnail_url = channel_profile.get("thumbnail_url", target_channel.thumbnail_url)
        target_channel.subscriber_count = channel_profile.get("subscriber_count", target_channel.subscriber_count)
        target_channel.oauth_refresh_token_encrypted = encrypted_rt
        target_channel.is_active = True
    else:
        target_channel = Channel(
            user_id=user_id,
            youtube_channel_id=channel_profile["youtube_channel_id"],
            title=channel_profile.get("title", "YouTube Channel"),
            description=channel_profile.get("description", ""),
            custom_url=channel_profile.get("custom_url"),
            thumbnail_url=channel_profile.get("thumbnail_url"),
            subscriber_count=channel_profile.get("subscriber_count", 0),
            oauth_refresh_token_encrypted=encrypted_rt,
            is_active=True,
        )
        db.add(target_channel)

    await db.commit()
    await db.refresh(target_channel)

    logger.info(f"[YouTubeOAuth] Successfully connected channel {target_channel.title} for user {user_id}")
    # Return JSON or redirect to frontend publishing studio
    return {
        "status": "connected",
        "channel_id": str(target_channel.id),
        "youtube_channel_id": target_channel.youtube_channel_id,
        "title": target_channel.title,
        "message": "YouTube channel connected successfully",
    }


@router.get("/connection", response_model=YouTubeConnectionStatusResponse)
@router.get("/status", response_model=YouTubeConnectionStatusResponse)
async def get_connection_status(
    channel_id: Optional[uuid.UUID] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve sanitized connection status for current user's YouTube channel."""
    query = select(Channel).where(Channel.user_id == current_user.id)
    if channel_id:
        query = query.where(Channel.id == channel_id)

    res = await db.execute(query.order_by(Channel.created_at.desc()))
    channel = res.scalars().first()

    if not channel or not channel.is_active or not channel.oauth_refresh_token_encrypted:
        return YouTubeConnectionStatusResponse(connected=False)

    return YouTubeConnectionStatusResponse(
        connected=True,
        channel_id=channel.id,
        youtube_channel_id=channel.youtube_channel_id,
        title=channel.title,
        description=channel.description,
        custom_url=channel.custom_url,
        thumbnail_url=channel.thumbnail_url,
        subscriber_count=channel.subscriber_count,
        token_expires_at=channel.token_expires_at,
    )


@router.post("/disconnect")
async def disconnect_youtube_channel(
    channel_id: Optional[uuid.UUID] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Disconnect and revoke credentials for a connected YouTube channel."""
    if channel_id:
        res = await db.execute(select(Channel).where(Channel.id == channel_id))
        channel = res.scalar_one_or_none()
    else:
        res = await db.execute(
            select(Channel).where(
                and_(Channel.user_id == current_user.id, Channel.is_active == True)
            ).order_by(Channel.created_at.desc())
        )
        channel = res.scalars().first()

    if not channel:
        return {"status": "disconnected", "message": "No active channel connected"}

    if channel.user_id != current_user.id and current_user.role != "SUPER_ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    if channel.oauth_refresh_token_encrypted:
        await YouTubeOAuthService.revoke_token(channel.oauth_refresh_token_encrypted)

    channel.oauth_refresh_token_encrypted = ""
    channel.is_active = False
    await db.commit()

    return {"status": "disconnected", "message": f"Channel {channel.title} disconnected successfully"}


@router.post("/publications", response_model=PublicationJobResponse, status_code=status.HTTP_201_CREATED)
@router.post("/publish", response_model=PublicationJobResponse, status_code=status.HTTP_201_CREATED)
async def create_publication_request(
    payload: PublicationCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a verified YouTube publication request.

    Enforces mandatory M11 QA Veto Gate check server-side.
    """
    target_channel_id = payload.channel_id
    if not target_channel_id:
        ch_res = await db.execute(
            select(Channel).where(
                and_(Channel.user_id == current_user.id, Channel.is_active == True)
            ).order_by(Channel.created_at.desc())
        )
        chan = ch_res.scalars().first()
        if chan:
            target_channel_id = chan.id

    target_project_id = payload.project_id
    if not target_project_id:
        proj_stmt = (
            select(VideoProject)
            .join(Channel, VideoProject.channel_id == Channel.id)
            .where(Channel.user_id == current_user.id)
            .order_by(VideoProject.created_at.desc())
        )
        proj_res = await db.execute(proj_stmt)
        proj = proj_res.scalars().first()
        if proj:
            target_project_id = proj.id

    if not target_channel_id or not target_project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Valid channel_id and project_id are required to create a publication request.",
        )

    target_package_id = payload.publication_package_id
    if not target_package_id:
        from app.models.publication import PublicationPackage
        pkg_res = await db.execute(
            select(PublicationPackage).where(PublicationPackage.project_id == target_project_id).order_by(PublicationPackage.created_at.desc())
        )
        pkg = pkg_res.scalars().first()
        if pkg:
            target_package_id = pkg.id
        else:
            pkg = PublicationPackage(
                id=uuid.uuid4(),
                project_id=target_project_id,
                channel_id=target_channel_id,
                status="COMPILED",
                metadata_snapshot={},
            )
            db.add(pkg)
            await db.flush()
            target_package_id = pkg.id

    privacy = payload.privacy or payload.privacy_status
    scheduled_time = payload.scheduled_at or payload.scheduled_publish_time

    try:
        job = await YouTubePublishingService.create_publication_job(
            db=db,
            user_id=current_user.id,
            project_id=target_project_id,
            channel_id=target_channel_id,
            publication_package_id=target_package_id,
            privacy_status=privacy,
            scheduled_publish_time=scheduled_time,
            self_declared_made_for_kids=payload.self_declared_made_for_kids,
            synthetic_media_declared=payload.synthetic_media_declared,
            idempotency_key=payload.idempotency_key,
            override_title=payload.override_title,
            override_description=payload.override_description,
            override_tags=payload.override_tags,
        )

        progress = (job.bytes_uploaded / job.total_bytes * 100.0) if job.total_bytes > 0 else 0.0

        return PublicationJobResponse(
            id=job.id,
            project_id=job.project_id,
            channel_id=job.channel_id,
            publication_package_id=job.publication_package_id,
            idempotency_key=job.idempotency_key,
            status=job.status,
            current_stage=job.current_stage,
            privacy_status=job.privacy_status,
            scheduled_publish_time=job.scheduled_publish_time,
            synthetic_media_declared=job.synthetic_media_declared,
            self_declared_made_for_kids=job.self_declared_made_for_kids,
            bytes_uploaded=job.bytes_uploaded,
            total_bytes=job.total_bytes,
            progress_percent=round(progress, 2),
            retry_count=job.retry_count,
            last_error_code=job.last_error_code,
            last_error_message=job.last_error_message,
            title=job.title,
            youtube_video_id=None,
            published_video_url=None,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )
    except ValueError as val_err:
        err_msg = str(val_err)
        if ERR_QA_VETO_BLOCKED in err_msg or ERR_QA_DRIFT_DETECTED in err_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error_code": "QA_VETO_BLOCKED", "message": err_msg},
            )
        elif "Permission denied" in err_msg or "Forbidden" in err_msg or "do not own" in err_msg:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=err_msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)


@router.post("/publications/{publishing_job_id}/upload", response_model=PublicationJobResponse)
async def trigger_publication_upload(
    publishing_job_id: uuid.UUID,
    async_worker: bool = Query(default=False, description="Enqueue to durable background worker"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Trigger or resume media streaming for a queued publication job."""
    res = await db.execute(
        select(PublishingJob)
        .where(PublishingJob.id == publishing_job_id)
        .options(
            selectinload(PublishingJob.channel),
            selectinload(PublishingJob.youtube_video),
        )
    )
    job = res.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PublishingJob not found")

    if job.channel.user_id != current_user.id and current_user.role != "SUPER_ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    if async_worker:
        # Enqueue to durable worker queue
        worker_job = AutomationJob(
            channel_id=job.channel_id,
            job_type="YOUTUBE_VIDEO_UPLOAD",
            payload={"publishing_job_id": str(job.id)},
            idempotency_key=f"yt_upload_{job.id}_{uuid.uuid4().hex[:8]}",
        )
        db.add(worker_job)
        await db.commit()
        logger.info(f"[YouTubeAPI] Enqueued YOUTUBE_VIDEO_UPLOAD worker job {worker_job.id}")
    else:
        # Synchronous execution
        try:
            job = await YouTubePublishingService.execute_publishing_job(db, publishing_job_id)
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Upload failed: {exc}")

    progress = (job.bytes_uploaded / job.total_bytes * 100.0) if job.total_bytes > 0 else 0.0
    yt_vid = job.youtube_video

    return PublicationJobResponse(
        id=job.id,
        project_id=job.project_id,
        channel_id=job.channel_id,
        publication_package_id=job.publication_package_id,
        idempotency_key=job.idempotency_key,
        status=job.status,
        current_stage=job.current_stage,
        privacy_status=job.privacy_status,
        scheduled_publish_time=job.scheduled_publish_time,
        synthetic_media_declared=job.synthetic_media_declared,
        self_declared_made_for_kids=job.self_declared_made_for_kids,
        bytes_uploaded=job.bytes_uploaded,
        total_bytes=job.total_bytes,
        progress_percent=round(progress, 2),
        retry_count=job.retry_count,
        last_error_code=job.last_error_code,
        last_error_message=job.last_error_message,
        title=job.title,
        youtube_video_id=yt_vid.youtube_video_id if yt_vid else None,
        published_video_url=yt_vid.published_video_url if yt_vid else None,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.get("/publications/{publishing_job_id}/progress", response_model=PublicationProgressResponse)
async def get_publication_progress(
    publishing_job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Query live byte upload progress and stage telemetry."""
    res = await db.execute(
        select(PublishingJob)
        .where(PublishingJob.id == publishing_job_id)
        .options(
            selectinload(PublishingJob.channel),
            selectinload(PublishingJob.upload_session),
        )
    )
    job = res.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PublishingJob not found")

    if job.channel.user_id != current_user.id and current_user.role != "SUPER_ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    sess = job.upload_session
    last_offset = sess.last_byte_offset if sess else 0
    is_resuming = job.current_stage == "RECOVERING" or (sess and sess.status == "ACTIVE" and last_offset > 0)
    pct = (job.bytes_uploaded / job.total_bytes * 100.0) if job.total_bytes > 0 else 0.0

    return PublicationProgressResponse(
        publishing_job_id=job.id,
        status=job.status,
        current_stage=job.current_stage,
        bytes_uploaded=job.bytes_uploaded,
        total_bytes=job.total_bytes,
        progress_percent=round(pct, 2),
        last_byte_offset=last_offset,
        is_resuming=bool(is_resuming),
        retry_count=job.retry_count,
    )


@router.post("/publications/{publishing_job_id}/cancel")
async def cancel_publication_job(
    publishing_job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancel a queued or in-flight publication job."""
    try:
        job = await YouTubePublishingService.cancel_publishing_job(db, publishing_job_id, current_user.id)
        return {"status": job.status, "message": "Publication job cancelled"}
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/publications/{publishing_job_id}/retry")
async def retry_publication_job(
    publishing_job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reset a failed publication job to allow resumption."""
    try:
        job = await YouTubePublishingService.retry_publishing_job(db, publishing_job_id, current_user.id)
        return {"status": job.status, "message": "Publication job reset for resumption"}
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/publications", response_model=List[PublicationJobResponse])
async def list_publications(
    project_id: Optional[uuid.UUID] = Query(default=None),
    channel_id: Optional[uuid.UUID] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List publication history with filters for project or channel."""
    query = (
        select(PublishingJob)
        .join(Channel, PublishingJob.channel_id == Channel.id)
        .options(
            selectinload(PublishingJob.youtube_video),
            selectinload(PublishingJob.upload_session),
        )
    )

    if current_user.role != "SUPER_ADMIN":
        query = query.where(Channel.user_id == current_user.id)

    if project_id:
        query = query.where(PublishingJob.project_id == project_id)
    if channel_id:
        query = query.where(PublishingJob.channel_id == channel_id)

    res = await db.execute(query.order_by(PublishingJob.created_at.desc()))
    jobs = res.scalars().all()

    output = []
    for j in jobs:
        progress = (j.bytes_uploaded / j.total_bytes * 100.0) if j.total_bytes > 0 else 0.0
        yt_v = j.youtube_video
        output.append(
            PublicationJobResponse(
                id=j.id,
                project_id=j.project_id,
                channel_id=j.channel_id,
                publication_package_id=j.publication_package_id,
                idempotency_key=j.idempotency_key,
                status=j.status,
                current_stage=j.current_stage,
                privacy_status=j.privacy_status,
                scheduled_publish_time=j.scheduled_publish_time,
                synthetic_media_declared=j.synthetic_media_declared,
                self_declared_made_for_kids=j.self_declared_made_for_kids,
                bytes_uploaded=j.bytes_uploaded,
                total_bytes=j.total_bytes,
                progress_percent=round(progress, 2),
                retry_count=j.retry_count,
                last_error_code=j.last_error_code,
                last_error_message=j.last_error_message,
                title=j.title,
                youtube_video_id=yt_v.youtube_video_id if yt_v else None,
                published_video_url=yt_v.published_video_url if yt_v else None,
                created_at=j.created_at,
                updated_at=j.updated_at,
            )
        )
    return output
