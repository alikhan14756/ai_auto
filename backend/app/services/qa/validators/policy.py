"""YouTube platform policy, synthetic media disclosure, and risk assessment QA validator."""

import re
import time
from typing import List
from app.services.qa.constants import QACategory, QASeverity, QACheckStatus
from app.services.qa.models import CheckResult, CheckFindingSpec, QAExecutionContext
from app.services.qa.validators.base import BaseQAValidator

DECEPTIVE_PATTERNS = [
    re.compile(r"\b(100% guaranteed|get rich overnight|cure cancer|free bitcoin giveaway)\b", re.I),
    re.compile(r"\b(hack bank account|free credit card generator)\b", re.I),
]


class YouTubePolicyValidator(BaseQAValidator):
    category = QACategory.YOUTUBE_POLICY.value

    async def validate(self, context: QAExecutionContext) -> List[CheckResult]:
        results: List[CheckResult] = []
        t0 = time.time()
        findings: List[CheckFindingSpec] = []

        draft = context.metadata_draft
        synthetic_declared = False

        if draft:
            synthetic_declared = bool(getattr(draft, "synthetic_media_declared", True))
            desc = getattr(draft, "description", "") or ""
            if "synthetic" in desc.lower() or "ai-generated" in desc.lower() or "ai generated" in desc.lower():
                synthetic_declared = True

        if not synthetic_declared:
            findings.append(
                CheckFindingSpec(
                    category=self.category,
                    severity=QASeverity.HIGH.value,
                    affected_artifact="metadata",
                    title="Synthetic Media Disclosure Missing",
                    explanation="YouTube platform rules mandate disclosing realistic synthetic/AI content.",
                    recommended_correction="Enable synthetic media disclosure flag and include AI notice in video description.",
                    requires_human_review=False,
                )
            )

        # Deceptive content scan
        text_corpus = ""
        if draft:
            text_corpus += (getattr(draft, "title", "") or "") + " " + (getattr(draft, "description", "") or "")
        if context.script:
            text_corpus += " " + (getattr(context.script, "content", "") or "")

        for pattern in DECEPTIVE_PATTERNS:
            match = pattern.search(text_corpus)
            if match:
                findings.append(
                    CheckFindingSpec(
                        category=self.category,
                        severity=QASeverity.CRITICAL.value,
                        affected_artifact="metadata_and_script",
                        title=f"Policy Hazard: Flagged Phrasing '{match.group(0)}'",
                        explanation="Detected prohibited claims or scam signals violating YouTube Community Guidelines.",
                        evidence={"matched": match.group(0)},
                        recommended_correction="Remove deceptive claims or prohibited health/financial advice.",
                        requires_human_review=True,
                    )
                )

        score = 100.0
        for f in findings:
            if f.severity == QASeverity.CRITICAL.value:
                score = 0.0
            elif f.severity == QASeverity.HIGH.value:
                score -= 25.0

        status = QACheckStatus.PASSED.value
        if score < 70.0:
            status = QACheckStatus.FAILED.value
        elif score < 95.0:
            status = QACheckStatus.WARNING.value

        results.append(
            self.create_result(
                check_name="youtube_policy_and_compliance",
                status=status,
                score=score,
                start_time=t0,
                metrics={
                    "synthetic_media_declared": synthetic_declared,
                    "policy_hazards_count": len([f for f in findings if f.severity == QASeverity.CRITICAL.value]),
                },
                findings=findings,
            )
        )

        return results
