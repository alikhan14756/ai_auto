"""Pydantic Schemas for Voice Profiles, Narration Tracks, and Audio Quality Reports."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class VoiceInfoResponse(BaseModel):
    """API model for available text-to-speech voices."""
    voice_id: str
    display_name: str
    provider: str
    language_code: str
    gender: Optional[str] = None
    description: Optional[str] = None
    is_neural: bool = True
    is_free: bool = True


class VoiceProfileCreate(BaseModel):
    """Payload to create a reusable channel voice profile."""
    channel_id: UUID
    display_name: str = Field(..., max_length=128)
    provider: str = Field(default="edge-tts", max_length=64)
    provider_voice_id: str = Field(..., max_length=128)
    language_code: str = Field(default="en-US", max_length=32)
    description: Optional[str] = None
    gender: Optional[str] = None
    speed_ratio: float = Field(default=1.00, ge=0.5, le=2.0)
    pitch_semitones: float = Field(default=0.00, ge=-12.0, le=12.0)
    is_default: bool = False
    settings: Dict[str, Any] = Field(default_factory=dict)


class VoiceProfileUpdate(BaseModel):
    """Payload to modify voice profile settings."""
    display_name: Optional[str] = None
    speed_ratio: Optional[float] = Field(None, ge=0.5, le=2.0)
    pitch_semitones: Optional[float] = Field(None, ge=-12.0, le=12.0)
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None
    settings: Optional[Dict[str, Any]] = None


class VoiceProfileResponse(BaseModel):
    """API representation of a VoiceProfile."""
    id: UUID
    channel_id: Optional[UUID] = None
    display_name: str
    provider: str
    provider_voice_id: str
    language_code: str
    description: Optional[str] = None
    gender: Optional[str] = None
    speed_ratio: float
    pitch_semitones: float
    is_default: bool
    is_active: bool
    settings: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class VoicePreviewRequest(BaseModel):
    """Payload to audition a voice sample."""
    voice_id: str
    provider: Optional[str] = None
    sample_text: Optional[str] = None
    speed_ratio: Optional[float] = Field(default=1.0, ge=0.5, le=2.0)


class VoicePreviewResponse(BaseModel):
    """Preview synthesis result."""
    voice_id: str
    duration_seconds: float
    file_format: str
    audio_base64: Optional[str] = None


class NarrationGenerateRequest(BaseModel):
    """Payload to request full project narration generation."""
    project_id: UUID
    voice_profile_id: Optional[UUID] = None
    speed_ratio: Optional[float] = Field(None, ge=0.5, le=2.0)
    pitch_semitones: Optional[float] = Field(None, ge=-12.0, le=12.0)


class NarrationSectionRegenerateRequest(BaseModel):
    """Payload to regenerate audio for a specific scene."""
    scene_id: UUID
    speed_ratio: Optional[float] = Field(None, ge=0.5, le=2.0)


class VoiceoverChunkResponse(BaseModel):
    """Individual scene audio chunk with timestamps."""
    id: UUID
    scene_id: UUID
    chunk_index: int
    duration_seconds: float
    word_timestamps: List[Dict[str, Any]]
    loudness_lufs: float
    status: str
    audio_url: Optional[str] = None

    model_config = {"from_attributes": True}


class NarrationTrackResponse(BaseModel):
    """Full master narration audio track view."""
    id: UUID
    project_id: UUID
    script_id: Optional[UUID] = None
    voice_profile_id: Optional[UUID] = None
    voice_profile: Optional[VoiceProfileResponse] = None
    script_version: int
    track_version: int
    file_format: str
    sample_rate: int
    channels: int
    duration_seconds: float
    file_size_bytes: int
    loudness_lufs: Optional[float] = None
    is_approved: bool
    status: str
    quality_status: str
    quality_report: Dict[str, Any]
    audio_url: Optional[str] = None
    voiceovers: List[VoiceoverChunkResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
