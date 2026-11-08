"""Deterministic Audio Quality Evaluation Service."""

from typing import Any, Dict, List, Optional
from app.core.logging import logger
from app.services.audio_processing import AudioProcessingService


class AudioQualityService:
    """Evaluates technical voiceover quality, duration compliance, and integrity."""

    @staticmethod
    def evaluate_narration_quality(
        master_wav_bytes: bytes,
        script_word_count: int,
        scene_count: int,
        chunk_count: int,
        expected_duration_seconds: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Run deterministic multi-point audio QA audit on the master narration track."""
        checks: Dict[str, Any] = {}
        warnings: List[str] = []
        failures: List[str] = []

        # 1. Integrity Check
        is_valid_file = AudioProcessingService.check_audio_integrity(master_wav_bytes)
        checks["file_integrity_passed"] = is_valid_file
        if not is_valid_file:
            failures.append("Corrupted or empty master audio file.")

        # 2. Extract Technical Parameters
        try:
            meta = AudioProcessingService.get_wav_metadata(master_wav_bytes)
            actual_duration = meta.duration_seconds
            sample_rate = meta.sample_rate
            channels = meta.channels
        except Exception as exc:
            failures.append(f"Could not extract audio metadata: {str(exc)}")
            actual_duration = 0.0
            sample_rate = 0
            channels = 0

        checks["sample_rate_hz"] = sample_rate
        checks["channels"] = channels
        checks["duration_seconds"] = actual_duration

        if sample_rate < 22050:
            warnings.append(f"Sample rate {sample_rate} Hz is below broadcast benchmark of 24000 Hz.")

        # 3. Completeness Check
        checks["scene_count"] = scene_count
        checks["chunk_count"] = chunk_count
        if chunk_count < scene_count:
            failures.append(f"Incomplete audio: only {chunk_count} of {scene_count} scenes have audio chunks.")
        checks["completeness_passed"] = chunk_count >= scene_count

        # 4. Spoken Duration vs Script Word Count (140 WPM benchmark)
        estimated_duration = expected_duration_seconds or max(5.0, (script_word_count / 140.0) * 60.0)
        checks["estimated_duration_seconds"] = round(estimated_duration, 2)

        if estimated_duration > 0 and actual_duration > 0:
            duration_ratio = actual_duration / estimated_duration
            checks["duration_ratio"] = round(duration_ratio, 3)
            # Duration should be within 60% to 150% of expected duration
            if duration_ratio < 0.60:
                warnings.append(f"Narration duration ({actual_duration:.1f}s) is significantly shorter than estimated ({estimated_duration:.1f}s).")
            elif duration_ratio > 1.50:
                warnings.append(f"Narration duration ({actual_duration:.1f}s) exceeds estimated duration ({estimated_duration:.1f}s).")
        else:
            checks["duration_ratio"] = 1.0

        # 5. Loudness & Silence Verification
        rms_dbfs = AudioProcessingService.calculate_rms_dbfs(master_wav_bytes)
        estimated_lufs = AudioProcessingService.estimate_loudness_lufs(master_wav_bytes)
        checks["rms_dbfs"] = rms_dbfs
        checks["estimated_loudness_lufs"] = estimated_lufs

        if rms_dbfs <= -55.0:
            failures.append(f"Audio track is effectively silent (RMS: {rms_dbfs:.1f} dBFS).")
        elif rms_dbfs >= -1.0:
            warnings.append(f"Audio signal is near clipping threshold (RMS: {rms_dbfs:.1f} dBFS).")

        # YouTube target is -14 LUFS (+/- 4 LUFS tolerance)
        if estimated_lufs < -24.0:
            warnings.append(f"Loudness ({estimated_lufs:.1f} LUFS) is below YouTube target of -14 LUFS.")
        elif estimated_lufs > -9.0:
            warnings.append(f"Loudness ({estimated_lufs:.1f} LUFS) is louder than YouTube target of -14 LUFS.")

        # Determine Final Quality Status
        if failures:
            quality_status = "FAILED"
        elif warnings:
            quality_status = "WARNING"
        else:
            quality_status = "PASSED"

        logger.info(f"Audio QA Result: {quality_status} ({len(warnings)} warnings, {len(failures)} failures)")

        return {
            "quality_status": quality_status,
            "overall_score": 100.0 - (len(failures) * 40.0) - (len(warnings) * 15.0),
            "checks": checks,
            "warnings": warnings,
            "failures": failures,
        }
