"""End-to-end integration tests for QA API endpoints and background worker handler."""

import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import auth_headers_for, TestingSessionLocal
from app.models.channel import Channel
from app.models.job import AutomationJob
from app.models.project import VideoProject
from app.models.qa import QARun, QAFinding
from app.workers.handlers.qa import QAPackageInspectionJobHandler


def test_qa_api_lifecycle(client, test_user, test_channel):
    """Test the complete API surface of QA evaluation, readiness checks, and findings resolution."""
    headers = auth_headers_for(test_user)

    # 1. Create a project
    p_resp = client.post(
        "/api/v1/projects",
        json={
            "channel_id": str(test_channel.id),
            "title": "M11 QA Veto Gate Pipeline Verification",
            "format": "LONG_FORM",
        },
        headers=headers,
    )
    assert p_resp.status_code == 201
    project_id = p_resp.json()["id"]

    # 2. Trigger synchronous QA run
    trigger_resp = client.post(
        "/api/v1/qa/runs",
        json={
            "project_id": project_id,
            "run_async": False,
        },
        headers=headers,
    )
    assert trigger_resp.status_code == 201
    qa_data = trigger_resp.json()
    run_id = qa_data["id"]
    assert qa_data["status"] == "COMPLETED"
    assert qa_data["veto_decision"] == "BLOCKED"  # Missing components on blank project
    assert qa_data["can_publish"] is False
    assert len(qa_data["findings"]) > 0

    # 3. Retrieve QA run details
    get_resp = client.get(f"/api/v1/qa/runs/{run_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == run_id
    assert len(get_resp.json()["checks"]) > 0
    assert len(get_resp.json()["category_scores"]) > 0

    # 4. Check readiness endpoint
    ready_resp = client.get(f"/api/v1/qa/runs/{run_id}/readiness", headers=headers)
    assert ready_resp.status_code == 200
    assert ready_resp.json()["can_publish"] is False
    assert ready_resp.json()["veto_decision"] == "BLOCKED"

    # 5. List historical runs for project
    list_resp = client.get(f"/api/v1/qa/runs/project/{project_id}", headers=headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    # 6. Get finding correction guide
    first_finding = qa_data["findings"][0]
    finding_id = first_finding["id"]
    guide_resp = client.get(f"/api/v1/qa/findings/{finding_id}/guide", headers=headers)
    assert guide_resp.status_code == 200
    assert len(guide_resp.json()["actionable_steps"]) > 0

    # 7. Resolve finding
    res_resp = client.post(
        f"/api/v1/qa/findings/{finding_id}/resolve",
        json={"resolution_notes": "Render job and mock artifacts configured."},
        headers=headers,
    )
    assert res_resp.status_code == 200
    assert res_resp.json()["status"] == "RESOLVED"
    assert res_resp.json()["resolution_notes"] == "Render job and mock artifacts configured."


@pytest.mark.asyncio
async def test_qa_async_queue_and_worker_handler(client, test_user, test_channel):
    """Test enqueuing QA job to worker queue and executing QAPackageInspectionJobHandler."""
    headers = auth_headers_for(test_user)

    # 1. Create project
    p_resp = client.post(
        "/api/v1/projects",
        json={
            "channel_id": str(test_channel.id),
            "title": "M11 Async Worker Test",
            "format": "LONG_FORM",
        },
        headers=headers,
    )
    assert p_resp.status_code == 201
    project_id = p_resp.json()["id"]

    # 2. Trigger asynchronous QA run
    async_trigger = client.post(
        "/api/v1/qa/runs",
        json={
            "project_id": project_id,
            "run_async": True,
        },
        headers=headers,
    )
    assert async_trigger.status_code == 201
    qa_run_id = async_trigger.json()["id"]
    assert async_trigger.json()["status"] == "QUEUED"

    # 3. Execute Worker Handler directly
    handler = QAPackageInspectionJobHandler(session_factory=TestingSessionLocal)
    await handler.validate({"run_id": qa_run_id})

    progress_log = []

    async def mock_progress(pct, stage):
        progress_log.append((pct, stage))

    async def mock_is_cancelled():
        return False

    mock_job = AutomationJob(
        id=uuid.uuid4(),
        channel_id=test_channel.id,
        job_type="QA_PACKAGE_INSPECTION",
        payload={"run_id": qa_run_id, "project_id": project_id},
    )

    result = await handler.execute(
        job=mock_job,
        update_progress=mock_progress,
        is_cancelled=mock_is_cancelled,
    )

    assert result["run_id"] == qa_run_id
    assert "veto_decision" in result
    assert "overall_score" in result
    assert any(stage == "QA_AUDIT_COMPLETED" for _, stage in progress_log)
