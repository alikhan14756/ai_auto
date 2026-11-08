"""Official Google Gemini AI Provider implementation using google-genai SDK."""

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Type, TypeVar
from pydantic import BaseModel
from google import genai
from google.genai import types
from google.genai import errors as genai_errors

from app.core.config import settings
from app.core.logging import logger
from app.providers.ai.base import (
    AIProviderInterface,
    AIProviderError,
    AIRateLimitError,
    AIQuotaExceededError,
    AITimeoutError,
    AIAuthenticationError,
    ProviderUsageMetrics,
    ProviderTextResponse,
    ProviderStructuredResponse,
    ProviderHealthStatus,
)

T = TypeVar("T", bound=BaseModel)

# Pricing per million tokens (USD)
PRICING_PER_1M = {
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
    "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
}


class GeminiRateLimiter:
    """Sliding-window in-memory rate limiter enforcing Free Tier RPM/RPD limits."""

    def __init__(self, rpm_limit: int = 15, rpd_limit: int = 1500):
        self.rpm_limit = rpm_limit
        self.rpd_limit = rpd_limit
        self._minute_window: List[float] = []
        self._day_window: List[float] = []
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.time()
            # Prune minute window (> 60s)
            self._minute_window = [t for t in self._minute_window if now - t < 60.0]
            # Prune day window (> 86400s)
            self._day_window = [t for t in self._day_window if now - t < 86400.0]

            if len(self._minute_window) >= self.rpm_limit:
                oldest = self._minute_window[0]
                wait_sec = round(60.0 - (now - oldest), 2)
                raise AIRateLimitError(
                    f"Gemini Free Tier RPM limit ({self.rpm_limit} req/min) exceeded. Wait {wait_sec}s.",
                    provider="GEMINI",
                    status_code=429,
                )

            if len(self._day_window) >= self.rpd_limit:
                raise AIQuotaExceededError(
                    f"Gemini Free Tier RPD limit ({self.rpd_limit} req/day) exhausted for today.",
                    provider="GEMINI",
                    status_code=429,
                )

            self._minute_window.append(now)
            self._day_window.append(now)

    def get_stats(self) -> Dict[str, Any]:
        now = time.time()
        active_rpm = len([t for t in self._minute_window if now - t < 60.0])
        active_rpd = len([t for t in self._day_window if now - t < 86400.0])
        return {
            "current_rpm": active_rpm,
            "rpm_limit": self.rpm_limit,
            "current_rpd": active_rpd,
            "rpd_limit": self.rpd_limit,
        }


