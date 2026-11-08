"""Master QA Orchestrator coordinating all 12 domain validators."""

import time
from typing import Dict, List, Optional, Set
from app.services.qa.constants import QACategory, QASeverity
from app.services.qa.models import (
    CheckResult,
    CheckFindingSpec,
    QAExecutionContext,
)
from app.services.qa.scorer import QAScoringEngine
from app.services.qa.veto import QAVetoGate
from app.services.qa.invalidation import QAInvalidationTracker
from app.services.qa.validators import (
    BaseQAValidator,
    FactualAccuracyValidator,
    ScriptQualityValidator,
    AudioQualityValidator,
    VisualAssetsValidator,
    VideoTechnicalValidator,
    CaptionIntegrityValidator,
    ThumbnailQualityValidator,
    MetadataSEOValidator,
    CopyrightLicensingValidator,
    SecurityPrivacyValidator,
    YouTubePolicyValidator,
    PackageCompletenessValidator,
)


class QAOrchestrator:
    """Coordinates parallel/sequential validator execution, scoring, and veto gating."""

    def __init__(self, validators: Optional[List[BaseQAValidator]] = None):
        self.validators: List[BaseQAValidator] = validators or [
            PackageCompletenessValidator(),
            FactualAccuracyValidator(),
            ScriptQualityValidator(),
            AudioQualityValidator(),
            VisualAssetsValidator(),
            VideoTechnicalValidator(),
            CaptionIntegrityValidator(),
            ThumbnailQualityValidator(),
            MetadataSEOValidator(),
            CopyrightLicensingValidator(),
            SecurityPrivacyValidator(),
            YouTubePolicyValidator(),
        ]

    async def evaluate_context(
        self,
        context: QAExecutionContext,
        target_categories: Optional[Set[str]] = None,
        excepted_finding_ids: Optional[Set[str]] = None,
    ) -> dict:
        """Run validation across target categories, score results, and determine veto gate status."""
        start_time = time.time()
        check_results: List[CheckResult] = []

        # 1. Run Validators
        for validator in self.validators:
            if target_categories and validator.category not in target_categories:
                continue

            try:
                results = await validator.validate(context)
                check_results.extend(results)
            except Exception as e:
                # Catch unexpected validator exception safely
                check_results.append(
                    validator.create_result(
                        check_name=f"{validator.category.lower()}_runtime_check",
                        status="FAILED",
                        score=0.0,
                        start_time=time.time(),
                        error_message=str(e),
                        findings=[
                            CheckFindingSpec(
                                category=validator.category,
                                severity=QASeverity.HIGH.value,
                                affected_artifact="validator_runtime",
                                title=f"Validator Error: {validator.category}",
                                explanation=f"Unexpected error executing {validator.category} validator: {str(e)}",
                                recommended_correction="Audit system logs and check asset configuration.",
                            )
                        ],
                    )
                )

        # 2. Compute Category and Composite Scores
        category_scores, overall_score = QAScoringEngine.calculate_category_scores(check_results)

        # 3. Collect all findings
        all_findings = []
        for cr in check_results:
            for f in cr.findings:
                all_findings.append({
                    "category": f.category,
                    "severity": f.severity,
                    "affected_artifact": f.affected_artifact,
                    "title": f.title,
                    "explanation": f.explanation,
                    "evidence": f.evidence,
                    "recommended_correction": f.recommended_correction,
                    "requires_human_review": f.requires_human_review,
                    "check_name": cr.check_name,
                })

        # 4. Evaluate Veto Gate
        veto_decision, can_publish, veto_breakdown = QAVetoGate.evaluate(
            findings=all_findings,
            excepted_finding_ids=excepted_finding_ids,
            overall_score=overall_score,
        )

        # 5. Compute snapshot state hash
        snapshot = QAInvalidationTracker.compute_context_snapshot(context)

        total_elapsed_ms = int((time.time() - start_time) * 1000)

        return {
            "overall_score": overall_score,
            "veto_decision": veto_decision,
            "can_publish": can_publish,
            "summary": {
                **veto_breakdown,
                "total_checks": len(check_results),
                "total_findings": len(all_findings),
                "execution_time_ms": total_elapsed_ms,
            },
            "category_scores": category_scores,
            "check_results": check_results,
            "findings": all_findings,
            "snapshot": snapshot,
        }
