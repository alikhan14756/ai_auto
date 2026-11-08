"""Voice and Speech Synthesis Providers Package."""

from app.providers.voice.base import (
    AudioUsageEstimate,
    GeneratedAudioResult,
    VoiceInfo,
    VoiceNotFoundError,
    VoiceProviderCapabilities,
    VoiceProviderError,
    VoiceProviderInterface,
    VoiceSynthesisError,
    WordTimestamp,
)
from app.providers.voice.edge_tts_provider import EdgeTTSProvider
from app.providers.voice.factory import (
    get_voice_provider,
    register_voice_provider,
    set_active_voice_provider,
)
from app.providers.voice.mock import MockVoiceProvider

__all__ = [
    "VoiceProviderInterface",
    "VoiceProviderError",
    "VoiceNotFoundError",
    "VoiceSynthesisError",
    "VoiceInfo",
    "WordTimestamp",
    "GeneratedAudioResult",
    "VoiceProviderCapabilities",
    "AudioUsageEstimate",
    "EdgeTTSProvider",
    "MockVoiceProvider",
    "get_voice_provider",
    "register_voice_provider",
    "set_active_voice_provider",
]