class GeminiProvider(AIProviderInterface):
    """Google Gemini generative AI provider backed by the official google-genai SDK."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: Optional[str] = None,
        rpm_limit: Optional[int] = None,
        rpd_limit: Optional[int] = None,
    ):
        self._name = "GEMINI"
        self._api_key = api_key or settings.GEMINI_API_KEY
        self._default_model = default_model or settings.GEMINI_MODEL_FAST
        self._rate_limiter = GeminiRateLimiter(
            rpm_limit=rpm_limit or settings.FREE_TIER_RPM_LIMIT,
            rpd_limit=rpd_limit or settings.FREE_TIER_RPD_LIMIT,
        )
        self._client: Optional[genai.Client] = None
        if self._api_key:
            self._client = genai.Client(api_key=self._api_key)

    @property
    def name(self) -> str:
        return self._name

    @property
    def default_model(self) -> str:
        return self._default_model

    @property
    def rate_limiter(self) -> GeminiRateLimiter:
        return self._rate_limiter

    def _calculate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate estimated cost in USD based on model pricing."""
        rates = PRICING_PER_1M.get(model, PRICING_PER_1M["gemini-1.5-flash"])
        input_cost = (prompt_tokens / 1_000_000.0) * rates["input"]
        output_cost = (completion_tokens / 1_000_000.0) * rates["output"]
        return round(input_cost + output_cost, 6)

    def _extract_usage(self, response: Any, model: str) -> ProviderUsageMetrics:
        prompt_tokens = 0
        completion_tokens = 0
        total_tokens = 0

        metadata = getattr(response, "usage_metadata", None)
        if metadata:
            prompt_tokens = getattr(metadata, "prompt_token_count", 0) or 0
            completion_tokens = getattr(metadata, "candidates_token_count", 0) or 0
            total_tokens = getattr(metadata, "total_token_count", 0) or (prompt_tokens + completion_tokens)

        cost = self._calculate_cost(model, prompt_tokens, completion_tokens)
        return ProviderUsageMetrics(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=cost,
        )

    def _normalize_error(self, exc: Exception) -> Exception:
        """Map SDK errors to standardized AI provider exceptions."""
        if isinstance(exc, (AIProviderError, AIRateLimitError, AITimeoutError, AIQuotaExceededError)):
            return exc

        if isinstance(exc, asyncio.TimeoutError):
            return AITimeoutError(f"Gemini API timed out: {str(exc)}", provider=self.name)

        if isinstance(exc, genai_errors.APIError):
            code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
            msg = str(exc)
            if code == 429 or "RESOURCE_EXHAUSTED" in msg or "quota" in msg.lower():
                return AIRateLimitError(f"Gemini rate limit / quota exceeded: {msg}", provider=self.name, status_code=429)
            if code in (401, 403) or "PERMISSION_DENIED" in msg or "API_KEY_INVALID" in msg:
                return AIAuthenticationError(f"Gemini auth error: {msg}", provider=self.name, status_code=code)
            return AIProviderError(f"Gemini API error ({code}): {msg}", provider=self.name, status_code=code)

        if isinstance(exc, genai_errors.ClientError):
            msg = str(exc)
            if "API_KEY" in msg.upper() or "KEY" in msg.upper():
                return AIAuthenticationError(f"Gemini API key error: {msg}", provider=self.name, status_code=401)
            return AIProviderError(f"Gemini Client error: {msg}", provider=self.name)

        return AIProviderError(f"Unexpected Gemini provider error: {str(exc)}", provider=self.name)

    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        timeout_seconds: float = 60.0,
    ) -> ProviderTextResponse:
        if not self._client or not self._api_key:
            raise AIAuthenticationError("GEMINI_API_KEY is not configured.", provider=self.name, status_code=401)

        await self._rate_limiter.acquire()
        chosen_model = model or self._default_model

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature,
            max_output_tokens=max_tokens,
        )

        try:
            async with asyncio.timeout(timeout_seconds):
                response = await self._client.aio.models.generate_content(
                    model=chosen_model,
                    contents=prompt,
                    config=config,
                )

            text_content = ""
            if response and response.text:
                text_content = response.text

            usage = self._extract_usage(response, chosen_model)
            return ProviderTextResponse(
                text=text_content,
                usage=usage,
                model_name=chosen_model,
            )
        except Exception as exc:
            raise self._normalize_error(exc)

    async def generate_structured(
        self,
        prompt: str,
        response_schema: Type[T],
        system_instruction: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        timeout_seconds: float = 60.0,
    ) -> ProviderStructuredResponse:
        if not self._client or not self._api_key:
            raise AIAuthenticationError("GEMINI_API_KEY is not configured.", provider=self.name, status_code=401)

        await self._rate_limiter.acquire()
        chosen_model = model or self._default_model

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature,
            response_mime_type="application/json",
            response_schema=response_schema,
        )

        try:
            async with asyncio.timeout(timeout_seconds):
                response = await self._client.aio.models.generate_content(
                    model=chosen_model,
                    contents=prompt,
                    config=config,
                )

            raw_text = response.text or "{}"
            parsed_instance = response_schema.model_validate_json(raw_text)
            usage = self._extract_usage(response, chosen_model)

            return ProviderStructuredResponse(
                parsed=parsed_instance,
                raw_text=raw_text,
                usage=usage,
                model_name=chosen_model,
            )
        except Exception as exc:
            raise self._normalize_error(exc)

    async def health_check(self) -> ProviderHealthStatus:
        if not self._client or not self._api_key:
            return ProviderHealthStatus(
                is_healthy=False,
                provider_name=self.name,
                model_name=self.default_model,
                latency_ms=0.0,
                message="GEMINI_API_KEY is missing or unconfigured.",
            )

        start = time.perf_counter()
        try:
            async with asyncio.timeout(10.0):
                response = await self._client.aio.models.generate_content(
                    model=self._default_model,
                    contents="ping",
                    config=types.GenerateContentConfig(max_output_tokens=10),
                )
            latency = (time.perf_counter() - start) * 1000
            return ProviderHealthStatus(
                is_healthy=True,
                provider_name=self.name,
                model_name=self.default_model,
                latency_ms=round(latency, 2),
                message="Google Gemini API operational and authenticated.",
            )
        except Exception as exc:
            latency = (time.perf_counter() - start) * 1000
            normalized = self._normalize_error(exc)
            return ProviderHealthStatus(
                is_healthy=False,
                provider_name=self.name,
                model_name=self.default_model,
                latency_ms=round(latency, 2),
                message=str(normalized),
            )
