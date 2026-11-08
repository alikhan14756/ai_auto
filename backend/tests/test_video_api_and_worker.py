"""End-to-end integration tests for Video Timeline, Renders REST API, and Worker Handlers."""

import os
from decimal import Decimal
import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import auth_headers_for, TestingSessionLocal
from app.models.channel import Channel
from app.models.job import AutomationJob
from app.models.project import VideoProject
from app.models.scene import Scene
from app.models.storyboard import Storyboard
from app.models.timeline import VideoTimeline, TimelineScene, CaptionAsset
from app.models.render import RenderJob
from app.models.user import User
from app.workers.handlers.video import (
    TimelineGenerationJobHandler,
    VideoRenderJobHandler,
    VideoValidationJobHandler,
)


def test_video_api_timeline_and_render_lifecycle(client, test_user, test_channel):
    """Test full API journey: Create timeline -> Update clip -> Trigger render -> Poll render -> Stream."""
    headers = auth_headers_for(test_user)

    # 1. Create project via API so session is managed consistently
    p_resp = client.post(
        "/api/v1/projects",
        json={
            "channel_id": str(test_channel.id),
            "title": "M09 Video Production Test",
            "format": "LONG_FORM",
        },
        headers=headers,
    )
    assert p_resp.status_code == 201
    project_id = p_resp.json()["id"]

    # 2. Add script and storyboard via existing endpoints or DB
    # We can create a script outline and scenes
    sync_resp = client.post(
        "/api/v1/scripts/sync",
        json={
            "project_id": project_id,
            "title": "Video Production Script",
            "sections": [
                {
                    "section_type": "HOOK",
                    "narration": "Intro to quantum computing.",
                    "visual_directive": "Display quantum processor",
                    "estimated_duration_seconds": 5.0,
                },
                {
                    "section_type": "BODY",
                    "narration": "Qubits and superposition explained.",
                    "visual_directive": "Display 3D qubit visualization",
                    "estimated_duration_seconds": 5.0,
                },
            ],
        },
        headers=headers,
    )
    assert sync_resp.status_code == 201

    # Generate storyboard from script
    sb_resp = client.post(
        "/api/v1/visual/storyboards/generate",
        json={
            "project_id": project_id,
            "aspect_ratio": "16:9",
        },
        headers=headers,
    )
    assert sb_resp.status_code == 200
    storyboard_id = sb_resp.json()["id"]

    # 3. POST /api/v1/video/timelines
    tl_res = client.post(
        "/api/v1/video/timelines",
        json={
            "storyboard_id": storyboard_id,
            "aspect_ratio": "16:9",
            "fps": 30,
            "music_volume": 0.15,
            "ducking_enabled": True,
        },
        headers=headers,
    )
    assert tl_res.status_code == 201
    tl_data = tl_res.json()
    timeline_id = tl_data["id"]
    assert tl_data["aspect_ratio"] == "16:9"
    assert tl_data["width"] == 1920
    assert tl_data["height"] == 1080
    assert float(tl_data["total_duration_seconds"]) > 0
    assert len(tl_data["timeline_scenes"]) >= 2
    assert len(tl_data["captions"]) == 1

    first_scene = tl_data["timeline_scenes"][0]
    first_scene_id = first_scene["id"]
    orig_scene_dur = float(first_scene["duration_seconds"])
    orig_total = float(tl_data["total_duration_seconds"])

    # 4. GET /api/v1/video/timelines/{timeline_id}
    get_tl = client.get(f"/api/v1/video/timelines/{timeline_id}", headers=headers)
    assert get_tl.status_code == 200
    assert get_tl.json()["id"] == timeline_id

    # 5. PATCH /api/v1/video/timelines/{timeline_id}/scenes/{scene_id}
    patch_res = client.patch(
        f"/api/v1/video/timelines/{timeline_id}/scenes/{first_scene_id}",
        json={
            "duration_seconds": 7.5,
            "motion_effect": "pan_left",
        },
        headers=headers,
    )
    assert patch_res.status_code == 200
    p_data = patch_res.json()
    assert float(p_data["duration_seconds"]) == 7.5
    assert p_data["motion_effect"] == "pan_left"

    # Verify updated timeline duration via GET
    get_tl_updated = client.get(f"/api/v1/video/timelines/{timeline_id}", headers=headers)
    expected_total = orig_total - orig_scene_dur + 7.5
    assert abs(float(get_tl_updated.json()["total_duration_seconds"]) - expected_total) < 0.01

    # 6. POST /api/v1/video/renders
    render_res = client.post(
        "/api/v1/video/renders",
        json={
            "timeline_id": timeline_id,
            "mode": "mock",
            "resolution": "1080p",
        },
        headers=headers,
    )
    assert render_res.status_code == 202
    render_data = render_res.json()
    render_id = render_data["id"]
    assert render_data["status"] == "QUEUED"

    # 7. GET /api/v1/video/renders/{render_id}
    poll_res = client.get(f"/api/v1/video/renders/{render_id}", headers=headers)
    assert poll_res.status_code == 200
    assert poll_res.json()["id"] == render_id

    # 8. GET /api/v1/video/projects/{project_id}/renders
    proj_renders = client.get(f"/api/v1/video/projects/{project_id}/renders", headers=headers)
    assert proj_renders.status_code == 200
    assert len(proj_renders.json()) >= 1


