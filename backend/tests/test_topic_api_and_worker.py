"""Comprehensive integration tests for Topics and Providers REST API and Worker Daemon."""

import pytest
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import auth_headers_for, TestingSessionLocal
from app.models.channel import Channel, ChannelSettings
from app.models.job import AutomationJob
from app.models.topic import Topic
from app.models.user import User
from app.providers.ai.mock import MockAIProvider
from app.providers.ai.factory import set_active_provider
from app.workers.handlers.topic_research import TopicResearchJobHandler


@pytest.fixture(autouse=True)
def ensure_mock_provider():
    set_active_provider(MockAIProvider())


def test_topic_api_full_workflow(client, test_user, test_channel, db_session):
    headers = auth_headers_for(test_user)

    # 1. Trigger synchronous topic research
    sync_resp = client.post(
        "/api/v1/topics/sync",
        headers=headers,
        json={"channel_id": str(test_channel.id), "count": 2},
    )
    assert sync_resp.status_code == 201, sync_resp.text
    created_topics = sync_resp.json()
    assert len(created_topics) >= 1
    topic_id = created_topics[0]["id"]
    assert created_topics[0]["status"] == "DISCOVERED"
    assert len(created_topics[0]["research_sources"]) >= 1

    # 2. List topics for channel
    list_resp = client.get(
        f"/api/v1/topics?channel_id={test_channel.id}&status=DISCOVERED",
        headers=headers,
    )
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["total"] >= 1
    assert any(t["id"] == topic_id for t in list_data["items"])

    # 3. Get specific topic detail
    detail_resp = client.get(
        f"/api/v1/topics/{topic_id}",
        headers=headers,
    )
    assert detail_resp.status_code == 200
    assert detail_resp.json()["id"] == topic_id

    # 4. Approve topic (SELECTED)
    approve_resp = client.post(
        f"/api/v1/topics/{topic_id}/approve",
        headers=headers,
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "SELECTED"

    # 5. Reject / archive topic (ARCHIVED)
    reject_resp = client.post(
        f"/api/v1/topics/{topic_id}/reject",
        headers=headers,
    )
    assert reject_resp.status_code == 200
    assert reject_resp.json()["status"] == "ARCHIVED"

    # 6. Enqueue background research job
    async_resp = client.post(
        "/api/v1/topics/research",
        headers=headers,
        json={"channel_id": str(test_channel.id), "count": 3},
    )
    assert async_resp.status_code == 202
    job_data = async_resp.json()
    assert job_data["job_type"] == "DISCOVER_TOPICS"
    assert job_data["status"] == "QUEUED"


def test_providers_api_endpoints(client, test_user, test_channel):
    headers = auth_headers_for(test_user)

    # GET /api/v1/providers/status
    status_resp = client.get("/api/v1/providers/status", headers=headers)
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert "active_provider" in status_data
    assert "default_model" in status_data
    assert "free_tier_rpm_limit" in status_data

    # GET /api/v1/providers/health
    health_resp = client.get("/api/v1/providers/health", headers=headers)
    assert health_resp.status_code == 200
    health_data = health_resp.json()
    assert health_data["is_healthy"] is True
    assert health_data["latency_ms"] >= 0.0

    # GET /api/v1/providers/usage
    usage_resp = client.get(f"/api/v1/providers/usage?channel_id={test_channel.id}", headers=headers)
    assert usage_resp.status_code == 200
    usage_data = usage_resp.json()
    assert "current_month_spend_usd" in usage_data
    assert "max_monthly_spend_usd" in usage_data

    # POST /api/v1/providers/test
    test_resp = client.post(
        "/api/v1/providers/test",
        headers=headers,
        json={"prompt": "Explain database indexing"},
    )
    assert test_resp.status_code == 200
    test_data = test_resp.json()
    assert "text" in test_data
    assert "usage" in test_data


@pytest.mark.asyncio
async def test_topic_api_cross_tenant_isolation(client, other_user, test_channel, db_session: AsyncSession):
    # Channel belongs to test_user. Create a topic in it:
    topic_a = Topic(
        channel_id=test_channel.id,
        title="Owner Private Topic",
        niche_category="Confidential",
        opportunity_score=95.0,
        status="DISCOVERED",
    )
    db_session.add(topic_a)
    await db_session.commit()

    # other_user (attacker) requests test_channel topics
    headers_b = auth_headers_for(other_user)

    # List topics of Channel A
    res_list = client.get(f"/api/v1/topics?channel_id={test_channel.id}", headers=headers_b)
    assert res_list.status_code == 403

    # Access detail of Topic A
    res_detail = client.get(f"/api/v1/topics/{topic_a.id}", headers=headers_b)
    assert res_detail.status_code == 403

    # Attempt to approve Topic A
    res_approve = client.post(f"/api/v1/topics/{topic_a.id}/approve", headers=headers_b)
    assert res_approve.status_code == 403


@pytest.mark.asyncio
async def test_topic_research_job_handler_execution(test_channel):
    """Direct execution of TopicResearchJobHandler with progress updates."""
    handler = TopicResearchJobHandler(session_factory=TestingSessionLocal)

    # Validate payload
    await handler.validate({"channel_id": str(test_channel.id), "count": 2})

    # Track progress calls
    progress_stages = []

    async def mock_progress(pct: int, stage: str = None):
        progress_stages.append((pct, stage))

    async def mock_cancelled():
        return False

    job = AutomationJob(
        channel_id=test_channel.id,
        job_type="DISCOVER_TOPICS",
        payload={"channel_id": str(test_channel.id), "count": 2},
    )

    result = await handler.execute(job, mock_progress, mock_cancelled)
    assert result["topics_discovered_count"] >= 1
    assert "topic_ids" in result
    assert (10, "INITIALIZING_RESEARCH") in progress_stages
    assert (100, "COMPLETED") in progress_stages
