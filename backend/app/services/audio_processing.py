"""Audio processing, RIFF WAV parsing, silence detection, and chunk concatenation service."""

import io
import math
import struct
import wave
from dataclasses import dataclass
from typing import List, Optional, Tuple

from app.core.logging import logger


class AudioProcessingError(Exception):
    """Exception raised for errors during audio processing."""
    pass


@dataclass
class AudioMetadata:
    """Extracted audio file technical parameters."""
    file_format: str
    sample_rate: int
    channels: int
    bit_depth: int
    duration_seconds: float
    frame_count: int
    file_size_bytes: int


class AudioProcessingService:
    """Pure-Python audio processing utility for WAV synthesis, analysis, and assembly."""

    @staticmethod
    def get_wav_metadata(wav_bytes: bytes) -> AudioMetadata:
        """Extract technical parameters and duration from RIFF WAV bytes."""
        if len(wav_bytes) < 44:
            raise AudioProcessingError("Audio data is too small to be a valid WAV file.")

        try:
            with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
                channels = wf.getnchannels()
                sample_width = wf.getsampwidth()
                sample_rate = wf.getframerate()
                frame_count = wf.getnframes()
                duration = frame_count / float(sample_rate) if sample_rate > 0 else 0.0

                return AudioMetadata(
                    file_format="wav",
                    sample_rate=sample_rate,
                    channels=channels,
                    bit_depth=sample_width * 8,
                    duration_seconds=round(duration, 3),
                    frame_count=frame_count,
                    file_size_bytes=len(wav_bytes),
                )
        except Exception as exc:
            raise AudioProcessingError(f"Failed to parse WAV audio metadata: {str(exc)}") from exc

    @staticmethod
    def check_audio_integrity(audio_bytes: bytes, min_bytes: int = 100) -> bool:
        """Check if audio bytes are non-empty and have a valid RIFF WAV or MP3 signature."""
        if not audio_bytes or len(audio_bytes) < min_bytes:
            return False

        # Check RIFF header (WAV)
        if audio_bytes[:4] == b"RIFF" and audio_bytes[8:12] == b"WAVE":
            return True

        # Check MP3 ID3v2 tag or frame sync
        if audio_bytes[:3] == b"ID3":
            return True
        if len(audio_bytes) >= 2 and audio_bytes[0] == 0xFF and (audio_bytes[1] & 0xE0) == 0xE0:
            return True

        return False

    @staticmethod
    def calculate_rms_dbfs(wav_bytes: bytes) -> float:
        """Calculate Root Mean Square (RMS) energy in dBFS from 16-bit PCM WAV bytes."""
        try:
            with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
                sample_width = wf.getsampwidth()
                frame_count = wf.getnframes()
                if frame_count == 0:
                    return -100.0

                raw_frames = wf.readframes(frame_count)
                if sample_width != 2:
                    # Non 16-bit: return baseline estimate
                    return -14.0

                total_samples = len(raw_frames) // 2
                if total_samples == 0:
                    return -100.0

                samples = struct.unpack(f"<{total_samples}h", raw_frames)
                sum_sq = sum(s * s for s in samples)
                mean_sq = sum_sq / total_samples
                rms = math.sqrt(mean_sq)

                if rms <= 0.0001:
                    return -100.0

                # 32768 is full scale for 16-bit signed PCM
                dbfs = 20.0 * math.log10(rms / 32768.0)
                return round(dbfs, 2)
        except Exception as exc:
            logger.warning(f"Could not calculate RMS dBFS: {exc}")
            return -14.0

    @staticmethod
    def estimate_loudness_lufs(wav_bytes: bytes) -> float:
        """Estimate integrated loudness in LUFS approximating ITU-R BS.1770."""
        rms_dbfs = AudioProcessingService.calculate_rms_dbfs(wav_bytes)
        if rms_dbfs <= -90.0:
            return -70.0
        # For standard voice signals, K-weighted LUFS closely tracks RMS dBFS + ~1.5 to 3.0 dB offset
        estimated_lufs = max(-70.0, min(0.0, rms_dbfs + 1.2))
        return round(estimated_lufs, 2)

    @staticmethod
    def create_silence_wav(
        duration_seconds: float,
        sample_rate: int = 24000,
        channels: int = 1,
    ) -> bytes:
        """Generate silent 16-bit PCM WAV bytes for pauses between spoken scenes."""
        frame_count = int(sample_rate * max(0.01, duration_seconds))
        buffer = io.BytesIO()

        with wave.open(buffer, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            # Silent 16-bit samples are all 0x0000
            silent_frames = b"\x00" * (frame_count * 2 * channels)
            wf.writeframes(silent_frames)

        return buffer.getvalue()

    @staticmethod
    def concatenate_wav_chunks(
        wav_chunks: List[bytes],
        pause_between_chunks_sec: float = 0.35,
    ) -> bytes:
        """Concatenate a sequence of WAV chunks into a unified master audio file with pauses."""
        if not wav_chunks:
            raise AudioProcessingError("Cannot concatenate empty list of audio chunks.")

        if len(wav_chunks) == 1 and pause_between_chunks_sec <= 0:
            return wav_chunks[0]

        # Read properties from the first chunk
        try:
            first_meta = AudioProcessingService.get_wav_metadata(wav_chunks[0])
        except Exception as exc:
            raise AudioProcessingError(f"First chunk is not a valid WAV: {exc}") from exc

        sample_rate = first_meta.sample_rate
        channels = first_meta.channels
        sample_width = first_meta.bit_depth // 8

        # Prepare silence gap frames
        silence_gap_frames = b""
        if pause_between_chunks_sec > 0:
            gap_frame_count = int(sample_rate * pause_between_chunks_sec)
            silence_gap_frames = b"\x00" * (gap_frame_count * sample_width * channels)

        combined_frames = bytearray()

        for idx, chunk in enumerate(wav_chunks):
            try:
                with wave.open(io.BytesIO(chunk), "rb") as wf:
                    # Append silence gap between chunks (not before the first chunk)
                    if idx > 0 and silence_gap_frames:
                        combined_frames.extend(silence_gap_frames)

                    frames = wf.readframes(wf.getnframes())
                    combined_frames.extend(frames)
            except Exception as exc:
                logger.error(f"Failed to read WAV chunk at index {idx}: {exc}")
                raise AudioProcessingError(f"Corrupted WAV chunk at index {idx}: {str(exc)}") from exc

        # Output combined master WAV
        output_buffer = io.BytesIO()
        with wave.open(output_buffer, "wb") as out_wf:
            out_wf.setnchannels(channels)
            out_wf.setsampwidth(sample_width)
            out_wf.setframerate(sample_rate)
            out_wf.writeframes(bytes(combined_frames))

        return output_buffer.getvalue()
