"""Test token encryption (AES-256-GCM) and JWT handling."""

import pytest
from datetime import timedelta
from app.core.security import (
    encrypt_token,
    decrypt_token,
    create_access_token,
    verify_supabase_jwt,
)


def test_aes_gcm_token_encryption_roundtrip():
    """Verify AES-256-GCM encryption and decryption roundtrip."""
    secret = "ya29.a0AfH6SMD_very_secret_oauth_refresh_token_123456789"
    encrypted = encrypt_token(secret)
    assert encrypted != secret
    assert len(encrypted) > 20

    decrypted = decrypt_token(encrypted)
    assert decrypted == secret


def test_aes_gcm_tampered_ciphertext_detection():
    """Verify corrupted ciphertext raises ValueError without silent failure."""
    secret = "my-secret-token"
    encrypted = encrypt_token(secret)

    # Tamper with the encrypted string
    tampered = encrypted[:-4] + "AAAA"
    with pytest.raises(ValueError, match="Decryption failed"):
        decrypt_token(tampered)


def test_jwt_token_creation_and_verification():
    """Verify JWT token signing and decoding."""
    payload = {
        "sub": "user_123456",
        "email": "test@example.com",
        "role": "CREATOR",
        "user_metadata": {"full_name": "Test Creator"},
    }
    token = create_access_token(payload, expires_delta=timedelta(hours=1))
    decoded = verify_supabase_jwt(token)

    assert decoded["sub"] == "user_123456"
    assert decoded["email"] == "test@example.com"
    assert decoded["role"] == "CREATOR"


def test_jwt_expired_token_rejection():
    """Verify expired JWT token is rejected."""
    payload = {"sub": "user_expired", "email": "exp@example.com"}
    expired_token = create_access_token(payload, expires_delta=timedelta(seconds=-10))

    with pytest.raises(ValueError, match="Token has expired"):
        verify_supabase_jwt(expired_token)


def test_jwt_invalid_signature_rejection():
    """Verify JWT with altered signature is rejected."""
    payload = {"sub": "user_forged", "email": "forged@example.com"}
    token = create_access_token(payload, secret_key="wrong-secret-key-1234567890abcdef")

    with pytest.raises(ValueError, match="Invalid token signature"):
        verify_supabase_jwt(token)
