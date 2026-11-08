"""Integration tests for Workflow REST APIs, RBAC, and multi-tenant security isolation."""

import uuid
import pytest
from app.models.user import User
from app.models.channel import Channel
from tests.conftest import auth_headers_for


@pytest.mark.asyncio
async def test_workflow_api_lifecycle(client, test_user, test_channel, db_session):
    """Test full workflow API lifecycle: create -> get -> pause -> resume -> cancel."""
    headers = auth_headers_for(test_user)

    # Configure channel policy to not require topic approval for this lifecycle test
    patch_payload = {
        "require_topic_approval": False,
    }
    client.patch(
        f"/api/v1/automation/policies?channel_id={test_channel.id}",
        json=patch_payload,
        headers=headers,
    )

    # 1. Create workflow execution
    create_payload = {
        "channel_id": str(test_channel.id),
        "template_key": "TEMPLATE_TOPIC_RESEARCH_ONLY",
        "auto_start": True,
    }
    resp = client.post("/api/v1/workflows", json=create_payload, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    wf_id = data["id"]
    assert data["template_key"] == "TEMPLATE_TOPIC_RESEARCH_ONLY"
    assert data["status"] in ("READY", "RUNNING")

    # 2. Get workflow detail
    get_resp = client.get(f"/api/v1/workflows/{wf_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == wf_id
    assert len(get_resp.json()["stages"]) >= 1

    # 3. Pause workflow
    pause_resp = client.post(f"/api/v1/workflows/{wf_id}/pause", headers=headers)
    assert pause_resp.status_code == 200
    assert pause_resp.json()["status"] == "PAUSED"

    # 4. Resume workflow
    resume_resp = client.post(f"/api/v1/workflows/{wf_id}/resume", headers=headers)
    assert resume_resp.status_code == 200
    assert resume_resp.json()["status"] == "RUNNING"

    # 5. Cancel workflow
    cancel_resp = client.post(f"/api/v1/workflows/{wf_id}/cancel", headers=headers)
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "CANCELLED"


@pytest.mark.asyncio
async def test_workflow_tenant_isolation(client, test_user, test_channel, db_session):
    """Verify Tenant B cannot access or mutate Tenant A's workflow executions."""
    headers_user_a = auth_headers_for(test_user)

    # Create workflow for User A
    create_payload = {
        "channel_id": str(test_channel.id),
        "template_key": "TEMPLATE_TOPIC_RESEARCH_ONLY",
    }
    resp_a = client.post("/api/v1/workflows", json=create_payload, headers=headers_user_a)
    assert resp_a.status_code == 201
    wf_id = resp_a.json()["id"]

    # Create User B (different tenant)
    user_b = User(
        supabase_user_id="sub_attacker_99",
        email="attacker@external.io",
        full_name="Attacker User",
        role="CREATOR",
    )
    db_session.add(user_b)
    await db_session.flush()

    channel_b = Channel(
        user_id=user_b.id,
        youtube_channel_id="UC_attacker_channel_01",
        title="Attacker Channel",
        oauth_refresh_token_encrypted="mock_enc",
    )
    db_session.add(channel_b)
    await db_session.flush()

    headers_user_b = auth_headers_for(user_b)

    # 1. User B attempts to read User A's workflow -> 403 Forbidden
    get_resp = client.get(f"/api/v1/workflows/{wf_id}", headers=headers_user_b)
    assert get_resp.status_code == 403
    assert "Unauthorized" in get_resp.json()["detail"]

    # 2. User B attempts to cancel User A's workflow -> 403 Forbidden
    cancel_resp = client.post(f"/api/v1/workflows/{wf_id}/cancel", headers=headers_user_b)
    assert cancel_resp.status_code == 403


@pytest.mark.asyncio
async def test_workflow_templates_api(client, test_user, test_channel, db_session):
    """Verify template listing and duplicating endpoints."""
    headers = auth_headers_for(test_user)

    # 1. List templates
    list_resp = client.get("/api/v1/workflow-templates", headers=headers)
    assert list_resp.status_code == 200
    templates = list_resp.json()
    assert len(templates) >= 8

    keys = [t["template_key"] for t in templates]
    assert "TEMPLATE_LONG_FORM" in keys
    assert "TEMPLATE_SHORTS" in keys

    # 2. Duplicate standard template
    dup_resp = client.post(
        f"/api/v1/workflow-templates/TEMPLATE_SHORTS/duplicate?channel_id={test_channel.id}",
        headers=headers,
    )
    assert dup_resp.status_code == 200
    dup_data = dup_resp.json()
    assert dup_data["is_system"] is False
    assert "Copy of" in dup_data["name"]
    custom_tpl_id = dup_data["id"]

    # 3. Test BOLA/IDOR protection on custom templates
    user_b = User(
        supabase_user_id="sub_attacker_templates_99",
        email="attacker_tpl@external.io",
        full_name="Attacker User",
        role="CREATOR",
    )
    db_session.add(user_b)
    await db_session.flush()

    channel_b = Channel(
        user_id=user_b.id,
        youtube_channel_id="UC_attacker_channel_tpl",
        title="Attacker Channel TPL",
        oauth_refresh_token_encrypted="mock_enc",
    )
    db_session.add(channel_b)
    await db_session.flush()

    headers_b = auth_headers_for(user_b)

    # User B cannot read User A's custom template by UUID -> 403
    unauth_get = client.get(f"/api/v1/workflow-templates/{custom_tpl_id}", headers=headers_b)
    assert unauth_get.status_code == 403

    # User B cannot duplicate User A's custom template -> 403
    unauth_dup = client.post(
        f"/api/v1/workflow-templates/{custom_tpl_id}/duplicate?channel_id={channel_b.id}",
        headers=headers_b,
    )
    assert unauth_dup.status_code == 403


@pytest.mark.asyncio
async def test_automation_policies_and_permissions_api(client, test_user, test_channel):
    """Verify policy management and permissions introspection endpoints."""
    headers = auth_headers_for(test_user)

    # 1. Get policies
    pol_resp = client.get(f"/api/v1/automation/policies?channel_id={test_channel.id}", headers=headers)
    assert pol_resp.status_code == 200
    policy = pol_resp.json()
    assert policy["automation_level"] == 1  # Assisted default

    # 2. Patch policies (safe update)
    patch_payload = {
        "max_concurrent_workflows": 3,
        "max_monthly_budget_usd": 15.0,
    }
    patch_resp = client.patch(
        f"/api/v1/automation/policies?channel_id={test_channel.id}",
        json=patch_payload,
        headers=headers,
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["max_concurrent_workflows"] == 3
    assert patch_resp.json()["max_monthly_budget_usd"] == 15.0

    # 3. Permissions endpoint
    perm_resp = client.get(f"/api/v1/automation/permissions?channel_id={test_channel.id}", headers=headers)
    assert perm_resp.status_code == 200
    perm = perm_resp.json()
    assert perm["is_qa_veto_gate_mandatory"] is True


@pytest.mark.asyncio
async def test_system_health_and_governor_api(client, test_user, test_channel):
    """Verify system health, resource usage, and budget status endpoints."""
    headers = auth_headers_for(test_user)

    # 1. Production Health
    health_resp = client.get(f"/api/v1/system/production-health?channel_id={test_channel.id}", headers=headers)
    assert health_resp.status_code == 200
    health = health_resp.json()
    assert "status" in health
    assert "active_workflows" in health

    # 2. Resource Usage
    usage_resp = client.get(f"/api/v1/system/resource-usage?channel_id={test_channel.id}", headers=headers)
    assert usage_resp.status_code == 200
    usage = usage_resp.json()
    assert "current_month_spend_usd" in usage

    # 3. Budget Status
    budget_resp = client.get(f"/api/v1/system/budget-status?channel_id={test_channel.id}", headers=headers)
    assert budget_resp.status_code == 200
    budget = budget_resp.json()
    assert "is_zero_dollar_budget" in budget
