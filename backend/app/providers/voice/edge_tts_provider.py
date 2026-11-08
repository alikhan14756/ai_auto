"""Microsoft Edge Online Neural TTS Provider implementation."""

import asyncio
import io
from typing import List, Optional

try:
    import edge_tts
    HAS_EDGE_TTS = True
except ImportError:
    HAS_EDGE_TTS = False

from app.core.logging import logger
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


class EdgeTTSProvider(VoiceProviderInterface):
    """Zero-cost neural text-to-speech engine using Edge TTS online neural voices."""

    def __init__(self):
        if not HAS_EDGE_TTS:
            logger.warning("edge-tts library is not installed. EdgeTTSProvider will fail if invoked.")

    @property
    def name(self) -> str:
        return "edge-tts"

    async def list_voices(self, language_code: Optional[str] = None) -> List[VoiceInfo]:
        if not HAS_EDGE_TTS:
            raise VoiceProviderError("edge-tts library is not available.")

        try:
            raw_voices = await edge_tts.list_voices()
        except Exception as exc:
            logger.error(f"Failed to fetch Edge TTS voice list: {exc}")
            raise VoiceProviderError(f"Failed to fetch voices from Edge TTS: {str(exc)}") from exc

        results: List[VoiceInfo] = []
        for v in raw_voices:
            locale = v.get("Locale", "en-US")
            if language_code and not locale.lower().startswith(language_code.lower()):
                continue

            results.append(
                VoiceInfo(
                    voice_id=v.get("ShortName", ""),
                    display_name=v.get("FriendlyName", v.get("ShortName", "")),
                    provider="edge-tts",
                    language_code=locale,
                    gender=v.get("Gender", "NEUTRAL").upper(),
                    description=f"{locale} Neural Voice ({v.get('VoiceType', 'Neural')})",
                    is_neural=True,
                    is_free=True,
                )
            )

        return results

    def _format_rate(self, speed_ratio: float) -> str:
        """Convert speed multiplier (e.g. 1.05) to Edge TTS rate string (e.g. '+5%')."""
        pct = int(round((speed_ratio - 1.0) * 100))
        return f"{pct:+d}%"

    def _format_pitch(self, pitch_semitones: float) -> str:
        """Convert pitch semitones to Edge TTS pitch string (e.g. '+2Hz')."""
        hz = int(round(pitch_semitones * 2))
        return f"{hz:+d}Hz"

    async def generate_speech(
        self,
        text: str,
        voice_id: str,
        speed_ratio: float = 1.0,
        pitch_semitones: float = 0.0,
        output_format: str = "mp3",
    ) -> GeneratedAudioResult:
        if not HAS_EDGE_TTS:
            raise VoiceProviderError("edge-tts is not installed.")

        rate_str = self._format_rate(speed_ratio)
        pitch_str = self._format_pitch(pitch_semitones)

        logger.info(f"Synthesizing speech via EdgeTTS: voice='{voice_id}', rate='{rate_str}', pitch='{pitch_str}'")

        try:
            communicate = edge_tts.Communicate(
                text=text,
                voice=voice_id,
                rate=rate_str,
                pitch=pitch_str,
            )

            audio_buffer = bytearray()
            word_timestamps: List[WordTimestamp] = []

            async for event in communicate.stream():
                event_type = event.get("type")
                if event_type == "audio":
                    data = event.get("data")
                    if data:
                        audio_buffer.extend(data)
                elif event_type == "WordBoundary":
                    # Offset and duration in microseconds (or 100ns depending on edge_tts version)
                    # Standard edge_tts provides offset/duration in 100ns units (ticks) or microseconds
                    offset = event.get("offset", 0) / 10_000_000.0  # Convert 100ns ticks to seconds
                    duration = event.get("duration", 0) / 10_000_000.0
                    word = event.get("text", "")
                    word_timestamps.append(
                        WordTimestamp(
                            word=word,
                            start=round(offset, 3),
                            end=round(offset + duration, 3),
                        )
                    )

            if not audio_buffer:
                raise VoiceSynthesisError("Edge TTS generated 0 bytes of audio.")

            # Calculate duration from word timestamps or fallback to estimate
            if word_timestamps:
                duration_seconds = max(w.end for w in word_timestamps)
            else:
                words_count = len(text.split())
                duration_seconds = max(0.5, (words_count / (140.0 * speed_ratio)) * 60.0)

            return GeneratedAudioResult(
                audio_bytes=bytes(audio_buffer),
                file_format="mp3",
                sample_rate=24000,
                channels=1,
                duration_seconds=round(duration_seconds, 3),
                word_timestamps=word_timestamps,
                loudness_lufs=-14.0,
                file_size_bytes=len(audio_buffer),
            )

        except Exception as exc:
            logger.error(f"Edge TTS synthesis error for voice {voice_id}: {exc}")
            raise VoiceSynthesisError(f"Edge TTS speech synthesis failed: {str(exc)}") from exc

    async def preview_voice(
        self,
        voice_id: str,
        sample_text: Optional[str] = None,
    ) -> GeneratedAudioResult:
        preview_text = sample_text or "Hello! This is a preview of the Creator Studio AI voice synthesis engine."
        return await self.generate_speech(
            text=preview_text,
            voice_id=voice_id,
            speed_ratio=1.0,
        )

    def get_capabilities(self) -> VoiceProviderCapabilities:
        return VoiceProviderCapabilities(
            provider_name="edge-tts",
            supported_formats=["mp3", "wav"],
            supports_rate_adjustment=True,
            supports_pitch_adjustment=True,
            supports_word_timestamps=True,
            supports_multilingual=True,
            is_local=False,
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
