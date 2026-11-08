"""Test authentication endpoints, RBAC permissions, and auto-provisioning."""

import uuid
import pytest
from tests.conftest import auth_headers_for


def test_auth_me_requires_bearer_token(client):
    """GET /api/v1/auth/me without token returns 401 Unauthorized."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert "credentials were not provided" in response.json()["detail"]


@pytest.mark.asyncio
async def test_auth_me_with_valid_token(client, test_user):
    """GET /api/v1/auth/me with valid Bearer token returns UserRead profile."""
    headers = auth_headers_for(test_user)
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user.email
    assert data["role"] == test_user.role
    assert data["supabase_user_id"] == test_user.supabase_user_id


def test_auth_register_and_login_flow(client):
    """Register new account, receive token, and log in."""
    email = f"newuser_{uuid.uuid4().hex[:6]}@example.com"
    password = "SuperSecurePassword123!"

    # 1. Register
    reg_res = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "New Registered Creator"},
    )
    assert reg_res.status_code == 200
    reg_data = reg_res.json()
    assert "access_token" in reg_data
    assert reg_data["user"]["email"] == email

    # 2. Login
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert "access_token" in login_data
    assert login_data["user"]["email"] == email


@pytest.mark.asyncio
async def test_users_me_update_profile(client, test_user):
    """PATCH /api/v1/users/me allows updating full name."""
    headers = auth_headers_for(test_user)
    res = client.patch(
        "/api/v1/users/me",
        headers=headers,
        json={"full_name": "Updated Name"},
    )
    assert res.status_code == 200
    assert res.json()["full_name"] == "Updated Name"


@pytest.mark.asyncio
async def test_rbac_standard_user_cannot_escalate_role(client, test_user):
    """CREATOR attempting to escalate role to SUPER_ADMIN receives 403 Forbidden."""
    headers = auth_headers_for(test_user)
    res = client.patch(
        "/api/v1/users/me",
        headers=headers,
        json={"role": "SUPER_ADMIN"},
    )
    assert res.status_code == 403
    assert "Only super administrators" in res.json()["detail"]
