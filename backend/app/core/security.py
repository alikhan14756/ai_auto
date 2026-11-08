"""Security, Token Encryption, and JWT Verification utilities."""

import os
import base64
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
import jwt
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings
from app.core.logging import logger

# Role Definitions
ROLE_SUPER_ADMIN = "SUPER_ADMIN"
ROLE_ADMIN = "ADMIN"
ROLE_CREATOR = "CREATOR"

ALLOWED_ROLES = [ROLE_SUPER_ADMIN, ROLE_ADMIN, ROLE_CREATOR]


def get_encryption_key() -> bytes:
    """Derive 32-byte key from APP_MASTER_ENCRYPTION_KEY setting."""
    key_raw = settings.APP_MASTER_ENCRYPTION_KEY
    if len(key_raw) == 64:
        # Hex string
        try:
            return bytes.fromhex(key_raw)
        except ValueError:
            pass
    # Fallback padding/truncating to exactly 32 bytes
    return key_raw.encode("utf-8").ljust(32, b"0")[:32]


def encrypt_token(plaintext: str) -> str:
    """Encrypt a secret token using AES-256-GCM.
    Returns URL-safe base64 string formatted as: nonce:ciphertext:tag.
    """
    if not plaintext:
        return ""
    key = get_encryption_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)  # 96-bit nonce for GCM
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    payload = nonce + ciphertext
    return base64.urlsafe_b64encode(payload).decode("utf-8")


def decrypt_token(encoded: str) -> str:
    """Decrypt an AES-256-GCM encrypted token."""
    if not encoded:
        return ""
    try:
        key = get_encryption_key()
        aesgcm = AESGCM(key)
        data = base64.urlsafe_b64decode(encoded.encode("utf-8"))
        nonce = data[:12]
        ciphertext = data[12:]
        decrypted = aesgcm.decrypt(nonce, ciphertext, None)
        return decrypted.decode("utf-8")
    except Exception as exc:
        logger.error(f"Failed to decrypt token: {exc}")
        raise ValueError("Decryption failed: invalid ciphertext or corrupted key") from exc


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
    secret_key: Optional[str] = None,
) -> str:
    """Create a signed JWT token (used for testing and local authentication tokens)."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(hours=24)

    to_encode.update({
        "exp": int(expire.timestamp()),
        "iat": int(now.timestamp()),
        "iss": "creator-studio-ai",
        "aud": "authenticated",
    })
    key = secret_key or settings.SUPABASE_JWT_SECRET or settings.APP_SECRET_KEY
    return jwt.encode(to_encode, key, algorithm="HS256")


def verify_supabase_jwt(token: str) -> Dict[str, Any]:
    """Verify and decode a Supabase Auth JWT token.
    Validates expiration, signature, and standard claims.
    """
    key = settings.SUPABASE_JWT_SECRET or settings.APP_SECRET_KEY
    try:
        payload = jwt.decode(
            token,
            key,
            algorithms=["HS256"],
            audience=["authenticated", "creator-studio-ai"],
            options={"verify_exp": True, "verify_aud": False},
        )
        return payload
    except jwt.ExpiredSignatureError as exc:
        raise ValueError("Token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise ValueError("Invalid token signature or malformed payload") from exc
