"""Comprehensive integration tests for Scripts REST API and Background Worker Daemon."""

import pytest
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import auth_headers_for, TestingSessionLocal
from app.models.channel import Channel, ChannelSettings
from app.models.job import AutomationJob
from app.models.project import VideoProject
from app.models.script import Script
from app.models.topic import Topic, ResearchSource
from app.models.user import User
from app.providers.ai.mock import MockAIProvider
from app.providers.ai.factory import set_active_provider
from app.workers.handlers.script_generation import (
    ScriptGenerationJobHandler,
    ScriptOutlineJobHandler,
    ScriptFactCheckJobHandler,
    ScriptQualityEvaluationJobHandler,
)


@pytest.fixture(autouse=True)
def ensure_mock_provider():
    set_active_provider(MockAIProvider())


def test_script_api_full_workflow(client, test_user, test_channel, db_session):
    headers = auth_headers_for(test_user)

    # 0. Set channel spend cap so test can execute both outline and sync generation
    cap_resp = client.patch(
        f"/api/v1/channels/{test_channel.id}/settings",
        headers=headers,
        json={"max_monthly_spend_usd": 50.00},
    )
    assert cap_resp.status_code == 200

    # 1. Create a project
    proj_resp = client.post(
        "/api/v1/projects",
        headers=headers,
        json={
            "channel_id": str(test_channel.id),
            "title": "PostgreSQL Queues in Depth",
            "format": "LONG_FORM",
            "target_duration_seconds": 480,
        },
    )
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    # 1b. Test outline generation endpoint
    outline_resp = client.post(
        "/api/v1/scripts/outline",
        headers=headers,
        json={"project_id": project_id, "target_duration_seconds": 480},
    )
    assert outline_resp.status_code == 200
    outline_data = outline_resp.json()
    assert outline_data["project_id"] == project_id
    assert len(outline_data["sections"]) >= 1

    # 2. Trigger synchronous script generation
    sync_resp = client.post(
        "/api/v1/scripts/sync",
        headers=headers,
        json={"project_id": project_id, "target_duration_seconds": 480},
    )
    assert sync_resp.status_code == 201, sync_resp.text
    script_data = sync_resp.json()
    script_id = script_data["id"]
    assert script_data["version"] == 1
    assert script_data["word_count"] > 0
    assert script_data["quality_metrics"]["overall_score"] > 0
    assert len(script_data["claims"]) >= 1

    # 3. List scripts for project
    list_resp = client.get(
        f"/api/v1/scripts?project_id={project_id}",
        headers=headers,
    )
    assert list_resp.status_code == 200
    scripts = list_resp.json()
    assert len(scripts) >= 1
    assert scripts[0]["id"] == script_id

    # 4. Get script detail
    detail_resp = client.get(
        f"/api/v1/scripts/{script_id}",
        headers=headers,
    )
    assert detail_resp.status_code == 200
    assert detail_resp.json()["id"] == script_id

    # 5. Regenerate individual section
    regen_resp = client.post(
        f"/api/v1/scripts/{script_id}/regenerate-section",
        headers=headers,
        json={"section_id": "sec_02", "custom_prompt": "Add more technical details on SKIP LOCKED"},
    )
    assert regen_resp.status_code == 200
    assert "[Revised Section sec_02]" in regen_resp.json()["full_text"]

    # 6. Update script text manually
    patch_resp = client.patch(
        f"/api/v1/scripts/{script_id}",
        headers=headers,
        json={"full_text": "Updated manual polish on the full script narration."},
    )
    assert patch_resp.status_code == 200
    assert "Updated manual polish" in patch_resp.json()["full_text"]

    # 7. Approve script (locks script and marks project state)
    approve_resp = client.post(
        f"/api/v1/scripts/{script_id}/approve",
        headers=headers,
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["is_locked"] is True

    # 8. Attempting to edit a locked script must return 400
    fail_edit = client.patch(
        f"/api/v1/scripts/{script_id}",
        headers=headers,
        json={"full_text": "Trying to edit locked script"},
    )
    assert fail_edit.status_code == 400

    # 9. Enqueue background script generation job
    async_resp = client.post(
        "/api/v1/scripts/generate",
        headers=headers,
        json={"project_id": project_id, "target_duration_seconds": 600},
    )
    assert async_resp.status_code == 202
    assert async_resp.json()["job_type"] == "GENERATE_SCRIPT"
    assert async_resp.json()["status"] == "QUEUED"


def test_script_cross_tenant_isolation(client, other_user, test_channel, db_session):
    headers_owner = auth_headers_for(test_channel.user)
    headers_attacker = auth_headers_for(other_user)

    # Owner creates project and script
    proj_resp = client.post(
        "/api/v1/projects",
        headers=headers_owner,
        json={"channel_id": str(test_channel.id), "title": "Confidential Script Project"},
    )
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    script_resp = client.post(
        "/api/v1/scripts/sync",
        headers=headers_owner,
        json={"project_id": project_id},
    )
    assert script_resp.status_code == 201
    script_id = script_resp.json()["id"]

    # Attacker tries to read script
    res_get = client.get(f"/api/v1/scripts/{script_id}", headers=headers_attacker)
    assert res_get.status_code == 403

    # Attacker tries to approve script
    res_approve = client.post(f"/api/v1/scripts/{script_id}/approve", headers=headers_attacker)
    assert res_approve.status_code == 403


@pytest.mark.asyncio
async def test_script_generation_job_handler_execution(test_channel, db_session: AsyncSession):
    project = VideoProject(
        channel_id=test_channel.id,
        title="Worker Script Project",
    )
    db_session.add(project)
    await db_session.commit()

    handler = ScriptGenerationJobHandler(session_factory=TestingSessionLocal)
    await handler.validate({"project_id": str(project.id)})

    progress_stages = []

    async def mock_progress(pct: int, stage: str = None):
        progress_stages.append((pct, stage))

    async def mock_cancelled():
        return False

    job = AutomationJob(
        channel_id=test_channel.id,
        job_type="GENERATE_SCRIPT",
        payload={"project_id": str(project.id)},
    )

    result = await handler.execute(job, mock_progress, mock_cancelled)
    assert "script_id" in result
    assert result["version"] == 1
    assert (10, "INITIALIZING_GENERATION") in progress_stages
    assert (100, "COMPLETED") in progress_stages


@pytest.mark.asyncio
async def test_script_outline_and_factcheck_worker_handlers(test_channel, db_session: AsyncSession):
    project = VideoProject(
        channel_id=test_channel.id,
        title="Worker Outline Project",
    )
    db_session.add(project)
    await db_session.flush()

    # 1. Outline Handler
    outline_handler = ScriptOutlineJobHandler(session_factory=TestingSessionLocal)
    await outline_handler.validate({"project_id": str(project.id)})

    stages = []
    async def mock_progress(pct: int, stage: str = None):
        stages.append(pct)
    async def mock_cancelled():
        return False

    outline_job = AutomationJob(
        channel_id=test_channel.id,
        job_type="SCRIPT_OUTLINE_GENERATION",
        payload={"project_id": str(project.id)},
    )
    outline_res = await outline_handler.execute(outline_job, mock_progress, mock_cancelled)
    assert "sections" in outline_res
    assert len(outline_res["sections"]) >= 1

    # 2. Fact Check & Quality Handlers
    script = Script(
        project_id=project.id,
        version=1,
        full_text="PostgreSQL 9.5 introduced SKIP LOCKED which scales to 5,000 jobs per second.",
        word_count=12,
        estimated_duration_seconds=5,
    )
    db_session.add(script)
    await db_session.commit()

    fc_handler = ScriptFactCheckJobHandler(session_factory=TestingSessionLocal)
    await fc_handler.validate({"script_id": str(script.id)})
    fc_job = AutomationJob(
        channel_id=test_channel.id,
        job_type="SCRIPT_FACT_CHECK",
        payload={"script_id": str(script.id)},
    )
    fc_res = await fc_handler.execute(fc_job, mock_progress, mock_cancelled)
    assert fc_res["script_id"] == str(script.id)

    qe_handler = ScriptQualityEvaluationJobHandler(session_factory=TestingSessionLocal)
    await qe_handler.validate({"script_id": str(script.id)})
    qe_job = AutomationJob(
        channel_id=test_channel.id,
        job_type="SCRIPT_QUALITY_EVALUATION",
        payload={"script_id": str(script.id)},
    )
    qe_res = await qe_handler.execute(qe_job, mock_progress, mock_cancelled)
    assert qe_res["script_id"] == str(script.id)
    assert "overall_score" in qe_res["quality_metrics"]
