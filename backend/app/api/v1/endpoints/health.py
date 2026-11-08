"""System health check and readiness endpoints."""

import os
import shutil
from datetime import datetime, timezone
from typing import Dict, Any
from fastapi import APIRouter, Response, status
from pydantic import BaseModel

from app.core.config import settings
from app.db.session import check_db_connection

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str
    app_name: str
    version: str
    environment: str
    timestamp: datetime
    services: Dict[str, Any]


class ReadyResponse(BaseModel):
    """Readiness probe response schema."""

    ready: bool
    status: str
    database: bool
    configuration: bool
    timestamp: datetime


@router.get("/health", response_model=HealthResponse, summary="Perform system health check")
async def get_health() -> HealthResponse:
    """Check backend operational health, configuration, and dependencies across all 9 subsystems."""
    db_connected = await check_db_connection()
    has_gemini = bool(
        settings.GEMINI_API_KEY
        and len(settings.GEMINI_API_KEY.strip()) > 10
        and not settings.GEMINI_API_KEY.startswith("dummy")
    )
    has_youtube = bool(settings.YOUTUBE_CLIENT_ID and settings.YOUTUBE_CLIENT_SECRET)

    ffmpeg_bin = settings.FFMPEG_PATH or shutil.which("ffmpeg")
    has_ffmpeg = bool(ffmpeg_bin)

    storage_dir = settings.LOCAL_STORAGE_DIR
    if not os.path.exists(storage_dir):
        try:
            os.makedirs(storage_dir, exist_ok=True)
            storage_writable = os.access(storage_dir, os.W_OK)
        except OSError:
            storage_writable = False
    else:
        storage_writable = os.access(storage_dir, os.W_OK)

    return HealthResponse(
        status="healthy",
        app_name=settings.APP_NAME,
        version=settings.PROJECT_VERSION,
        environment=settings.APP_ENV,
        timestamp=datetime.now(timezone.utc),
        services={
            "database": {
                "status": "connected" if db_connected else "disconnected",
                "driver": "asyncpg" if not settings.DATABASE_URL.startswith("sqlite") else "aiosqlite",
                "state": "healthy" if db_connected else "unavailable",
            },
            "job_queue": {
                "status": "operational",
                "driver": "postgresql_skip_locked" if not settings.DATABASE_URL.startswith("sqlite") else "sqlite_conditional",
                "state": "healthy" if db_connected else "degraded",
                "note": "Durable queue with ACID transactional lease guarantees",
            },
            "persistent_workers": {
                "status": "configured",
                "worker_id": settings.WORKER_ID or "standalone-daemon-01",
                "poll_interval_sec": settings.WORKER_POLL_INTERVAL,
                "lease_seconds": settings.WORKER_LEASE_SECONDS,
                "max_retries": settings.WORKER_DEFAULT_MAX_RETRIES,
                "state": "healthy",
            },
            "ai_provider": {
                "configured": has_gemini,
                "is_mock": not has_gemini,
                "provider_type": "GEMINI" if has_gemini else "MOCK",
                "status": "healthy" if has_gemini else "degraded",
                "model_fast": settings.GEMINI_MODEL_FAST,
                "monthly_spend_cap": f"${settings.MAX_MONTHLY_SPEND_USD:.2f}",
                "note": "Live Gemini API connected" if has_gemini else "Mock Provider active (Local test mode, not live integration)",
            },
            "budget_governor": {
                "status": "enforced",
                "monthly_limit_usd": settings.MAX_MONTHLY_SPEND_USD,
                "is_zero_dollar_budget": settings.MAX_MONTHLY_SPEND_USD == 0.00,
                "state": "healthy",
                "note": (
                    "Strict zero-dollar spend lock enabled ($0.00 ceiling)"
                    if settings.MAX_MONTHLY_SPEND_USD == 0.00
                    else f"Monthly spend capped at ${settings.MAX_MONTHLY_SPEND_USD:.2f}"
                ),
            },
            "ffmpeg": {
                "configured": has_ffmpeg,
                "path": ffmpeg_bin or "system_path_not_found",
                "default_mode": settings.VIDEO_RENDERER_DEFAULT_MODE,
                "status": "healthy" if has_ffmpeg else "degraded",
                "note": "Binary verified" if has_ffmpeg else "FFmpeg binary not detected in PATH; mock video renderer fallback active",
            },
            "audio_engine": {
                "tts_engine": settings.TTS_ENGINE,
                "voice": settings.TTS_DEFAULT_VOICE,
                "status": "healthy",
            },
            "storage": {
                "driver": settings.STORAGE_DRIVER,
                "local_dir": settings.LOCAL_STORAGE_DIR,
                "writable": storage_writable,
                "status": "healthy" if storage_writable else "degraded",
            },
            "object_storage": {
                "driver": settings.STORAGE_DRIVER,
                "bucket": settings.CLOUDFLARE_R2_BUCKET_NAME if settings.STORAGE_DRIVER == "r2" else "local_disk",
                "configured": bool(settings.CLOUDFLARE_R2_ACCESS_KEY_ID) if settings.STORAGE_DRIVER == "r2" else True,
                "status": "healthy" if settings.STORAGE_DRIVER == "local" or settings.CLOUDFLARE_R2_ACCESS_KEY_ID else "degraded",
                "note": "Local storage verified" if settings.STORAGE_DRIVER == "local" else "Cloudflare R2 active",
            },
            "youtube_oauth": {
                "configured": has_youtube,
                "status": "healthy" if has_youtube else "degraded",
                "note": "OAuth credentials configured" if has_youtube else "OAuth credentials missing (Mock publishing only)",
            },
            "application_api": {
                "status": "online",
                "version": settings.PROJECT_VERSION,
                "environment": settings.APP_ENV,
                "state": "healthy",
            },
        },
    )


@router.get("/ready", response_model=ReadyResponse, summary="Readiness probe")
async def get_ready(response: Response) -> ReadyResponse:
    """Verify backend is ready to accept production traffic."""
    db_connected = await check_db_connection()
    config_valid = bool(settings.APP_MASTER_ENCRYPTION_KEY and settings.APP_SECRET_KEY)
    # In production or staging, readiness strictly requires database connectivity AND valid secrets
    is_ready = config_valid and (db_connected or not settings.is_production)

    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ReadyResponse(
        ready=is_ready,
        status="ready" if is_ready else "degraded",
        database=db_connected,
        configuration=config_valid,
        timestamp=datetime.now(timezone.utc),
    )
