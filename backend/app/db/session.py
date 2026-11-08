"""Database session management and connection pooling."""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from app.core.config import settings
from app.core.logging import logger

# Declarative Base for models
Base = declarative_base()

# Async Engine for application runtime
# Using NullPool or standard pooling based on environment
connect_args = {}
if "supabase.co" in settings.DATABASE_URL or "supabase.com" in settings.DATABASE_URL:
    connect_args["ssl"] = "require"

if "6543" in settings.DATABASE_URL or "pooler.supabase.com" in settings.DATABASE_URL:
    # Transaction poolers (e.g. PgBouncer on port 6543) require disabling prepared statement cache in asyncpg
    connect_args["statement_cache_size"] = 0

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.APP_DEBUG,
    future=True,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    connect_args=connect_args,
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as exc:
            await session.rollback()
            logger.error(f"Database session rollback triggered by error: {exc}")
            raise
        finally:
            await session.close()


async def check_db_connection() -> bool:
    """Verify database connectivity."""
    try:
        import asyncio
        from sqlalchemy import text

        async def _ping():
            async with AsyncSessionLocal() as session:
                result = await session.execute(text("SELECT 1"))
                return result.scalar() == 1

        return await asyncio.wait_for(_ping(), timeout=1.0)
    except Exception as exc:
        logger.warning(f"Database connectivity check failed (non-fatal for M01): {exc}")
        return False
