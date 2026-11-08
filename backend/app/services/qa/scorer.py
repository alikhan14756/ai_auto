"""Deterministic QA scoring and weighting engine."""

from typing import Dict, List, Tuple
from app.services.qa.constants import (
    CATEGORY_WEIGHTS,
    SEVERITY_DEDUCTIONS,
    QACategory,
    QASeverity,
)
from app.services.qa.models import CheckResult, CheckFindingSpec


class QAScoringEngine:
    """Computes category-specific and overall weighted quality assurance scores."""

    @classmethod
    def calculate_category_scores(
        cls,
        check_results: List[CheckResult],
    ) -> Tuple[Dict[str, dict], float]:
        """Aggregate check results and findings into per-category scores and overall score.

        Returns:
            Tuple[Dict[category, metrics_dict], overall_weighted_score]
        """
        # Group checks by category
        categorized_checks: Dict[str, List[CheckResult]] = {}
        for cat in QACategory:
            categorized_checks[cat.value] = []

        for check in check_results:
            categorized_checks.setdefault(check.category, []).append(check)

        category_summaries: Dict[str, dict] = {}
        overall_weighted_score = 0.0

        for cat_name, checks in categorized_checks.items():
            weight = CATEGORY_WEIGHTS.get(cat_name, 0.05)
            deductions: List[dict] = []

            # Start from 100.0
            cat_score = 100.0
            check_count = len(checks)
            passed_count = sum(1 for c in checks if c.status == "PASSED")
            warning_count = sum(1 for c in checks if c.status == "WARNING")
            failed_count = sum(1 for c in checks if c.status == "FAILED")

            # Collect all findings in this category
            all_findings: List[CheckFindingSpec] = []
            for c in checks:
                all_findings.extend(c.findings)

            # Deduct per finding severity
            has_critical = False
            for f in all_findings:
                deduction_amt = SEVERITY_DEDUCTIONS.get(f.severity, 0.0)
                if f.severity == QASeverity.CRITICAL.value:
                    has_critical = True
                deductions.append({
                    "title": f.title,
                    "severity": f.severity,
                    "deduction": deduction_amt,
                })
                cat_score -= deduction_amt

            if has_critical:
                cat_score = 0.0

            cat_score = max(0.0, min(100.0, cat_score))
            weighted_val = round(cat_score * weight, 2)
            overall_weighted_score += weighted_val

            category_summaries[cat_name] = {
                "category": cat_name,
                "weight": weight,
                "raw_score": round(cat_score, 2),
                "weighted_score": weighted_val,
                "deductions": deductions,
                "check_count": check_count,
                "passed_count": passed_count,
                "warning_count": warning_count,
                "failed_count": failed_count,
            }

        overall_weighted_score = max(0.0, min(100.0, round(overall_weighted_score, 2)))
        return category_summaries, overall_weighted_score
