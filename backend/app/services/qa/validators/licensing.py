"""Copyright and commercial licensing QA validator."""

import time
from typing import List
from app.services.qa.constants import QACategory, QASeverity, QACheckStatus
from app.services.qa.models import CheckResult, CheckFindingSpec, QAExecutionContext
from app.services.qa.validators.base import BaseQAValidator

APPROVED_COMMERCIAL_LICENSES = {
    "COMMERCIAL_USE_ALLOWED",
    "CC0",
    "PUBLIC_DOMAIN",
    "AI_GENERATED",
    "UNSPLASH_LICENSE",
    "PEXELS_LICENSE",
    "PERMISSIVE",
}


class CopyrightLicensingValidator(BaseQAValidator):
    category = QACategory.COPYRIGHT_LICENSING.value

    async def validate(self, context: QAExecutionContext) -> List[CheckResult]:
        results: List[CheckResult] = []
        t0 = time.time()
        findings: List[CheckFindingSpec] = []

        total_assets = len(context.media_assets)
        unverified_licenses = 0
        restricted_licenses = 0

        for asset in context.media_assets:
            lic = (getattr(asset, "license_type", "") or "UNKNOWN").upper()
            asset_title = getattr(asset, "title", "Asset") or "Asset"

            if lic in ["NON_COMMERCIAL_ONLY", "PROHIBITED"]:
                restricted_licenses += 1
                findings.append(
                    CheckFindingSpec(
                        category=self.category,
                        severity=QASeverity.CRITICAL.value,
                        affected_artifact=f"asset_{getattr(asset, 'id', '')}",
                        title=f"Non-Commercial Asset Prohibited: '{asset_title}'",
                        explanation=f"Media asset has license '{lic}' which prohibits YouTube monetization or commercial broadcast.",
                        evidence={"asset_id": str(getattr(asset, "id", "")), "license": lic},
                        recommended_correction="Replace asset with CC0, AI-generated, or verified commercial stock media.",
                        requires_human_review=True,
                    )
                )
            elif lic in ["LICENSE_REVIEW_REQUIRED", "UNKNOWN"]:
                unverified_licenses += 1
                findings.append(
                    CheckFindingSpec(
                        category=self.category,
                        severity=QASeverity.HIGH.value,
                        affected_artifact=f"asset_{getattr(asset, 'id', '')}",
                        title=f"Unverified Media License: '{asset_title}'",
                        explanation=f"Asset license status is '{lic}'. Provenance must be audited before publication.",
                        evidence={"asset_id": str(getattr(asset, "id", "")), "license": lic},
                        recommended_correction="Confirm commercial license entitlement or regenerate with AI.",
                    )
                )

        score = 100.0
        if restricted_licenses > 0:
            score = 0.0
        elif unverified_licenses > 0:
            score = max(30.0, 100.0 - (unverified_licenses * 25.0))

        status = QACheckStatus.PASSED.value
        if restricted_licenses > 0 or score < 60.0:
            status = QACheckStatus.FAILED.value
        elif unverified_licenses > 0:
            status = QACheckStatus.WARNING.value

        results.append(
            self.create_result(
                check_name="commercial_licensing_audit",
                status=status,
                score=score,
                start_time=t0,
                metrics={
                    "total_assets": total_assets,
                    "restricted_licenses": restricted_licenses,
                    "unverified_licenses": unverified_licenses,
                },
                findings=findings,
            )
        )

        return results
