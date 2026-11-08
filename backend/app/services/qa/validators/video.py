"""Video technical quality and container verification QA validator."""

import os
import time
from typing import List
from app.services.qa.constants import (
    QACategory,
    QASeverity,
    QACheckStatus,
    MAX_BLACK_FRAME_DURATION_SEC,
    MAX_FREEZE_FRAME_DURATION_SEC,
)
from app.services.qa.models import CheckResult, CheckFindingSpec, QAExecutionContext
from app.services.qa.validators.base import BaseQAValidator


class VideoTechnicalValidator(BaseQAValidator):
    category = QACategory.VIDEO_TECHNICAL.value

    async def validate(self, context: QAExecutionContext) -> List[CheckResult]:
        results: List[CheckResult] = []
        t0 = time.time()
        findings: List[CheckFindingSpec] = []

        render_job = context.render_job
        video_path = context.video_path or (getattr(render_job, "output_video_path", None) if render_job else None)

        if not render_job and not video_path:
            results.append(
                self.create_result(
                    check_name="video_stream_and_container",
                    status=QACheckStatus.FAILED.value,
                    score=0.0,
                    start_time=t0,
                    findings=[
                        CheckFindingSpec(
                            category=self.category,
                            severity=QASeverity.CRITICAL.value,
                            affected_artifact="render_job",
                            title="Missing Completed Video Render",
                            explanation="Project does not contain a completed master video render artifact.",
                            recommended_correction="Trigger FFmpeg video rendering before running publication QA gate.",
                            requires_human_review=True,
                        )
                    ],
                )
            )
            return results

        # Physical file existence check
        file_exists = bool(video_path and os.path.exists(video_path))
        file_size_bytes = os.path.getsize(video_path) if file_exists else 0

        if not file_exists or file_size_bytes == 0:
            findings.append(
                CheckFindingSpec(
                    category=self.category,
                    severity=QASeverity.CRITICAL.value,
                    affected_artifact="video_file",
                    title="Rendered Video File Missing or Empty",
                    explanation=f"Rendered video at path '{video_path}' does not exist or has 0 bytes.",
                    evidence={"path": video_path, "exists": file_exists, "size_bytes": file_size_bytes},
                    recommended_correction="Re-render master video through Video Production pipeline.",
                    requires_human_review=True,
                )
            )

        # Inspect metrics from render job or fallback
        # Check if project has QualityReport metrics from M09
        black_frame_duration = 0.0
        freeze_duration = 0.0
        target_dur = float(getattr(context, "project_format", "") == "SHORTS" and 60.0 or 480.0)

        # Check render job status
        render_status = getattr(render_job, "status", "UNKNOWN")
        if render_status != "COMPLETED":
            findings.append(
                CheckFindingSpec(
                    category=self.category,
                    severity=QASeverity.CRITICAL.value,
                    affected_artifact="render_job",
                    title=f"Render Job Incomplete (Status: {render_status})",
                    explanation=f"Render job did not finish in COMPLETED status.",
                    evidence={"render_status": render_status},
                    recommended_correction="Wait for video render job to reach COMPLETED state or restart render.",
                )
            )

        # Check QualityReport metrics or render_job direct attributes
        q_report = getattr(context, "quality_report", None)
        if not q_report and render_job and hasattr(render_job, "quality_reports"):
            reports = getattr(render_job, "quality_reports", [])
            if reports:
                q_report = reports[0]

        if q_report:
            black_frame_duration = float(getattr(q_report, "black_frame_duration_max", 0.0) or 0.0)
            freeze_duration = float(getattr(q_report, "freeze_duration_max", 0.0) or 0.0)
        elif hasattr(render_job, "black_frame_duration_max"):
            black_frame_duration = float(getattr(render_job, "black_frame_duration_max", 0.0) or 0.0)
            freeze_duration = float(getattr(render_job, "freeze_duration_max", 0.0) or 0.0)
        
        if black_frame_duration > MAX_BLACK_FRAME_DURATION_SEC:
            findings.append(
                CheckFindingSpec(
                    category=self.category,
                    severity=QASeverity.CRITICAL.value,
                    affected_artifact="video_frames",
                    title=f"Black Frame Glitch Detected ({black_frame_duration:.2f}s)",
                    explanation=f"Detected black frames of {black_frame_duration:.2f}s exceeding strict {MAX_BLACK_FRAME_DURATION_SEC}s threshold.",
                    evidence={"black_frame_duration_s": black_frame_duration, "threshold": MAX_BLACK_FRAME_DURATION_SEC},
                    recommended_correction="Check transition timing and ensure all scene visual layers are populated.",
                    requires_human_review=True,
                )
            )

        # Freeze frames check
        if hasattr(render_job, "freeze_duration_max"):
            freeze_duration = float(render_job.freeze_duration_max or 0.0)

        if freeze_duration > MAX_FREEZE_FRAME_DURATION_SEC:
            findings.append(
                CheckFindingSpec(
                    category=self.category,
                    severity=QASeverity.HIGH.value,
                    affected_artifact="video_frames",
                    title=f"Frozen Video Frame Detected ({freeze_duration:.2f}s)",
                    explanation=f"Video display is frozen for {freeze_duration:.2f}s exceeding {MAX_FREEZE_FRAME_DURATION_SEC}s tolerance.",
                    evidence={"freeze_duration_s": freeze_duration, "threshold": MAX_FREEZE_FRAME_DURATION_SEC},
                    recommended_correction="Apply Ken Burns pan/zoom motion to avoid static image freezes.",
                )
            )

        # Compute check score
        score = 100.0
        for f in findings:
            if f.severity == QASeverity.CRITICAL.value:
                score = 0.0
            elif f.severity == QASeverity.HIGH.value:
                score -= 25.0
            elif f.severity == QASeverity.MEDIUM.value:
                score -= 10.0

        status = QACheckStatus.PASSED.value
        if score < 60.0 or any(f.severity == QASeverity.CRITICAL.value for f in findings):
            status = QACheckStatus.FAILED.value
        elif score < 95.0:
            status = QACheckStatus.WARNING.value

        results.append(
            self.create_result(
                check_name="video_technical_integrity",
                status=status,
                score=score,
                start_time=t0,
                metrics={
                    "file_exists": file_exists,
                    "file_size_bytes": file_size_bytes,
                    "black_frame_duration_s": black_frame_duration,
                    "freeze_duration_s": freeze_duration,
                    "render_status": render_status,
                },
                findings=findings,
            )
        )

        return results
