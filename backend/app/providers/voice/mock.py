"""Deterministic Mock Voice Provider for fast, offline, and keyless testing."""

import io
import math
import struct
import wave
from typing import List, Optional

from app.providers.voice.base import (
    AudioUsageEstimate,
    GeneratedAudioResult,
    VoiceInfo,
    VoiceNotFoundError,
    VoiceProviderCapabilities,
    VoiceProviderInterface,
    WordTimestamp,
)

DEFAULT_MOCK_VOICES = [
    VoiceInfo(
        voice_id="mock-tech-male-1",
        display_name="Mock Christopher (Tech Lead)",
        provider="mock",
        language_code="en-US",
        gender="MALE",
        description="Calm, authoritative male narrator optimized for deep technical explanations.",
        is_neural=True,
        is_free=True,
    ),
    VoiceInfo(
        voice_id="mock-tech-female-1",
        display_name="Mock Jenny (Fast Explainer)",
        provider="mock",
        language_code="en-US",
        gender="FEMALE",
        description="Clear, fast-paced female voice suitable for tutorials and YouTube Shorts.",
        is_neural=True,
        is_free=True,
    ),
    VoiceInfo(
        voice_id="mock-british-male-1",
        display_name="Mock Ryan (British Architecture)",
        provider="mock",
        language_code="en-GB",
        gender="MALE",
        description="British English accent for architectural reviews and case studies.",
        is_neural=True,
        is_free=True,
    ),
]


def create_synthetic_wav_bytes(
    duration_seconds: float,
    sample_rate: int = 24000,
    frequency: float = 440.0,
    volume: float = 0.2,
) -> bytes:
    """Generate valid 16-bit mono RIFF WAV audio bytes with a gentle sine wave tone."""
    total_frames = int(sample_rate * max(0.1, duration_seconds))
    buffer = io.BytesIO()

    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)      # Mono
        wav_file.setsampwidth(2)     # 16-bit PCM (2 bytes per sample)
        wav_file.setframerate(sample_rate)

        # Generate audio frames
        frames = bytearray()
        amplitude = int(volume * 32767)
        for i in range(total_frames):
            # Soft sine wave with gentle fade-in / fade-out to prevent clicks
            time_sec = i / sample_rate
            envelope = min(1.0, time_sec / 0.05, (duration_seconds - time_sec) / 0.05)
            envelope = max(0.0, envelope)
            sample = int(envelope * amplitude * math.sin(2.0 * math.pi * frequency * time_sec))
            # Clamp sample to 16-bit signed integer range
            sample = max(-32768, min(32767, sample))
            frames.extend(struct.pack("<h", sample))

        wav_file.writeframes(frames)

    return buffer.getvalue()


class MockVoiceProvider(VoiceProviderInterface):
    """Deterministic, keyless voice provider generating real WAV audio for testing and local dev."""

    def __init__(self, voices: Optional[List[VoiceInfo]] = None):
        self._voices = voices or DEFAULT_MOCK_VOICES

    @property
    def name(self) -> str:
        return "mock"

    async def list_voices(self, language_code: Optional[str] = None) -> List[VoiceInfo]:
        if not language_code:
            return list(self._voices)
        return [v for v in self._voices if v.language_code.lower().startswith(language_code.lower())]

    async def generate_speech(
        self,
        text: str,
        voice_id: str,
        speed_ratio: float = 1.0,
        pitch_semitones: float = 0.0,
        output_format: str = "wav",
    ) -> GeneratedAudioResult:
        # Verify voice
        voice_exists = any(v.voice_id == voice_id for v in self._voices)
        if not voice_exists:
            raise VoiceNotFoundError(f"Mock voice '{voice_id}' not found.")

        # Words and duration calculation (~140 WPM adjusted by speed_ratio)
        words = text.split()
        word_count = len(words)
        effective_wpm = 140.0 * max(0.5, min(2.0, speed_ratio))
        duration_seconds = max(0.5, (word_count / effective_wpm) * 60.0)

        # Generate real, compliant WAV audio bytes
        audio_bytes = create_synthetic_wav_bytes(
            duration_seconds=duration_seconds,
            sample_rate=24000,
            frequency=440.0,
            volume=0.2,
        )

        # Generate word-level timestamps
        timestamps: List[WordTimestamp] = []
        if word_count > 0:
            time_per_word = duration_seconds / word_count
            current_time = 0.0
            for w in words:
                start = round(current_time, 3)
                end = round(min(duration_seconds, current_time + (time_per_word * 0.85)), 3)
                timestamps.append(WordTimestamp(word=w, start=start, end=end))
                current_time += time_per_word

        return GeneratedAudioResult(
            audio_bytes=audio_bytes,
            file_format="wav",
            sample_rate=24000,
            channels=1,
            duration_seconds=round(duration_seconds, 3),
            word_timestamps=timestamps,
            loudness_lufs=-14.0,
            file_size_bytes=len(audio_bytes),
        )

    async def preview_voice(
        self,
        voice_id: str,
        sample_text: Optional[str] = None,
    ) -> GeneratedAudioResult:
        text = sample_text or "Hello! This is a preview of the Creator Studio AI voice synthesis engine."
        return await self.generate_speech(text=text, voice_id=voice_id, speed_ratio=1.0)

    def get_capabilities(self) -> VoiceProviderCapabilities:
        return VoiceProviderCapabilities(
            provider_name="mock",
            supported_formats=["wav"],
            supports_rate_adjustment=True,
            supports_pitch_adjustment=True,
            supports_word_timestamps=True,
            supports_multilingual=True,
            is_local=True,
            requires_api_key=False,
        )

    def estimate_usage(self, text: str) -> AudioUsageEstimate:
        words = text.split()
        duration = (len(words) / 140.0) * 60.0
        return AudioUsageEstimate(
            character_count=len(text),
            word_count=len(words),
            estimated_duration_seconds=round(duration, 2),
            estimated_cost_usd=0.00,
        )
