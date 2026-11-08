"""Unit and integration tests for AI Providers and Rate Limiting."""

import asyncio
import pytest
from pydantic import BaseModel

from app.providers.ai.base import (
    AIProviderError,
    AIRateLimitError,
    AITimeoutError,
    ProviderStructuredResponse,
    ProviderTextResponse,
)
from app.providers.ai.gemini import GeminiRateLimiter
from app.providers.ai.mock import MockAIProvider
from app.providers.ai.factory import get_ai_provider, set_active_provider


class DummySchema(BaseModel):
    title: str
    score: float


@pytest.mark.asyncio
async def test_mock_provider_generate_text():
    provider = MockAIProvider(default_model="test-fast")
    assert provider.name == "MOCK"
    assert provider.default_model == "test-fast"

    resp = await provider.generate_text(prompt="What is PostgreSQL SKIP LOCKED?")
    assert isinstance(resp, ProviderTextResponse)
    assert "SKIP LOCKED" in resp.text
    assert resp.usage.total_tokens > 0
    assert resp.usage.prompt_tokens > 0
    assert resp.model_name == "test-fast"


@pytest.mark.asyncio
async def test_mock_provider_generate_structured():
    provider = MockAIProvider()
    resp = await provider.generate_structured(
        prompt="Propose dummy item",
        response_schema=DummySchema,
    )
    assert isinstance(resp, ProviderStructuredResponse)
    assert isinstance(resp.parsed, DummySchema)
    assert resp.parsed.title is not None
    assert resp.parsed.score is not None
    assert resp.usage.total_tokens > 0


@pytest.mark.asyncio
async def test_mock_provider_simulated_faults():
    # Rate limit simulation
    rate_limited_provider = MockAIProvider(simulate_rate_limit=True)
    with pytest.raises(AIRateLimitError) as exc_info:
        await rate_limited_provider.generate_text("test")
    assert "429" in str(exc_info.value)
    assert exc_info.value.status_code == 429

    # Timeout simulation
    timeout_provider = MockAIProvider(simulate_timeout=True)
    with pytest.raises(AITimeoutError):
        await timeout_provider.generate_text("test")

    # Generic AI error simulation
    error_provider = MockAIProvider(simulate_error=True)
    with pytest.raises(AIProviderError):
        await error_provider.generate_text("test")


@pytest.mark.asyncio
async def test_mock_provider_health_check():
    provider = MockAIProvider()
    health = await provider.health_check()
    assert health.is_healthy is True
    assert health.provider_name == "MOCK"
    assert health.latency_ms >= 0.0

    faulty = MockAIProvider(simulate_error=True)
    health_faulty = await faulty.health_check()
    assert health_faulty.is_healthy is False
    assert "error" in health_faulty.message.lower()


@pytest.mark.asyncio
async def test_gemini_rate_limiter_rpm_enforcement():
    limiter = GeminiRateLimiter(rpm_limit=3, rpd_limit=100)

    # 3 acquires should succeed
    await limiter.acquire()
    await limiter.acquire()
    await limiter.acquire()

    stats = limiter.get_stats()
    assert stats["current_rpm"] == 3
    assert stats["rpm_limit"] == 3

    # 4th acquire within 60s must raise AIRateLimitError
    with pytest.raises(AIRateLimitError) as exc:
        await limiter.acquire()
    assert "RPM limit" in str(exc.value)


@pytest.mark.asyncio
async def test_ai_provider_factory():
    mock_p = get_ai_provider("mock", force_refresh=True)
    assert mock_p.name == "MOCK"

    custom_mock = MockAIProvider(default_model="custom-override")
    set_active_provider(custom_mock)
    retrieved = get_ai_provider()
    assert retrieved.default_model == "custom-override"
