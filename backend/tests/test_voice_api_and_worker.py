"""Comprehensive integration tests for Voice REST API and Worker Job Handlers."""

import pytest
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import auth_headers_for, TestingSessionLocal
from app.models.channel import Channel
from app.models.job import AutomationJob
from app.models.project import VideoProject
from app.models.scene import Scene
from app.models.script import Script
from app.models.user import User
from app.models.voice import NarrationTrack, Voiceover, VoiceProfile
from app.providers.voice.mock import MockVoiceProvider
from app.providers.voice.factory import set_active_voice_provider
from app.workers.handlers.narration import (
    NarrationGenerationJobHandler,
    VoicePreviewJobHandler,
    NarrationSectionRegenerateJobHandler,
)


@pytest.fixture(autouse=True)
def ensure_mock_provider():
    set_active_voice_provider(MockVoiceProvider())


def test_voice_api_full_workflow(client, test_user, test_channel, db_session):
    headers = auth_headers_for(test_user)

    # 1. List Providers
    prov_resp = client.get("/api/v1/voice/providers", headers=headers)
    assert prov_resp.status_code == 200
    assert prov_resp.json()["active_provider"] == "mock"

    # 2. List Voices
    voices_resp = client.get("/api/v1/voice/voices?language_code=en-US", headers=headers)
    assert voices_resp.status_code == 200
    voices = voices_resp.json()
    assert len(voices) >= 2
    voice_id = voices[0]["voice_id"]

    # 3. Create Voice Profile
    create_prof = client.post(
        "/api/v1/voice/profiles",
        headers=headers,
        json={
            "channel_id": str(test_channel.id),
            "display_name": "Senior Architecture Narrator",
            "provider": "mock",
            "provider_voice_id": voice_id,
            "language_code": "en-US",
            "speed_ratio": 1.05,
            "is_default": True,
        },
    )
    assert create_prof.status_code == 201
    profile_id = create_prof.json()["id"]

    # 4. List Profiles
    list_prof = client.get(f"/api/v1/voice/profiles?channel_id={test_channel.id}", headers=headers)
    assert list_prof.status_code == 200
    assert len(list_prof.json()) >= 1

    # 5. Preview Voice
    prev_resp = client.post(
        "/api/v1/voice/preview",
        headers=headers,
        json={"voice_id": voice_id, "sample_text": "Auditioning neural voice for Creator Studio AI."},
    )
    assert prev_resp.status_code == 200
    assert prev_resp.json()["duration_seconds"] > 0
    assert prev_resp.json()["audio_base64"] is not None

    # 6. Setup Project & Script
    proj_resp = client.post(
        "/api/v1/projects",
        headers=headers,
        json={"channel_id": str(test_channel.id), "title": "Voice Pipeline Project"},
    )
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    # Generate script
    script_resp = client.post(
        "/api/v1/scripts/sync",
        headers=headers,
        json={"project_id": project_id},
    )
    assert script_resp.status_code == 201

    # 7. Generate Narration Synchronously
    gen_resp = client.post(
        "/api/v1/voice/generate-sync",
        headers=headers,
        json={"project_id": project_id, "voice_profile_id": profile_id},
    )
    assert gen_resp.status_code == 201, gen_resp.text
    track_data = gen_resp.json()
    track_id = track_data["id"]
    assert track_data["duration_seconds"] > 0
    assert len(track_data["voiceovers"]) >= 1

    chunk_id = track_data["voiceovers"][0]["id"]
    scene_id = track_data["voiceovers"][0]["scene_id"]

    # 8. List Tracks
    tracks_list = client.get(f"/api/v1/voice/tracks?project_id={project_id}", headers=headers)
    assert tracks_list.status_code == 200
    assert len(tracks_list.json()) >= 1

    # 9. Get Track Detail
    track_detail = client.get(f"/api/v1/voice/tracks/{track_id}", headers=headers)
    assert track_detail.status_code == 200
    assert track_detail.json()["id"] == track_id

    # 10. Stream Master Audio
    audio_stream = client.get(f"/api/v1/voice/tracks/{track_id}/audio", headers=headers)
    assert audio_stream.status_code == 200
    assert audio_stream.headers["content-type"] == "audio/wav"
    assert len(audio_stream.content) > 100

    # 11. Stream Chunk Audio
    chunk_stream = client.get(f"/api/v1/voice/chunks/{chunk_id}/audio", headers=headers)
    assert chunk_stream.status_code == 200
    assert chunk_stream.headers["content-type"] == "audio/wav"

    # 12. Regenerate Section Audio
    regen_resp = client.post(
        f"/api/v1/voice/tracks/{track_id}/regenerate-section",
        headers=headers,
        json={"scene_id": scene_id, "speed_ratio": 1.1},
    )
    assert regen_resp.status_code == 200, regen_resp.text
    assert regen_resp.json()["id"] == track_id

    # 13. Approve Track
    approve_resp = client.post(f"/api/v1/voice/tracks/{track_id}/approve", headers=headers)
    assert approve_resp.status_code == 200
    assert approve_resp.json()["is_approved"] is True

    # 14. Enqueue Background Narration Job
    async_job_resp = client.post(
        "/api/v1/voice/generate",
        headers=headers,
        json={"project_id": project_id, "voice_profile_id": profile_id},
    )
    assert async_job_resp.status_code == 202
    assert async_job_resp.json()["job_type"] == "NARRATION_GENERATION"


