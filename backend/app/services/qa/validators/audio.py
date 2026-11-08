"""Narration and audio technical quality QA validator."""

import os
import time
from typing import List
from app.services.qa.constants import (
    QACategory,
    QASeverity,
    QACheckStatus,
    MAX_AUDIO_SILENCE_DURATION_SEC,
    MAX_AUDIO_TRUE_PEAK_DBTP,
    TARGET_INTEGRATED_LUFS,
    LUFS_TOLERANCE,
)
from app.services.qa.models import CheckResult, CheckFindingSpec, QAExecutionContext
from app.services.qa.validators.base import BaseQAValidator


class AudioQualityValidator(BaseQAValidator):
    category = QACategory.NARRATION_AUDIO.value

    async def validate(self, context: QAExecutionContext) -> List[CheckResult]:
        results: List[CheckResult] = []
        t0 = time.time()
        findings: List[CheckFindingSpec] = []

        track = context.narration_track
        audio_path = context.audio_path or (getattr(track, "audio_file_path", None) if track else None)

        if not track and not audio_path:
            results.append(
                self.create_result(
                    check_name="audio_master_integrity",
                    status=QACheckStatus.FAILED.value,
                    score=0.0,
                    start_time=t0,
                    findings=[
                        CheckFindingSpec(
                            category=self.category,
                            severity=QASeverity.CRITICAL.value,
                            affected_artifact="narration_track",
                            title="Missing Master Narration Track",
                            explanation="Project does not contain an approved voiceover or master narration audio file.",
                            recommended_correction="Generate and master audio voiceover before QA verification.",
                            requires_human_review=True,
                        )
                    ],
                )
            )
            return results

        # Audio file existence check
        if audio_path and not os.path.exists(audio_path):
            findings.append(
                CheckFindingSpec(
                    category=self.category,
                    severity=QASeverity.CRITICAL.value,
                    affected_artifact="audio_file",
                    title="Audio Master File Unreachable on Disk",
                    explanation=f"Audio file at path '{audio_path}' could not be located.",
                    evidence={"path": audio_path},
                    recommended_correction="Verify storage volume and regenerate narration master audio.",
                    requires_human_review=True,
                )
            )

        # Inspect metrics stored on narration track or direct audio file
        metrics = getattr(track, "qa_metrics", {}) or {}
        has_measured_metrics = bool(metrics or getattr(track, "integrated_lufs", None))

        if not has_measured_metrics and audio_path and os.path.exists(audio_path):
            try:
                with open(audio_path, "rb") as af:
                    content_bytes = af.read()
                from app.services.audio_processing import AudioProcessingService
                meta = AudioProcessingService.get_wav_metadata(content_bytes)
                if meta.sample_rate < MIN_AUDIO_SAMPLE_RATE_HZ:
                    findings.append(
                        CheckFindingSpec(
                            category=self.category,
                            severity=QASeverity.HIGH.value,
                            affected_artifact="audio_file",
                            title=f"Substandard Audio Sample Rate ({meta.sample_rate} Hz)",
                            explanation=f"Sample rate is below {MIN_AUDIO_SAMPLE_RATE_HZ} Hz broadcast requirement.",
                            evidence={"sample_rate": meta.sample_rate},
                            recommended_correction="Export voiceover at 44.1 kHz or 48.0 kHz 16-bit WAV.",
                        )
                    )
            except Exception:
                pass

            findings.append(
                CheckFindingSpec(
                    category=self.category,
                    severity=QASeverity.MEDIUM.value,
                    affected_artifact="narration_track",
                    title="Audio Loudness Not Calibrated to EBU R128",
                    explanation="Audio master lacks verified integrated loudness measurement (-14 LUFS standard).",
                    recommended_correction="Run AudioProcessingService normalization before publication.",
                )
            )

        integrated_lufs = float(metrics.get("integrated_lufs", getattr(track, "integrated_lufs", -14.0)) or -14.0)
        true_peak_dbtp = float(metrics.get("true_peak_dbtp", getattr(track, "true_peak_dbtp", -1.5)) or -1.5)
        max_silence_s = float(metrics.get("max_silence_duration_s", 0.8) or 0.8)

        # 1. Loudness Check (-14 LUFS +/- 2 LUFS)
        lufs_diff = abs(integrated_lufs - TARGET_INTEGRATED_LUFS)
        if lufs_diff > (LUFS_TOLERANCE * 2):  # > 4 dB difference
            findings.append(
                CheckFindingSpec(
                    category=self.category,
                    severity=QASeverity.HIGH.value,
                    affected_artifact="narration_track",
                    title=f"Severe Audio Loudness Deviation ({integrated_lufs:.1f} LUFS)",
                    explanation=f"Target is {TARGET_INTEGRATED_LUFS} LUFS. Video audio deviates by {lufs_diff:.1f} dB.",
                    evidence={"integrated_lufs": integrated_lufs, "target": TARGET_INTEGRATED_LUFS},
                    recommended_correction="Apply EBU R128 loudness normalization to reach -14 LUFS YouTube standard.",
                )
            )
        elif lufs_diff > LUFS_TOLERANCE:
            findings.append(
                CheckFindingSpec(
                    category=self.category,
                    severity=QASeverity.MEDIUM.value,
                    affected_artifact="narration_track",
                    title=f"Moderate Audio Loudness Deviation ({integrated_lufs:.1f} LUFS)",
                    explanation=f"Audio is slightly outside optimal -14 LUFS +/- {LUFS_TOLERANCE} LUFS tolerance.",
                    evidence={"integrated_lufs": integrated_lufs, "target": TARGET_INTEGRATED_LUFS},
                    recommended_correction="Normalize audio tracks to -14 LUFS for consistent multi-platform volume.",
                )
            )

        # 2. True Peak / Clipping Check
        if true_peak_dbtp > MAX_AUDIO_TRUE_PEAK_DBTP:
            findings.append(
                CheckFindingSpec(
                    category=self.category,
                    severity=QASeverity.HIGH.value,
                    affected_artifact="narration_track",
                    title=f"Audio Clipping Risk Detected ({true_peak_dbtp:.1f} dBTP)",
                    explanation=f"True peak exceeds safe ceiling of {MAX_AUDIO_TRUE_PEAK_DBTP} dBTP, causing digital distortion.",
                    evidence={"true_peak_dbtp": true_peak_dbtp, "max_allowed": MAX_AUDIO_TRUE_PEAK_DBTP},
                    recommended_correction="Apply a true peak limiter set to -1.0 dBTP ceiling.",
                )
            )

        # 3. Excessive Silence Check
        if max_silence_s > MAX_AUDIO_SILENCE_DURATION_SEC:
            findings.append(
                CheckFindingSpec(
                    category=self.category,
                    severity=QASeverity.MEDIUM.value,
                    affected_artifact="narration_track",
                    title=f"Excessive Audio Silence ({max_silence_s:.2f}s)",
                    explanation=f"Continuous silence exceeds {MAX_AUDIO_SILENCE_DURATION_SEC}s, hurting audience retention.",
                    evidence={"max_silence_s": max_silence_s, "threshold": MAX_AUDIO_SILENCE_DURATION_SEC},
                    recommended_correction="Trim dead air pauses in audio mastering pipeline.",
                )
            )

        score = 100.0
        for f in findings:
            if f.severity == QASeverity.CRITICAL.value:
                score = 0.0
            elif f.severity == QASeverity.HIGH.value:
                score -= 25.0
            elif f.severity == QASeverity.MEDIUM.value:
                score -= 10.0
            elif f.severity == QASeverity.LOW.value:
                score -= 3.0

        status = QACheckStatus.PASSED.value
        if score < 60.0 or any(f.severity == QASeverity.CRITICAL.value for f in findings):
            status = QACheckStatus.FAILED.value
        elif score < 95.0:
            status = QACheckStatus.WARNING.value

        results.append(
            self.create_result(
                check_name="audio_technical_standards",
                status=status,
                score=score,
                start_time=t0,
                metrics={
                    "integrated_lufs": integrated_lufs,
                    "true_peak_dbtp": true_peak_dbtp,
                    "max_silence_s": max_silence_s,
                },
                findings=findings,
            )
        )

        return results
