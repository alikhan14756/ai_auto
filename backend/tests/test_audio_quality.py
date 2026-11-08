"""Unit tests for Audio Quality Evaluation Service."""

import pytest
from app.providers.voice.mock import create_synthetic_wav_bytes
from app.services.audio_processing import AudioProcessingService
from app.services.audio_quality import AudioQualityService


def test_audio_quality_pass():
    # 5.0 seconds audio for 12 words (~140 WPM gives ~5.1s)
    wav_bytes = create_synthetic_wav_bytes(duration_seconds=5.0, sample_rate=24000, volume=0.3)
    eval_result = AudioQualityService.evaluate_narration_quality(
        master_wav_bytes=wav_bytes,
        script_word_count=12,
        scene_count=3,
        chunk_count=3,
        expected_duration_seconds=5.1,
    )

    assert eval_result["quality_status"] in ("PASSED", "WARNING")
    assert eval_result["checks"]["file_integrity_passed"] is True
    assert eval_result["checks"]["completeness_passed"] is True
    assert len(eval_result["failures"]) == 0


def test_audio_quality_silent_failure():
    silent_bytes = AudioProcessingService.create_silence_wav(duration_seconds=3.0, sample_rate=24000)
    eval_result = AudioQualityService.evaluate_narration_quality(
        master_wav_bytes=silent_bytes,
        script_word_count=15,
        scene_count=2,
        chunk_count=2,
    )

    assert eval_result["quality_status"] == "FAILED"
    assert any("silent" in f.lower() for f in eval_result["failures"])


def test_audio_quality_incomplete_chunks_failure():
    wav_bytes = create_synthetic_wav_bytes(duration_seconds=3.0, sample_rate=24000)
    eval_result = AudioQualityService.evaluate_narration_quality(
        master_wav_bytes=wav_bytes,
        script_word_count=10,
        scene_count=4,
        chunk_count=2,  # Missing 2 chunks
    )

    assert eval_result["quality_status"] == "FAILED"
    assert eval_result["checks"]["completeness_passed"] is False
    assert any("incomplete" in f.lower() for f in eval_result["failures"])
