"""Test application configuration loading and validation."""

from app.core.config import Settings


def test_default_settings():
    """Verify default configuration attributes."""
    cfg = Settings()
    assert cfg.APP_NAME == "Creator Studio AI"
    assert cfg.APP_PORT == 8000
    assert cfg.MAX_MONTHLY_SPEND_USD == 0.00
    assert cfg.FREE_TIER_RPM_LIMIT == 15
    assert cfg.TTS_ENGINE == "edge-tts"
    assert cfg.STORAGE_DRIVER == "local"
    assert not cfg.is_production


def test_cors_origins_contain_frontend():
    """Verify CORS origins allow standard frontend dev server."""
    cfg = Settings()
    assert "http://localhost:3000" in cfg.ALLOWED_ORIGINS
