"""Test database configuration and Alembic environment discovery."""

import pytest
from app.core.config import settings
from app.db.session import Base, engine, check_db_connection


def test_database_url_configured():
    """Verify database URLs are configured correctly."""
    assert settings.DATABASE_URL.startswith("postgresql+asyncpg://")
    assert settings.DATABASE_URL_SYNC.startswith("postgresql://")


def test_declarative_base():
    """Verify SQLAlchemy declarative base is initialized."""
    assert hasattr(Base, "metadata")
    assert Base.metadata is not None


def test_engine_initialized():
    """Verify async database engine is initialized."""
    assert engine is not None
    assert engine.url.drivername == "postgresql+asyncpg"


@pytest.mark.asyncio
async def test_graceful_db_fallback():
    """Verify check_db_connection handles missing local DB gracefully without crashing."""
    connected = await check_db_connection()
    assert isinstance(connected, bool)
