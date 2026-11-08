"""Factory for creating and resolving configured AI provider instances."""

from typing import Optional
from app.core.config import settings
from app.providers.ai.base import AIProviderInterface
from app.providers.ai.gemini import GeminiProvider
from app.providers.ai.mock import MockAIProvider

_active_provider: Optional[AIProviderInterface] = None


def get_ai_provider(provider_type: Optional[str] = None, force_refresh: bool = False) -> AIProviderInterface:
    """Retrieve or initialize the active AI provider.
    
    If provider_type is explicitly specified ('gemini', 'mock'), uses that type.
    Otherwise checks if GEMINI_API_KEY is configured. If not configured or empty,
    falls back cleanly to MockAIProvider so that all local dev and tests run smoothly.
    """
    global _active_provider
    if _active_provider is not None and not force_refresh and provider_type is None:
        return _active_provider

    selected = provider_type.lower() if provider_type else None

    if selected == "gemini":
        provider = GeminiProvider()
    elif selected == "mock":
        provider = MockAIProvider()
    else:
        # Auto-detect from environment
        has_key = bool(settings.GEMINI_API_KEY and len(settings.GEMINI_API_KEY.strip()) > 10 and not settings.GEMINI_API_KEY.startswith("dummy"))
        if has_key:
            provider = GeminiProvider()
        else:
            provider = MockAIProvider()

    if provider_type is None:
        _active_provider = provider

    return provider


def set_active_provider(provider: AIProviderInterface) -> None:
    """Explicitly override active provider (useful for tests)."""
    global _active_provider
    _active_provider = provider
