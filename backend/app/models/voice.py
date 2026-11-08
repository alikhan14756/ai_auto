"""Voiceover, Voice Profile, and Narration Track models."""

from sqlalchemy import Column, String, Text, ForeignKey, Numeric, Integer, BigInteger, Boolean, JSON
from sqlalchemy.types import Uuid
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.models.base import UUIDPrimaryKeyMixin, TimestampMixin


class VoiceProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Configurable voice profile definition linking a channel to a TTS voice."""

    __tablename__ = "voice_profiles"

    channel_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("channels.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    display_name = Column(String(128), nullable=False)
    provider = Column(String(64), nullable=False)  # EDGE_TTS, MOCK, KOKORO
    provider_voice_id = Column(String(128), nullable=False)
    language_code = Column(String(32), default="en-US", nullable=False)
    description = Column(Text, nullable=True)
    gender = Column(String(32), nullable=True)  # MALE, FEMALE, NEUTRAL
    speed_ratio = Column(Numeric(4, 2), default=1.00, nullable=False)
    pitch_semitones = Column(Numeric(4, 2), default=0.00, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    settings = Column(JSON, default=dict, nullable=False)

    # Relationships
    channel = relationship("Channel", back_populates="voice_profiles")
    narration_tracks = relationship("NarrationTrack", back_populates="voice_profile")


class NarrationTrack(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Full assembled master narration audio track for a project."""

    __tablename__ = "narration_tracks"

    project_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("video_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    script_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("scripts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    voice_profile_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("voice_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    script_version = Column(Integer, default=1, nullable=False)
    track_version = Column(Integer, default=1, nullable=False)
    audio_storage_path = Column(Text, nullable=False)
    file_format = Column(String(16), default="wav", nullable=False)  # wav, mp3
    sample_rate = Column(Integer, default=24000, nullable=False)
    channels = Column(Integer, default=1, nullable=False)
    duration_seconds = Column(Numeric(8, 3), nullable=False)
    file_size_bytes = Column(BigInteger, default=0, nullable=False)
    loudness_lufs = Column(Numeric(5, 2), nullable=True)
    is_approved = Column(Boolean, default=False, nullable=False)
    status = Column(String(32), default="READY", nullable=False)  # PENDING, GENERATING, STITCHING, READY, FAILED, OUTDATED
    quality_status = Column(String(32), default="PASSED", nullable=False)  # PASSED, WARNING, FAILED, NEEDS_REVIEW
    quality_report = Column(JSON, default=dict, nullable=False)

    # Relationships
    project = relationship("VideoProject", back_populates="narration_tracks")
    script = relationship("Script")
    voice_profile = relationship("VoiceProfile", back_populates="narration_tracks")
    voiceovers = relationship("Voiceover", back_populates="narration_track", cascade="all, delete-orphan")


class Voiceover(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Synthesized speech audio file and word-level alignment data for a specific scene chunk."""

    __tablename__ = "voiceovers"

    scene_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("scenes.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    project_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("video_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    narration_track_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("narration_tracks.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    chunk_index = Column(Integer, default=1, nullable=False)
    status = Column(String(32), default="GENERATED", nullable=False)  # PENDING, GENERATED, FAILED
    tts_engine = Column(String(64), nullable=False)  # EDGE_TTS, MOCK, KOKORO_LOCAL, PIPER
    voice_id = Column(String(128), nullable=False)
    audio_storage_path = Column(Text, nullable=False)
    duration_seconds = Column(Numeric(6, 3), nullable=False)
    word_timestamps = Column(JSON, nullable=False)  # [{ word, start, end }]
    loudness_lufs = Column(Numeric(4, 2), nullable=False)

    # Relationships
    scene = relationship("Scene", back_populates="voiceover")
    project = relationship("VideoProject", back_populates="voiceovers")
    narration_track = relationship("NarrationTrack", back_populates="voiceovers")
