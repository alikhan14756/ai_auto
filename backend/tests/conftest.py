"""Pytest fixtures and test database configuration."""

import os
import uuid
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.models.user import User
from app.models.channel import Channel, ChannelSettings
from app.core.security import create_access_token, encrypt_token, ROLE_CREATOR, ROLE_SUPER_ADMIN

# Use in-memory SQLite for high-speed, isolated unit & API testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest_asyncio.fixture(autouse=True)
async def init_test_db():
    """Create all tables in test database."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide isolated transactional async session for tests."""
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()


@pytest.fixture
def client(db_session: AsyncSession):
    """FastAPI TestClient with overridden get_db dependency."""
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Fixture providing a standard CREATOR user."""
    user = User(
        supabase_user_id=f"test_sub_{uuid.uuid4().hex[:12]}",
        email=f"creator_{uuid.uuid4().hex[:8]}@example.com",
        full_name="Creator User",
        role=ROLE_CREATOR,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Fixture providing a SUPER_ADMIN user."""
    user = User(
        supabase_user_id=f"test_admin_{uuid.uuid4().hex[:12]}",
        email=f"admin_{uuid.uuid4().hex[:8]}@example.com",
        full_name="Admin User",
        role=ROLE_SUPER_ADMIN,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def other_user(db_session: AsyncSession) -> User:
    """Fixture providing another CREATOR user to test multi-tenant boundaries."""
    user = User(
        supabase_user_id=f"test_other_{uuid.uuid4().hex[:12]}",
        email=f"other_{uuid.uuid4().hex[:8]}@example.com",
        full_name="Other Tenant",
        role=ROLE_CREATOR,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_channel(db_session: AsyncSession, test_user: User) -> Channel:
    """Fixture providing a test channel belonging to test_user."""
    channel = Channel(
        user_id=test_user.id,
        youtube_channel_id=f"UC_{uuid.uuid4().hex[:20]}",
        title="Test AI Channel",
        description="A channel for automated AI testing",
        oauth_refresh_token_encrypted=encrypt_token("mock-oauth-refresh-token"),
        is_active=True,
    )
    db_session.add(channel)
    await db_session.flush()

    settings = ChannelSettings(
        channel_id=channel.id,
        niche_keywords=["ai tools", "productivity"],
        default_privacy="unlisted",
        default_category_id="28",
        weekly_cadence_long=2,
        weekly_cadence_shorts=3,
        auto_publish_enabled=False,
        max_monthly_spend_usd=0.00,
        topic_retention_weights={"CTR": 0.4, "retention_30s": 0.6},
    )
    db_session.add(settings)
    await db_session.commit()
    await db_session.refresh(channel)
    return channel


def auth_headers_for(user: User) -> dict:
    """Generate authorization headers for a given user."""
    token = create_access_token({
        "sub": user.supabase_user_id,
        "email": user.email,
        "role": user.role,
        "user_metadata": {"full_name": user.full_name},
    })
    return {"Authorization": f"Bearer {token}"}
