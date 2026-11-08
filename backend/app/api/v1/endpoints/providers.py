"""AI Provider management, diagnostics, and usage reporting endpoints."""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_active_user
from app.core.config import settings
from app.models.user import User
from app.providers.ai.base import AIProviderError
from app.providers.ai.factory import get_ai_provider
from app.providers.ai.gemini import GeminiProvider
from app.schemas.provider import (
    ProviderHealthResponse,
    ProviderStatusResponse,
    ProviderTestRequest,
    ProviderTestResponse,
    UsageSummaryResponse,
)
from app.services.usage import UsageTrackingService

router = APIRouter()


@router.get("/status", response_model=ProviderStatusResponse)
async def get_provider_status(
    current_user: User = Depends(get_current_active_user),
):
    """Retrieve operational status, model configuration, and rate-limit statistics of active AI provider."""
    provider = get_ai_provider()
    has_api_key = bool(
        settings.GEMINI_API_KEY
        and len(settings.GEMINI_API_KEY.strip()) > 10
        and not settings.GEMINI_API_KEY.startswith("dummy")
    )

    current_rpm = 0
    current_rpd = 0
    if isinstance(provider, GeminiProvider):
        stats = provider.rate_limiter.get_stats()
        current_rpm = stats["current_rpm"]
        current_rpd = stats["current_rpd"]

    return ProviderStatusResponse(
        active_provider=provider.name,
        default_model=provider.default_model,
        reasoning_model=settings.GEMINI_MODEL_REASONING,
        free_tier_rpm_limit=settings.FREE_TIER_RPM_LIMIT,
        free_tier_rpd_limit=settings.FREE_TIER_RPD_LIMIT,
        current_rpm=current_rpm,
        current_rpd=current_rpd,
        has_api_key=has_api_key,
    )


@router.get("/health", response_model=ProviderHealthResponse)
async def check_provider_health(
    current_user: User = Depends(get_current_active_user),
):
    """Run an active diagnostic health check query against the AI provider."""
    provider = get_ai_provider()
    health = await provider.health_check()
    return ProviderHealthResponse(
        is_healthy=health.is_healthy,
        provider_name=health.provider_name,
        model_name=health.model_name,
        latency_ms=health.latency_ms,
        message=health.message,
    )


@router.get("/usage", response_model=UsageSummaryResponse)
async def get_channel_usage(
    channel_id: UUID = Query(..., description="Target Channel ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Retrieve token usage metrics, spend breakdown, and budget status for a channel."""
    summary = await UsageTrackingService.get_channel_usage_summary(channel_id, db)
    return UsageSummaryResponse(**summary)


@router.post("/test", response_model=ProviderTestResponse)
async def test_provider_inference(
    request: ProviderTestRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Execute a dry-run test prompt against the active AI provider."""
    provider = get_ai_provider()
    try:
        resp = await provider.generate_text(
            prompt=request.prompt,
            model=request.model,
            max_tokens=256,
            temperature=0.7,
        )
        return ProviderTestResponse(
            text=resp.text,
            usage=resp.usage.model_dump(),
            model_name=resp.model_name,
        )
    except AIProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI Provider error during test inference: {str(exc)}",
        )
