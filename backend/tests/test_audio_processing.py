"""Unit tests for Audio Processing, WAV parsing, and chunk concatenation."""

import pytest
from app.providers.voice.mock import create_synthetic_wav_bytes
from app.services.audio_processing import AudioProcessingError, AudioProcessingService


def test_wav_metadata_extraction():
    wav_bytes = create_synthetic_wav_bytes(duration_seconds=2.5, sample_rate=24000)
    meta = AudioProcessingService.get_wav_metadata(wav_bytes)

    assert meta.file_format == "wav"
    assert meta.sample_rate == 24000
    assert meta.channels == 1
    assert meta.bit_depth == 16
    assert abs(meta.duration_seconds - 2.5) < 0.05
    assert meta.file_size_bytes == len(wav_bytes)


def test_audio_integrity_check():
    valid_wav = create_synthetic_wav_bytes(duration_seconds=1.0)
    assert AudioProcessingService.check_audio_integrity(valid_wav) is True

    # Corrupt data
    assert AudioProcessingService.check_audio_integrity(b"") is False
    assert AudioProcessingService.check_audio_integrity(b"random bytes not an audio file") is False


def test_silence_detection_and_rms():
    # Audible sine wave
    audible_wav = create_synthetic_wav_bytes(duration_seconds=1.0, volume=0.5)
    rms_audible = AudioProcessingService.calculate_rms_dbfs(audible_wav)
    assert rms_audible > -30.0  # Clear audible signal

    # Silent audio
    silent_wav = AudioProcessingService.create_silence_wav(duration_seconds=1.0, sample_rate=24000)
    rms_silent = AudioProcessingService.calculate_rms_dbfs(silent_wav)
    assert rms_silent <= -90.0  # Silent baseline


def test_concatenate_wav_chunks_with_pause():
    chunk1 = create_synthetic_wav_bytes(duration_seconds=1.0, sample_rate=24000)
    chunk2 = create_synthetic_wav_bytes(duration_seconds=1.5, sample_rate=24000)
    chunk3 = create_synthetic_wav_bytes(duration_seconds=2.0, sample_rate=24000)

    # 3 chunks with 0.5s pause between them: total = 1.0 + 1.5 + 2.0 + (2 * 0.5) = 5.5s
    master_wav = AudioProcessingService.concatenate_wav_chunks(
        [chunk1, chunk2, chunk3],
        pause_between_chunks_sec=0.5,
    )

    meta = AudioProcessingService.get_wav_metadata(master_wav)
    assert meta.sample_rate == 24000
    assert meta.channels == 1
    assert abs(meta.duration_seconds - 5.5) < 0.1


def test_concatenate_empty_chunks_raises():
    with pytest.raises(AudioProcessingError):
        AudioProcessingService.concatenate_wav_chunks([])