def test_voice_cross_tenant_isolation(client, other_user, test_channel, db_session):
    headers_owner = auth_headers_for(test_channel.user)
    headers_attacker = auth_headers_for(other_user)

    # Owner creates project, script, and narration
    proj_resp = client.post(
        "/api/v1/projects",
        headers=headers_owner,
        json={"channel_id": str(test_channel.id), "title": "Confidential Audio Project"},
    )
    project_id = proj_resp.json()["id"]

    client.post("/api/v1/scripts/sync", headers=headers_owner, json={"project_id": project_id})
    gen_resp = client.post("/api/v1/voice/generate-sync", headers=headers_owner, json={"project_id": project_id})
    track_id = gen_resp.json()["id"]

    # Attacker attempts to access track detail
    res_get = client.get(f"/api/v1/voice/tracks/{track_id}", headers=headers_attacker)
    assert res_get.status_code == 403

    # Attacker attempts to stream audio
    res_stream = client.get(f"/api/v1/voice/tracks/{track_id}/audio", headers=headers_attacker)
    assert res_stream.status_code == 403

    # Attacker attempts to approve track
    res_approve = client.post(f"/api/v1/voice/tracks/{track_id}/approve", headers=headers_attacker)
    assert res_approve.status_code == 403


@pytest.mark.asyncio
async def test_narration_worker_handlers(test_channel, db_session: AsyncSession):
    # Setup project with scene
    project = VideoProject(channel_id=test_channel.id, title="Worker Audio Project")
    db_session.add(project)
    await db_session.flush()

    script = Script(
        project_id=project.id,
        version=1,
        full_text="Worker narration test.",
        word_count=3,
        estimated_duration_seconds=2,
        is_locked=True,
    )
    db_session.add(script)
    await db_session.flush()

    scene = Scene(project_id=project.id, scene_order=1, narration_text="Worker speech scene.", visual_archetype="INFOGRAPHIC", visual_directive="Test", duration_seconds=3)
    db_session.add(scene)
    await db_session.commit()

    stages = []
    async def mock_progress(pct: int, stage: str = None):
        stages.append(pct)
    async def mock_cancelled():
        return False

    # 1. Preview Handler
    prev_handler = VoicePreviewJobHandler(session_factory=TestingSessionLocal)
    await prev_handler.validate({"voice_id": "mock-tech-male-1"})
    prev_job = AutomationJob(channel_id=test_channel.id, job_type="VOICE_PREVIEW_GENERATION", payload={"voice_id": "mock-tech-male-1"})
    prev_res = await prev_handler.execute(prev_job, mock_progress, mock_cancelled)
    assert prev_res["voice_id"] == "mock-tech-male-1"

    # 2. Narration Generation Handler
    gen_handler = NarrationGenerationJobHandler(session_factory=TestingSessionLocal)
    await gen_handler.validate({"project_id": str(project.id)})
    gen_job = AutomationJob(channel_id=test_channel.id, job_type="NARRATION_GENERATION", payload={"project_id": str(project.id)})
    gen_res = await gen_handler.execute(gen_job, mock_progress, mock_cancelled)
    assert "narration_track_id" in gen_res
    track_id = gen_res["narration_track_id"]
    assert 100 in stages

    # 3. Section Regenerate Handler
    regen_handler = NarrationSectionRegenerateJobHandler(session_factory=TestingSessionLocal)
    await regen_handler.validate({"narration_track_id": track_id, "scene_id": str(scene.id)})
    regen_job = AutomationJob(channel_id=test_channel.id, job_type="NARRATION_SECTION_REGENERATE", payload={"narration_track_id": track_id, "scene_id": str(scene.id)})
    regen_res = await regen_handler.execute(regen_job, mock_progress, mock_cancelled)
    assert regen_res["narration_track_id"] == track_id
