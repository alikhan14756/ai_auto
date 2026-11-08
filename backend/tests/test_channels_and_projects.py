"""Test channels and projects API endpoints."""

import uuid
import pytest
from tests.conftest import auth_headers_for


@pytest.mark.asyncio
async def test_list_channels(client, test_user, test_channel):
    """List channels for authenticated user returns their channel."""
    headers = auth_headers_for(test_user)
    res = client.get("/api/v1/channels", headers=headers)
    assert res.status_code == 200
    channels = res.json()
    assert len(channels) >= 1
    assert channels[0]["id"] == str(test_channel.id)
    assert channels[0]["title"] == test_channel.title
    assert channels[0]["settings"] is not None


@pytest.mark.asyncio
async def test_create_channel(client, test_user):
    """POST /api/v1/channels creates a channel with encrypted token and default settings."""
    headers = auth_headers_for(test_user)
    payload = {
        "youtube_channel_id": f"UC_{uuid.uuid4().hex[:16]}",
        "title": "Newly Added Tech Channel",
        "description": "Tech reviews and tutorials",
        "custom_url": "@newlytech",
        "oauth_refresh_token": "refresh_token_to_encrypt",
    }
    res = client.post("/api/v1/channels", headers=headers, json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["title"] == payload["title"]
    assert data["settings"]["default_privacy"] == "unlisted"
    assert data["settings"]["default_category_id"] == "28"


@pytest.mark.asyncio
async def test_update_channel_settings(client, test_user, test_channel):
    """PATCH /api/v1/channels/{id}/settings updates cadence and spend cap."""
    headers = auth_headers_for(test_user)
    update_payload = {
        "weekly_cadence_long": 4,
        "max_monthly_spend_usd": 150.00,
        "auto_publish_enabled": True,
    }
    res = client.patch(
        f"/api/v1/channels/{test_channel.id}/settings",
        headers=headers,
        json=update_payload,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["weekly_cadence_long"] == 4
    assert data["max_monthly_spend_usd"] == 150.00
    assert data["auto_publish_enabled"] is True


@pytest.mark.asyncio
async def test_create_and_list_projects(client, test_user, test_channel):
    """Create a video project and list it for the channel."""
    headers = auth_headers_for(test_user)

    # 1. Create project
    create_payload = {
        "channel_id": str(test_channel.id),
        "title": "Ultimate Guide to AI Agents",
        "format": "LONG_FORM",
        "target_duration_seconds": 600,
    }
    create_res = client.post("/api/v1/projects", headers=headers, json=create_payload)
    assert create_res.status_code == 201
    project_data = create_res.json()
    assert project_data["title"] == create_payload["title"]
    assert project_data["state"] == "IDEA"

    # 2. List projects for channel
    list_res = client.get(f"/api/v1/projects?channel_id={test_channel.id}", headers=headers)
    assert list_res.status_code == 200
    projects = list_res.json()
    assert len(projects) >= 1
    assert any(p["id"] == project_data["id"] for p in projects)
