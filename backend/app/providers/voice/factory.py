"""Factory and Registry for Voice Providers."""

from typing import Dict, Optional

from app.core.config import settings
from app.core.logging import logger
from app.providers.voice.base import VoiceProviderInterface
from app.providers.voice.edge_tts_provider import EdgeTTSProvider, HAS_EDGE_TTS
from app.providers.voice.mock import MockVoiceProvider

_ACTIVE_PROVIDER: Optional[VoiceProviderInterface] = None
_PROVIDERS: Dict[str, VoiceProviderInterface] = {}


def register_voice_provider(provider: VoiceProviderInterface) -> None:
    """Register a voice provider instance."""
    _PROVIDERS[provider.name.lower()] = provider
    logger.debug(f"Registered voice provider: {provider.name}")


def get_voice_provider(provider_name: Optional[str] = None) -> VoiceProviderInterface:
    """Retrieve active voice provider or specific provider by name."""
    global _ACTIVE_PROVIDER

    # If active provider explicitly set (e.g. by test fixture), return it
    if provider_name is None and _ACTIVE_PROVIDER is not None:
        return _ACTIVE_PROVIDER

    target_name = (provider_name or settings.TTS_ENGINE).lower()

    if target_name in _PROVIDERS:
        return _PROVIDERS[target_name]

    # Initialize requested provider
    if target_name in ("edge-tts", "edgetts"):
        if HAS_EDGE_TTS:
            provider = EdgeTTSProvider()
        else:
            logger.warning("edge-tts requested but not installed. Falling back to MockVoiceProvider.")
            provider = MockVoiceProvider()
    elif target_name == "mock":
        provider = MockVoiceProvider()
    else:
        logger.warning(f"Unknown voice provider '{target_name}'. Defaulting to MockVoiceProvider.")
        provider = MockVoiceProvider()

    register_voice_provider(provider)
    if _ACTIVE_PROVIDER is None and provider_name is None:
        _ACTIVE_PROVIDER = provider

    return provider


def set_active_voice_provider(provider: VoiceProviderInterface) -> None:
    """Explicitly set the active voice provider (used in test fixtures)."""
    global _ACTIVE_PROVIDER
    _ACTIVE_PROVIDER = provider
    register_voice_provider(provider)
