"""Unit tests for Voice Providers and Speech Synthesis Abstraction."""

import pytest
from app.providers.voice.base import VoiceNotFoundError
from app.providers.voice.factory import (
    get_voice_provider,
    register_voice_provider,
    set_active_voice_provider,
)
from app.providers.voice.mock import MockVoiceProvider, create_synthetic_wav_bytes
from app.services.audio_processing import AudioProcessingService


@pytest.fixture(autouse=True)
def ensure_mock_voice_provider():
    set_active_voice_provider(MockVoiceProvider())


@pytest.mark.asyncio
async def test_mock_voice_provider_synthesis():
    provider = MockVoiceProvider()
    text = "PostgreSQL SKIP LOCKED eliminates background queue infrastructure overhead."
    result = await provider.generate_speech(
        text=text,
        voice_id="mock-tech-male-1",
        speed_ratio=1.0,
    )

    assert result.audio_bytes is not None
    assert len(result.audio_bytes) > 100
    assert result.file_format == "wav"
    assert result.sample_rate == 24000
    assert result.channels == 1
    assert result.duration_seconds > 0.5
    assert len(result.word_timestamps) == len(text.split())
    assert result.loudness_lufs == -14.0

    # Verify actual WAV header is valid
    meta = AudioProcessingService.get_wav_metadata(result.audio_bytes)
    assert meta.sample_rate == 24000
    assert meta.channels == 1
    assert abs(meta.duration_seconds - result.duration_seconds) < 0.1


@pytest.mark.asyncio
async def test_mock_voice_provider_preview():
    provider = MockVoiceProvider()
    preview = await provider.preview_voice("mock-tech-male-1")
    assert preview.audio_bytes is not None
    assert preview.duration_seconds > 0.0
    assert preview.file_format == "wav"


@pytest.mark.asyncio
async def test_mock_voice_provider_nonexistent_voice_raises():
    provider = MockVoiceProvider()
    with pytest.raises(VoiceNotFoundError):
        await provider.generate_speech("Test", voice_id="nonexistent-voice-999")


@pytest.mark.asyncio
async def test_voice_list_and_language_filtering():
    provider = MockVoiceProvider()
    all_voices = await provider.list_voices()
    assert len(all_voices) >= 3

    en_us_voices = await provider.list_voices(language_code="en-US")
    assert len(en_us_voices) >= 2
    for v in en_us_voices:
        assert v.language_code.startswith("en-US")

    en_gb_voices = await provider.list_voices(language_code="en-GB")
    assert len(en_gb_voices) >= 1
    assert en_gb_voices[0].language_code == "en-GB"


def test_voice_provider_capabilities_and_usage_estimate():
    provider = MockVoiceProvider()
    caps = provider.get_capabilities()
    assert caps.provider_name == "mock"
    assert "wav" in caps.supported_formats
    assert caps.supports_word_timestamps is True

    text = "Hello world this is a test of voice usage estimation."
    estimate = provider.estimate_usage(text)
    assert estimate.word_count == 10
    assert estimate.estimated_duration_seconds > 0.0
    assert estimate.estimated_cost_usd == 0.00


def test_voice_provider_factory():
    provider = get_voice_provider("mock")
    assert provider.name == "mock"

    custom_mock = MockVoiceProvider()
    set_active_voice_provider(custom_mock)
    assert get_voice_provider() is custom_mock
