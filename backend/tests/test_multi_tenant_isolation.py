"""Test multi-tenant isolation, cross-tenant boundary protections, and role boundaries."""

import pytest
from tests.conftest import auth_headers_for


@pytest.mark.asyncio
async def test_tenant_cannot_read_other_users_channel(client, test_channel, other_user):
    """User B attempting to read User A's channel receives 404 (preventing channel enumeration)."""
    headers = auth_headers_for(other_user)
    response = client.get(f"/api/v1/channels/{test_channel.id}", headers=headers)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_tenant_cannot_update_other_users_channel_settings(client, test_channel, other_user):
    """User B attempting to modify User A's channel settings receives 404."""
    headers = auth_headers_for(other_user)
    payload = {"auto_publish_enabled": True}
    response = client.patch(
        f"/api/v1/channels/{test_channel.id}/settings",
        headers=headers,
        json=payload,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_tenant_cannot_list_projects_of_other_channel(client, test_channel, other_user):
    """User B attempting to list projects of User A's channel receives 404."""
    headers = auth_headers_for(other_user)
    response = client.get(f"/api/v1/projects?channel_id={test_channel.id}", headers=headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_tenant_cannot_create_project_in_other_channel(client, test_channel, other_user):
    """User B attempting to create a project in User A's channel receives 404."""
    headers = auth_headers_for(other_user)
    payload = {
        "channel_id": str(test_channel.id),
        "title": "Malicious Injected Project",
        "format": "SHORTS",
    }
    response = client.post("/api/v1/projects", headers=headers, json=payload)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_super_admin_can_access_any_channel(client, test_channel, admin_user):
    """SUPER_ADMIN role bypasses tenant boundary for system management."""
    headers = auth_headers_for(admin_user)
    response = client.get(f"/api/v1/channels/{test_channel.id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == str(test_channel.id)
