"""Test Job Queue REST API endpoints, idempotency, budget gates, and worker execution."""

import uuid
import pytest
from tests.conftest import auth_headers_for
from app.workers.runner import WorkerDaemon


@pytest.mark.asyncio
async def test_job_submission_requires_auth(client):
    """POST /api/v1/jobs without token returns 401."""
    res = client.post("/api/v1/jobs", json={"channel_id": str(uuid.uuid4()), "job_type": "TEST_DEMO"})
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_job_submission_unregistered_job_type_rejected(client, test_user, test_channel):
    """POST /api/v1/jobs with invalid job_type returns 400."""
    headers = auth_headers_for(test_user)
    payload = {
        "channel_id": str(test_channel.id),
        "job_type": "UNREGISTERED_DANGEROUS_TYPE",
        "payload": {},
    }
    res = client.post("/api/v1/jobs", headers=headers, json=payload)
    assert res.status_code == 400
    assert "Invalid or unregistered job type" in res.json()["detail"]


@pytest.mark.asyncio
async def test_job_submission_cross_tenant_rejected(client, other_user, test_channel):
    """User B attempting to submit a job to User A's channel receives 404."""
    headers = auth_headers_for(other_user)
    payload = {
        "channel_id": str(test_channel.id),
        "job_type": "TEST_DEMO",
        "payload": {},
    }
    res = client.post("/api/v1/jobs", headers=headers, json=payload)
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_job_idempotency_duplicate_protection(client, test_user, test_channel):
    """Submitting with identical idempotency_key returns original job without duplicate work."""
    headers = auth_headers_for(test_user)
    key = f"idem_{uuid.uuid4().hex}"
    payload = {
        "channel_id": str(test_channel.id),
        "job_type": "TEST_DEMO",
        "payload": {"unique_id": 42},
        "idempotency_key": key,
    }

    # First submission
    res1 = client.post("/api/v1/jobs", headers=headers, json=payload)
    assert res1.status_code == 201
    job1 = res1.json()

    # Second submission with same key
    res2 = client.post("/api/v1/jobs", headers=headers, json=payload)
    assert res2.status_code in [200, 201]
    job2 = res2.json()

    assert job1["id"] == job2["id"]
    assert job1["idempotency_key"] == job2["idempotency_key"]


@pytest.mark.asyncio
async def test_budget_guardrail_rejection(client, test_user, test_channel):
    """Job requiring paid API quota is rejected when channel budget is $0.00."""
    headers = auth_headers_for(test_user)
    payload = {
        "channel_id": str(test_channel.id),
        "job_type": "TEST_DEMO",
        "payload": {"requires_paid_quota": True},
    }
    res = client.post("/api/v1/jobs", headers=headers, json=payload)
    assert res.status_code == 402
    assert "budget cap is set to $0.00" in res.json()["detail"]


@pytest.mark.asyncio
async def test_e2e_worker_execution_and_progress(client, test_user, test_channel):
    """Submit demo job via API, process with WorkerDaemon, verify progress and COMPLETED status."""
    headers = auth_headers_for(test_user)
    payload = {
        "channel_id": str(test_channel.id),
        "job_type": "TEST_DEMO",
        "payload": {"step_delay_seconds": 0.01},
    }

    # 1. Enqueue via API
    create_res = client.post("/api/v1/jobs", headers=headers, json=payload)
    assert create_res.status_code == 201
    job_id = create_res.json()["id"]

    # 2. Worker executes job
    from tests.conftest import TestingSessionLocal
    worker = WorkerDaemon(worker_id="test_runner_daemon", session_factory=TestingSessionLocal)
    processed = await worker.process_one_job()
    assert processed is True

    # 3. Verify job details via API
    detail_res = client.get(f"/api/v1/jobs/{job_id}", headers=headers)
    assert detail_res.status_code == 200
    job_data = detail_res.json()
    assert job_data["status"] == "COMPLETED"
    assert job_data["progress_percentage"] == 100
    assert job_data["current_stage"] == "COMPLETED"
    assert job_data["completed_at"] is not None

    # 4. Verify progress endpoint
    prog_res = client.get(f"/api/v1/jobs/{job_id}/progress", headers=headers)
    assert prog_res.status_code == 200
    assert prog_res.json()["progress_percentage"] == 100