@pytest.mark.asyncio
async def test_video_render_and_validation_worker_handlers(db_session: AsyncSession, test_user, test_channel):
    """Test background worker execution of VideoRenderJobHandler and VideoValidationJobHandler."""
    # 1. Create project and timeline directly
    project = VideoProject(
        id=uuid.uuid4(),
        channel_id=test_channel.id,
        title="Worker Test Project",
        format="LONG_FORM",
        state="IDEA",
    )
    db_session.add(project)
    await db_session.commit()

    timeline = VideoTimeline(
        id=uuid.uuid4(),
        project_id=project.id,
        aspect_ratio="16:9",
        fps=30,
        width=1920,
        height=1080,
        total_duration_seconds=Decimal("6.00"),
        status="READY",
    )
    db_session.add(timeline)
    await db_session.flush()

    s1 = TimelineScene(
        id=uuid.uuid4(),
        timeline_id=timeline.id,
        sequence_number=1,
        start_time_seconds=Decimal("0.00"),
        end_time_seconds=Decimal("6.00"),
        duration_seconds=Decimal("6.00"),
        motion_effect="zoom_in",
        transition_type="cut",
    )
    db_session.add(s1)

    render_job = RenderJob(
        id=uuid.uuid4(),
        project_id=project.id,
        timeline_id=timeline.id,
        resolution="1080p",
        video_width=1920,
        video_height=1080,
        fps=30,
        aspect_ratio="16:9",
        renderer_mode="mock",
        current_stage="QUEUED",
        progress_percentage=0,
        status="QUEUED",
        quality_status="PENDING",
    )
    db_session.add(render_job)
    await db_session.commit()

    # 2. Execute VideoRenderJobHandler
    handler = VideoRenderJobHandler(session_factory=TestingSessionLocal)

    progress_events = []
    async def dummy_progress(pct: int, stage: str = None):
        progress_events.append((pct, stage))

    async def dummy_cancellation() -> bool:
        return False

    job = AutomationJob(
        id=uuid.uuid4(),
        channel_id=test_channel.id,
        job_type="VIDEO_RENDER",
        payload={
            "render_job_id": str(render_job.id),
            "timeline_id": str(timeline.id),
            "mode": "mock",
        },
        idempotency_key=f"test_render_{render_job.id}",
    )

    await handler.validate(job.payload)
    result = await handler.execute(job, dummy_progress, dummy_cancellation)

    assert result["status"] == "COMPLETED"
    assert result["output_path"] is not None
    assert os.path.exists(result["output_path"])
    assert len(progress_events) > 0

    # 3. Execute VideoValidationJobHandler
    val_handler = VideoValidationJobHandler(session_factory=TestingSessionLocal)
    val_job = AutomationJob(
        id=uuid.uuid4(),
        channel_id=test_channel.id,
        job_type="VIDEO_VALIDATION",
        payload={"render_job_id": str(render_job.id)},
        idempotency_key=f"test_val_{render_job.id}",
    )
    await val_handler.validate(val_job.payload)
    val_res = await val_handler.execute(val_job, dummy_progress, dummy_cancellation)

    assert val_res["quality_status"] in ["PASSED", "WARNING"]
    assert val_res["score"] >= 80.0

    # Clean up output file
    if os.path.exists(result["output_path"]):
        os.remove(result["output_path"])
