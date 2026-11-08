"""Thumbnail dimensions, size, and layout QA validator."""

import os
import time
from typing import List
from app.services.qa.constants import (
    QACategory,
    QASeverity,
    QACheckStatus,
    THUMBNAIL_REQUIRED_WIDTH,
    THUMBNAIL_REQUIRED_HEIGHT,
    MAX_THUMBNAIL_SIZE_BYTES,
)
from app.services.qa.models import CheckResult, CheckFindingSpec, QAExecutionContext
from app.services.qa.validators.base import BaseQAValidator


class ThumbnailQualityValidator(BaseQAValidator):
    category = QACategory.THUMBNAIL_QUALITY.value

    async def validate(self, context: QAExecutionContext) -> List[CheckResult]:
        results: List[CheckResult] = []
        t0 = time.time()
        findings: List[CheckFindingSpec] = []

        thumbnail = context.thumbnail
        thumb_path = context.thumbnail_path or (getattr(thumbnail, "storage_path", None) if thumbnail else None)

        if not thumbnail and not thumb_path:
            results.append(
                self.create_result(
                    check_name="thumbnail_spec_audit",
                    status=QACheckStatus.FAILED.value,
                    score=0.0,
                    start_time=t0,
                    findings=[
                        CheckFindingSpec(
                            category=self.category,
                            severity=QASeverity.CRITICAL.value,
                            affected_artifact="thumbnail",
                            title="Missing Selected Thumbnail",
                            explanation="No thumbnail has been generated or selected for this publication package.",
                            recommended_correction="Generate and select an approved thumbnail variant in Thumbnail Studio.",
                            requires_human_review=True,
                        )
                    ],
                )
            )
            return results

        # File presence & size
        file_size_bytes = 0
        if thumb_path:
            if not os.path.exists(thumb_path):
                findings.append(
                    CheckFindingSpec(
                        category=self.category,
                        severity=QASeverity.CRITICAL.value,
                        affected_artifact="thumbnail_file",
                        title="Thumbnail Image File Not Found on Disk",
                        explanation=f"Thumbnail at path '{thumb_path}' is missing.",
                        evidence={"path": thumb_path},
                        recommended_correction="Re-compose thumbnail graphic in Thumbnail Studio.",
                        requires_human_review=True,
                    )
                )
            else:
                file_size_bytes = os.path.getsize(thumb_path)
                if file_size_bytes > MAX_THUMBNAIL_SIZE_BYTES:
                    findings.append(
                        CheckFindingSpec(
                            category=self.category,
                            severity=QASeverity.HIGH.value,
                            affected_artifact="thumbnail_file",
                            title=f"Thumbnail File Size Exceeds Limit ({file_size_bytes / (1024*1024):.2f} MB)",
                            explanation=f"YouTube strictly rejects thumbnails over 2.0 MB ({MAX_THUMBNAIL_SIZE_BYTES} bytes).",
                            evidence={"size_bytes": file_size_bytes, "max_allowed": MAX_THUMBNAIL_SIZE_BYTES},
                            recommended_correction="Compress thumbnail image or lower JPEG quality.",
                        )
                    )

        # Dimensions check
        width = int(getattr(thumbnail, "width", THUMBNAIL_REQUIRED_WIDTH) or THUMBNAIL_REQUIRED_WIDTH)
        height = int(getattr(thumbnail, "height", THUMBNAIL_REQUIRED_HEIGHT) or THUMBNAIL_REQUIRED_HEIGHT)

        if width != THUMBNAIL_REQUIRED_WIDTH or height != THUMBNAIL_REQUIRED_HEIGHT:
            findings.append(
                CheckFindingSpec(
                    category=self.category,
                    severity=QASeverity.HIGH.value,
                    affected_artifact="thumbnail",
                    title=f"Invalid Thumbnail Dimensions ({width}x{height})",
                    explanation=f"Expected {THUMBNAIL_REQUIRED_WIDTH}x{THUMBNAIL_REQUIRED_HEIGHT} (16:9).",
                    evidence={"width": width, "height": height, "expected": f"{THUMBNAIL_REQUIRED_WIDTH}x{THUMBNAIL_REQUIRED_HEIGHT}"},
                    recommended_correction="Resize thumbnail canvas to standard 1280x720 resolution.",
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

        status = QACheckStatus.PASSED.value
        if score < 60.0 or any(f.severity == QASeverity.CRITICAL.value for f in findings):
            status = QACheckStatus.FAILED.value
        elif score < 95.0:
            status = QACheckStatus.WARNING.value

        results.append(
            self.create_result(
                check_name="thumbnail_spec_audit",
                status=status,
                score=score,
                start_time=t0,
                metrics={
                    "width": width,
                    "height": height,
                    "file_size_bytes": file_size_bytes,
                },
                findings=findings,
            )
        )

        return results
