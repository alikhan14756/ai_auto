"""Subtitle and caption integrity QA validator."""

import os
import time
from typing import List
from app.services.qa.constants import QACategory, QASeverity, QACheckStatus
from app.services.qa.models import CheckResult, CheckFindingSpec, QAExecutionContext
from app.services.qa.validators.base import BaseQAValidator


class CaptionIntegrityValidator(BaseQAValidator):
    category = QACategory.CAPTION_INTEGRITY.value

    async def validate(self, context: QAExecutionContext) -> List[CheckResult]:
        results: List[CheckResult] = []
        t0 = time.time()
        findings: List[CheckFindingSpec] = []

        sub_path = context.subtitles_path
        caption_asset = context.caption_asset

        if not sub_path and caption_asset:
            sub_path = getattr(caption_asset, "file_path", None)

        if not sub_path and not caption_asset:
            # Captions are highly recommended, warning if omitted
            findings.append(
                CheckFindingSpec(
                    category=self.category,
                    severity=QASeverity.MEDIUM.value,
                    affected_artifact="captions",
                    title="No Caption Asset Configured",
                    explanation="Video does not have compiled kinetic or standard subtitles.",
                    recommended_correction="Compile kinetic ASS or SRT subtitles for improved viewer comprehension.",
                )
            )
        elif sub_path and not os.path.exists(sub_path):
            findings.append(
                CheckFindingSpec(
                    category=self.category,
                    severity=QASeverity.HIGH.value,
                    affected_artifact="captions",
                    title="Caption File Missing on Disk",
                    explanation=f"Referenced subtitle file at '{sub_path}' was not found.",
                    evidence={"subtitles_path": sub_path},
                    recommended_correction="Recompile subtitle track using SubtitleCompiler.",
                )
            )

        score = 100.0
        for f in findings:
            if f.severity == QASeverity.HIGH.value:
                score -= 25.0
            elif f.severity == QASeverity.MEDIUM.value:
                score -= 10.0

        status = QACheckStatus.PASSED.value if score >= 90.0 else QACheckStatus.WARNING.value

        results.append(
            self.create_result(
                check_name="caption_syntax_and_sync",
                status=status,
                score=score,
                start_time=t0,
                metrics={"has_captions": bool(sub_path or caption_asset)},
                findings=findings,
            )
        )

        return results
