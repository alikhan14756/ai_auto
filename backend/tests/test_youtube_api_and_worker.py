"""Integration tests for YouTube REST API endpoints and durable worker handlers."""

import uuid
import pytest
from app.models.project import VideoProject
from app.models.publication import PublicationPackage
from app.models.qa import QARun
from app.models.job import AutomationJob
from app.services.qa.constants import QAVetoDecision
from app.services.youtube.mock_client import mock_youtube_client
from app.workers.registry import registry
from tests.conftest import auth_headers_for, TestingSessionLocal
from app.workers.handlers.youtube_publishing import (
    YouTubeVideoUploadJobHandler,
    YouTubeChannelSyncJobHandler,
)


@pytest.mark.asyncio
async def test_youtube_api_full_publishing_lifecycle(client, test_user, test_channel, db_session):
    """Test full API sequence: connect -> callback -> create publication -> upload -> progress."""
    headers = auth_headers_for(test_user)
    mock_youtube_client.reset()

    # 1. Connect URL endpoint
    conn_resp = client.get(f"/api/v1/youtube/connect?channel_id={test_channel.id}", headers=headers)
    assert conn_resp.status_code == 200
    conn_data = conn_resp.json()
    assert "authorization_url" in conn_data
    state = conn_data["state"]

    # 2. Callback endpoint
    cb_resp = client.get(f"/api/v1/youtube/oauth/callback?code=mock_code_123&state={state}")
    assert cb_resp.status_code == 200
    assert cb_resp.json()["status"] == "connected"

    # 3. Connection status endpoint
    status_resp = client.get(f"/api/v1/youtube/connection?channel_id={test_channel.id}", headers=headers)
    assert status_resp.status_code == 200
    assert status_resp.json()["connected"] is True

    # 4. Prepare verified project and package with approved QA run
    project = VideoProject(
        channel_id=test_channel.id,
        title="Full Lifecycle Video Production",
        state="READY_TO_PUBLISH",
    )
    db_session.add(project)
    await db_session.flush()

    package = PublicationPackage(project_id=project.id, status="APPROVED")
    db_session.add(package)
    await db_session.flush()

    qa_run = QARun(
        project_id=project.id,
        publication_package_id=package.id,
        run_number=1,
        status="COMPLETED",
        veto_decision=QAVetoDecision.APPROVED.value,
        can_publish=True,
    )
    db_session.add(qa_run)
    await db_session.commit()

    # 5. Create publication request
    pub_req = {
        "project_id": str(project.id),
        "channel_id": str(test_channel.id),
        "publication_package_id": str(package.id),
        "privacy_status": "unlisted",
        "synthetic_media_declared": True,
        "self_declared_made_for_kids": False,
    }
    create_resp = client.post("/api/v1/youtube/publications", json=pub_req, headers=headers)
    assert create_resp.status_code == 201
    pub_job_data = create_resp.json()
    pub_job_id = pub_job_data["id"]
    assert pub_job_data["status"] == "PENDING"
    assert pub_job_data["current_stage"] == "QUEUED"

    # 6. Trigger upload
    upload_resp = client.post(
        f"/api/v1/youtube/publications/{pub_job_id}/upload?async_worker=false",
        headers=headers,
    )
    assert upload_resp.status_code == 200
    uploaded_data = upload_resp.json()
    assert uploaded_data["status"] == "COMPLETED"
    assert uploaded_data["youtube_video_id"] is not None
    assert "https://www.youtube.com/watch?v=" in uploaded_data["published_video_url"]

    # 7. Check progress endpoint
    prog_resp = client.get(f"/api/v1/youtube/publications/{pub_job_id}/progress", headers=headers)
    assert prog_resp.status_code == 200
    prog_data = prog_resp.json()
    assert prog_data["status"] == "COMPLETED"
    assert prog_data["progress_percent"] == 100.0

    # 8. List publications history
    list_resp = client.get(f"/api/v1/youtube/publications?project_id={project.id}", headers=headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1


@pytest.mark.asyncio
async def test_durable_worker_handlers_upload_and_sync(db_session, test_user, test_channel):
    """Test registry execution of YOUTUBE_VIDEO_UPLOAD and YOUTUBE_CHANNEL_SYNC."""
    mock_youtube_client.reset()

    # 1. Prepare approved project
    project = VideoProject(channel_id=test_channel.id, title="Worker Test Project", state="READY_TO_PUBLISH")
    db_session.add(project)
    await db_session.flush()

    package = PublicationPackage(project_id=project.id, status="APPROVED")
    db_session.add(package)
    await db_session.flush()

    qa_run = QARun(
        project_id=project.id,
        publication_package_id=package.id,
        run_number=1,
        status="COMPLETED",
        veto_decision=QAVetoDecision.APPROVED.value,
        can_publish=True,
    )
    db_session.add(qa_run)
    await db_session.commit()

    from app.services.youtube.publishing_service import YouTubePublishingService
    pub_job = await YouTubePublishingService.create_publication_job(
        db=db_session,
        user_id=test_user.id,
        project_id=project.id,
        channel_id=test_channel.id,
        publication_package_id=package.id,
    )

    # 2. Test YOUTUBE_VIDEO_UPLOAD worker handler
    upload_handler = YouTubeVideoUploadJobHandler(session_factory=TestingSessionLocal)
    worker_job = AutomationJob(
        channel_id=test_channel.id,
        job_type="YOUTUBE_VIDEO_UPLOAD",
        payload={"publishing_job_id": str(pub_job.id)},
        idempotency_key=f"worker_upload_{uuid.uuid4().hex}",
    )
    db_session.add(worker_job)
    await db_session.commit()

    async def mock_progress(pct, stage):
        pass

    async def mock_is_cancelled():
        return False

    upload_result = await upload_handler.execute(
        worker_job,
        update_progress=mock_progress,
        is_cancelled=mock_is_cancelled,
    )
    assert upload_result["status"] == "COMPLETED"
    assert upload_result["youtube_video_id"] is not None

    # 3. Test YOUTUBE_CHANNEL_SYNC worker handler
    sync_handler = YouTubeChannelSyncJobHandler(session_factory=TestingSessionLocal)
    sync_job = AutomationJob(
        channel_id=test_channel.id,
        job_type="YOUTUBE_CHANNEL_SYNC",
        payload={"channel_id": str(test_channel.id)},
        idempotency_key=f"worker_sync_{uuid.uuid4().hex}",
    )
    db_session.add(sync_job)
    await db_session.commit()

    sync_result = await sync_handler.execute(
        sync_job,
        update_progress=mock_progress,
        is_cancelled=mock_is_cancelled,
    )
    assert sync_result["channel_id"] == str(test_channel.id)
    assert sync_result["subscriber_count"] > 0
