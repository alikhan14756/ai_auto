"""YouTube OAuth 2.0 Service with CSRF State HMAC and AES-256 Token Encryption."""

import hmac
import hashlib
import time
import uuid
import urllib.parse
from typing import Tuple, Optional, Dict, Any
import httpx

from app.core.config import settings
from app.core.logging import logger
from app.core.security import encrypt_token, decrypt_token
from app.services.youtube.constants import (
    YOUTUBE_SCOPES,
    GOOGLE_AUTH_URL,
    GOOGLE_TOKEN_URL,
    GOOGLE_REVOKE_URL,
    YOUTUBE_CHANNELS_URL,
)
from app.services.youtube.mock_client import mock_youtube_client


class YouTubeOAuthService:
    """Manages Google OAuth 2.0 flow for YouTube channel connectivity."""

    STATE_EXPIRY_SECONDS = 600  # 10 minutes

    @classmethod
    def _get_signing_key(cls) -> bytes:
        return settings.APP_MASTER_ENCRYPTION_KEY.encode("utf-8")

    @classmethod
    def generate_authorization_url(
        cls,
        user_id: uuid.UUID,
        channel_id: Optional[uuid.UUID] = None,
        redirect_uri: Optional[str] = None,
    ) -> Tuple[str, str]:
        """Generate Google OAuth authorization URL with signed CSRF state token."""
        ts = int(time.time())
        nonce = uuid.uuid4().hex[:16]
        channel_str = str(channel_id) if channel_id else "none"
        payload = f"{user_id}:{channel_str}:{nonce}:{ts}"

        sig = hmac.new(cls._get_signing_key(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
        state = f"{payload}:{sig}"

        redirect = redirect_uri or settings.YOUTUBE_REDIRECT_URI
        client_id = settings.YOUTUBE_CLIENT_ID or "mock_google_client_id.apps.googleusercontent.com"

        params = {
            "client_id": client_id,
            "redirect_uri": redirect,
            "response_type": "code",
            "scope": " ".join(YOUTUBE_SCOPES),
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "true",
            "state": state,
        }
        auth_url = f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"
        return auth_url, state

    @classmethod
    def verify_state(cls, state: str) -> Tuple[uuid.UUID, Optional[uuid.UUID]]:
        """Verify HMAC signature and timestamp freshness of OAuth state."""
        parts = state.split(":")
        if len(parts) != 5:
            raise ValueError("Malformed OAuth state parameter")

        user_id_str, channel_str, nonce, ts_str, signature = parts
        payload = f"{user_id_str}:{channel_str}:{nonce}:{ts_str}"
        expected_sig = hmac.new(cls._get_signing_key(), payload.encode("utf-8"), hashlib.sha256).hexdigest()

        if not hmac.compare_digest(signature, expected_sig):
            raise ValueError("Invalid OAuth state signature (potential CSRF attempt)")

        ts = int(ts_str)
        if time.time() - ts > cls.STATE_EXPIRY_SECONDS:
            raise ValueError("OAuth state token has expired")

        user_id = uuid.UUID(user_id_str)
        channel_id = uuid.UUID(channel_str) if channel_str != "none" else None
        return user_id, channel_id

    @classmethod
    async def exchange_code(
        cls,
        code: str,
        redirect_uri: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Exchange authorization code for access and refresh tokens."""
        redirect = redirect_uri or settings.YOUTUBE_REDIRECT_URI

        # Use mock client if enabled or credentials not configured
        if settings.YOUTUBE_USE_MOCK or not settings.YOUTUBE_CLIENT_ID or not settings.YOUTUBE_CLIENT_SECRET:
            logger.info("[YouTubeOAuth] Using MockYouTubeClient for code exchange")
            return await mock_youtube_client.exchange_code(code)

        payload = {
            "code": code,
            "client_id": settings.YOUTUBE_CLIENT_ID,
            "client_secret": settings.YOUTUBE_CLIENT_SECRET,
            "redirect_uri": redirect,
            "grant_type": "authorization_code",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(GOOGLE_TOKEN_URL, data=payload)
            if resp.status_code != 200:
                logger.error(f"[YouTubeOAuth] Code exchange failed: HTTP {resp.status_code} - {resp.text}")
                raise ValueError(f"Failed to exchange authorization code: {resp.text}")
            return resp.json()

    @classmethod
    async def refresh_access_token(cls, encrypted_refresh_token: str) -> Tuple[str, int]:
        """Decrypt refresh token and acquire a fresh access token.

        Returns:
            Tuple of (access_token, expires_in_seconds)
        """
        raw_refresh_token = decrypt_token(encrypted_refresh_token)

        if settings.YOUTUBE_USE_MOCK or not settings.YOUTUBE_CLIENT_ID or not settings.YOUTUBE_CLIENT_SECRET:
            res = await mock_youtube_client.refresh_access_token(raw_refresh_token)
            return res["access_token"], res.get("expires_in", 3600)

        payload = {
            "client_id": settings.YOUTUBE_CLIENT_ID,
            "client_secret": settings.YOUTUBE_CLIENT_SECRET,
            "refresh_token": raw_refresh_token,
            "grant_type": "refresh_token",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(GOOGLE_TOKEN_URL, data=payload)
            if resp.status_code != 200:
                logger.error(f"[YouTubeOAuth] Token refresh failed: HTTP {resp.status_code} - {resp.text}")
                raise ValueError(f"Failed to refresh access token: {resp.text}")
            data = resp.json()
            return data["access_token"], data.get("expires_in", 3600)

    @classmethod
    async def fetch_channel_profile(cls, access_token: str) -> Dict[str, Any]:
        """Fetch YouTube channel metadata using access token."""
        if settings.YOUTUBE_USE_MOCK or not settings.YOUTUBE_CLIENT_ID:
            return await mock_youtube_client.fetch_channel_profile(access_token)

        headers = {"Authorization": f"Bearer {access_token}"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(YOUTUBE_CHANNELS_URL, headers=headers)
            if resp.status_code != 200:
                raise ValueError(f"Failed to fetch YouTube channel profile: {resp.text}")
            data = resp.json()
            items = data.get("items", [])
            if not items:
                raise ValueError("No YouTube channel found for authenticated Google account")

            channel_item = items[0]
            snippet = channel_item.get("snippet", {})
            statistics = channel_item.get("statistics", {})
            thumbnails = snippet.get("thumbnails", {})
            thumb_url = (
                thumbnails.get("high", {}).get("url")
                or thumbnails.get("medium", {}).get("url")
                or thumbnails.get("default", {}).get("url")
            )

            return {
                "youtube_channel_id": channel_item["id"],
                "title": snippet.get("title", "Untitled Channel"),
                "description": snippet.get("description", ""),
                "custom_url": snippet.get("customUrl"),
                "thumbnail_url": thumb_url,
                "subscriber_count": int(statistics.get("subscriberCount", 0)),
            }

    @classmethod
    async def revoke_token(cls, encrypted_refresh_token: str) -> bool:
        """Revoke refresh token on Google servers."""
        try:
            raw_token = decrypt_token(encrypted_refresh_token)
        except Exception:
            return True

        if settings.YOUTUBE_USE_MOCK or not settings.YOUTUBE_CLIENT_ID:
            return await mock_youtube_client.revoke_token(raw_token)

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(GOOGLE_REVOKE_URL, params={"token": raw_token})
            return resp.status_code == 200
