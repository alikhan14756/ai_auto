"""Factual accuracy and claim verification QA validator."""

import time
from typing import List
from app.services.qa.constants import QACategory, QASeverity, QACheckStatus
from app.services.qa.models import CheckResult, CheckFindingSpec, QAExecutionContext
from app.services.qa.validators.base import BaseQAValidator


class FactualAccuracyValidator(BaseQAValidator):
    category = QACategory.FACTUAL_ACCURACY.value

    async def validate(self, context: QAExecutionContext) -> List[CheckResult]:
        results: List[CheckResult] = []

        # Check 1: Script Claims Verification
        t0 = time.time()
        findings: List[CheckFindingSpec] = []
        total_claims = len(context.script_claims)
        unverified_count = 0
        contradicted_count = 0
        low_confidence_count = 0

        for claim in context.script_claims:
            v_status = getattr(claim, "verification_status", "UNVERIFIED")
            conf = float(getattr(claim, "confidence_score", 0.0) or 0.0)
            text = getattr(claim, "claim_text", "")

            if v_status == "CONTRADICTED":
                contradicted_count += 1
                findings.append(
                    CheckFindingSpec(
                        category=self.category,
                        severity=QASeverity.CRITICAL.value,
                        affected_artifact="script_claim",
                        title=f"Contradicted Fact Detected: '{text[:60]}...'",
                        explanation=f"Script claim was flagged as contradicted by research evidence with confidence {conf:.2f}.",
                        evidence={"claim_id": str(getattr(claim, "id", "")), "claim_text": text, "status": v_status, "confidence": conf},
                        recommended_correction="Remove or rewrite the contradicted assertion with verified factual evidence.",
                        requires_human_review=True,
                    )
                )
            elif v_status == "UNVERIFIED":
                unverified_count += 1
                findings.append(
                    CheckFindingSpec(
                        category=self.category,
                        severity=QASeverity.HIGH.value,
                        affected_artifact="script_claim",
                        title=f"Unverified Claim: '{text[:60]}...'",
                        explanation="Factual assertion lacks verified citations or reputable research source grounding.",
                        evidence={"claim_id": str(getattr(claim, "id", "")), "claim_text": text, "status": v_status},
                        recommended_correction="Attach authoritative source citations or qualify the assertion as hypothetical/opinion.",
                        requires_human_review=True,
                    )
                )
            elif conf < 0.70:
                low_confidence_count += 1
                findings.append(
                    CheckFindingSpec(
                        category=self.category,
                        severity=QASeverity.MEDIUM.value,
                        affected_artifact="script_claim",
                        title=f"Low Confidence Citation: '{text[:60]}...'",
                        explanation=f"Claim confidence score is below threshold ({conf:.2f} < 0.70).",
                        evidence={"claim_id": str(getattr(claim, "id", "")), "confidence": conf},
                        recommended_correction="Cross-reference with a second independent source to strengthen citation confidence.",
                        requires_human_review=False,
                    )
                )

        score = 100.0
        if contradicted_count > 0:
            score = 0.0
            status = QACheckStatus.FAILED.value
        elif unverified_count > 0:
            score = max(20.0, 100.0 - (unverified_count * 25.0))
            status = QACheckStatus.FAILED.value if score < 60.0 else QACheckStatus.WARNING.value
        elif low_confidence_count > 0:
            score = max(50.0, 100.0 - (low_confidence_count * 10.0))
            status = QACheckStatus.WARNING.value
        else:
            status = QACheckStatus.PASSED.value

        results.append(
            self.create_result(
                check_name="claim_verification_audit",
                status=status,
                score=score,
                start_time=t0,
                metrics={
                    "total_claims": total_claims,
                    "contradicted_count": contradicted_count,
                    "unverified_count": unverified_count,
                    "low_confidence_count": low_confidence_count,
                },
                findings=findings,
            )
        )

        return results
