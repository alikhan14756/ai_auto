"""Abstract Voice Provider Interface and Data Schemas for TTS Engines."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class VoiceProviderError(Exception):
    """Base exception for voice provider operations."""
    pass


class VoiceNotFoundError(VoiceProviderError):
    """Raised when the requested voice ID is not available."""
    pass


class VoiceSynthesisError(VoiceProviderError):
    """Raised when speech synthesis fails."""
    pass


@dataclass
class VoiceInfo:
    """Metadata describing an available voice."""
    voice_id: str
    display_name: str
    provider: str
    language_code: str
    gender: Optional[str] = None
    description: Optional[str] = None
    sample_url: Optional[str] = None
    is_neural: bool = True
    is_free: bool = True


@dataclass
class WordTimestamp:
    """Word-level alignment timestamp for subtitles and kinetic typography."""
    word: str
    start: float  # In seconds
    end: float    # In seconds


@dataclass
class GeneratedAudioResult:
    """Result of speech synthesis containing audio bytes and alignment metadata."""
    audio_bytes: bytes
    file_format: str  # "wav" or "mp3"
    sample_rate: int
    channels: int
    duration_seconds: float
    word_timestamps: List[WordTimestamp] = field(default_factory=list)
    loudness_lufs: Optional[float] = None
    file_size_bytes: int = 0

    def __post_init__(self):
        if not self.file_size_bytes and self.audio_bytes:
            self.file_size_bytes = len(self.audio_bytes)


@dataclass
class VoiceProviderCapabilities:
    """Capabilities and supported parameters of a voice provider."""
    provider_name: str
    supported_formats: List[str]
    supports_rate_adjustment: bool = True
    supports_pitch_adjustment: bool = True
    supports_word_timestamps: bool = True
    supports_multilingual: bool = True
    is_local: bool = False
    requires_api_key: bool = False


@dataclass
class AudioUsageEstimate:
    """Usage and cost estimation for speech synthesis."""
    character_count: int
    word_count: int
    estimated_duration_seconds: float
    estimated_cost_usd: float = 0.00


class VoiceProviderInterface(ABC):
    """Abstract interface for all text-to-speech engines."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique provider identifier (e.g. 'edge-tts', 'mock', 'kokoro')."""
        pass

    @abstractmethod
    async def list_voices(self, language_code: Optional[str] = None) -> List[VoiceInfo]:
        """List available voices optionally filtered by language locale."""
        pass

    @abstractmethod
    async def generate_speech(
        self,
        text: str,
        voice_id: str,
        speed_ratio: float = 1.0,
        pitch_semitones: float = 0.0,
        output_format: str = "wav",
    ) -> GeneratedAudioResult:
        """Synthesize speech audio and return audio bytes with word timestamps."""
        pass

    @abstractmethod
    async def preview_voice(
        self,
        voice_id: str,
        sample_text: Optional[str] = None,
    ) -> GeneratedAudioResult:
        """Generate a short audition preview clip for a given voice."""
        pass

    @abstractmethod
    def get_capabilities(self) -> VoiceProviderCapabilities:
        """Return capabilities and audio parameter limits of the provider."""
        pass

    @abstractmethod
    def estimate_usage(self, text: str) -> AudioUsageEstimate:
        """Estimate spoken duration and monetary cost for input text."""
        pass
