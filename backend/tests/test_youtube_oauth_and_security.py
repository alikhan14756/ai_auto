"""Tests for YouTube OAuth 2.0 flow, CSRF state protection, and token encryption."""

import uuid
import time
import pytest
from app.core.security import encrypt_token, decrypt_token
from app.services.youtube.oauth import YouTubeOAuthService
from app.services.youtube.mock_client import mock_youtube_client
from tests.conftest import auth_headers_for


@pytest.mark.asyncio
async def test_oauth_state_hmac_generation_and_verification():
    """Verify HMAC-SHA256 OAuth state token generation and tamper detection."""
    user_id = uuid.uuid4()
    channel_id = uuid.uuid4()

    auth_url, state = YouTubeOAuthService.generate_authorization_url(user_id, channel_id)
    assert "https://accounts.google.com/o/oauth2/v2/auth" in auth_url
    assert "state=" in auth_url
    import urllib.parse
    assert state in urllib.parse.unquote(auth_url)

    # Verify legitimate state
    v_user_id, v_channel_id = YouTubeOAuthService.verify_state(state)
    assert v_user_id == user_id
    assert v_channel_id == channel_id

    # Tampered state test
    tampered_state = state[:-4] + "abcd"
    with pytest.raises(ValueError, match="Invalid OAuth state signature"):
        YouTubeOAuthService.verify_state(tampered_state)


@pytest.mark.asyncio
async def test_oauth_state_expiration():
    """Verify that expired state tokens are strictly rejected."""
    user_id = uuid.uuid4()
    channel_id = uuid.uuid4()

    # Manually craft an expired state token (>600s in the past)
    old_ts = int(time.time()) - 700
    nonce = "abc123nonce"
    payload = f"{user_id}:{channel_id}:{nonce}:{old_ts}"
    import hmac, hashlib
    sig = hmac.new(YouTubeOAuthService._get_signing_key(), payload.encode(), hashlib.sha256).hexdigest()
    expired_state = f"{payload}:{sig}"

    with pytest.raises(ValueError, match="expired"):
        YouTubeOAuthService.verify_state(expired_state)


@pytest.mark.asyncio
async def test_token_aes_256_gcm_encryption_roundtrip():
    """Verify AES-256-GCM token encryption and non-exposure in ciphertext."""
    plaintext_token = "1//04mock_google_oauth_refresh_token_very_secret_xyz789"
    encrypted = encrypt_token(plaintext_token)

    assert encrypted != plaintext_token
    assert "mock_google" not in encrypted
    assert "secret" not in encrypted

    decrypted = decrypt_token(encrypted)
    assert decrypted == plaintext_token


@pytest.mark.asyncio
async def test_mock_oauth_code_exchange_and_profile():
    """Test full code exchange and channel profile retrieval via mock client."""
    mock_youtube_client.reset()

    token_data = await YouTubeOAuthService.exchange_code("mock_valid_auth_code_123")
    assert "access_token" in token_data
    assert "refresh_token" in token_data
    assert token_data["token_type"] == "Bearer"

    access_token = token_data["access_token"]
    profile = await YouTubeOAuthService.fetch_channel_profile(access_token)
    assert profile["youtube_channel_id"] == "UC_ali_build_test_channel_01"
    assert profile["title"] == "Muhammad Ali AI Studio"
    assert profile["subscriber_count"] > 0


@pytest.mark.asyncio
async def test_oauth_disconnect_endpoint(client, test_user, test_channel):
    """Verify safe channel disconnection and credential revoking."""
    headers = auth_headers_for(test_user)

    resp = client.post(
        f"/api/v1/youtube/disconnect?channel_id={test_channel.id}",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "disconnected"

    # Connection status should now report disconnected
    status_resp = client.get(
        f"/api/v1/youtube/connection?channel_id={test_channel.id}",
        headers=headers,
    )
    assert status_resp.status_code == 200
    assert status_resp.json()["connected"] is False
