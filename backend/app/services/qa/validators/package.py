"""Publication package completeness and integrity QA validator."""

import time
from typing import List
from app.services.qa.constants import QACategory, QASeverity, QACheckStatus
from app.services.qa.models import CheckResult, CheckFindingSpec, QAExecutionContext
from app.services.qa.validators.base import BaseQAValidator


class PackageCompletenessValidator(BaseQAValidator):
    category = QACategory.PACKAGE_COMPLETENESS.value

    async def validate(self, context: QAExecutionContext) -> List[CheckResult]:
        results: List[CheckResult] = []
        t0 = time.time()
        findings: List[CheckFindingSpec] = []

        missing_components = []

        if not context.render_job:
            missing_components.append("video_render")
            findings.append(
                CheckFindingSpec(
                    category=self.category,
                    severity=QASeverity.CRITICAL.value,
                    affected_artifact="publication_package",
                    title="Package Incomplete: Missing Video Render",
                    explanation="Publication package does not link a completed video render.",
                    recommended_correction="Render project timeline and attach render output to package.",
                    requires_human_review=True,
                )
            )

        if not context.thumbnail:
            missing_components.append("thumbnail")
            findings.append(
                CheckFindingSpec(
                    category=self.category,
                    severity=QASeverity.CRITICAL.value,
                    affected_artifact="publication_package",
                    title="Package Incomplete: Missing Selected Thumbnail",
                    explanation="Publication package does not contain an approved thumbnail variant.",
                    recommended_correction="Select an approved thumbnail variant before publication.",
                    requires_human_review=True,
                )
            )

        if not context.metadata_draft:
            missing_components.append("metadata")
            findings.append(
                CheckFindingSpec(
                    category=self.category,
                    severity=QASeverity.CRITICAL.value,
                    affected_artifact="publication_package",
                    title="Package Incomplete: Missing SEO Metadata Draft",
                    explanation="Publication package requires an approved SEO metadata draft.",
                    recommended_correction="Generate and approve metadata draft in SEO Studio.",
                    requires_human_review=True,
                )
            )

        score = 0.0 if missing_components else 100.0
        status = QACheckStatus.FAILED.value if missing_components else QACheckStatus.PASSED.value

        results.append(
            self.create_result(
                check_name="publication_package_completeness",
                status=status,
                score=score,
                start_time=t0,
                metrics={
                    "missing_components": missing_components,
                    "is_complete": len(missing_components) == 0,
                },
                findings=findings,
            )
        )

        return results
