"""Deterministic publication veto gate evaluation."""

from typing import Dict, List, Set, Tuple
from app.services.qa.constants import (
    QASeverity,
    QAVetoDecision,
    QAFindingStatus,
)


class QAVetoGate:
    """Evaluates hard veto blockers and determines publication release readiness."""

    @classmethod
    def evaluate(
        cls,
        findings: List[dict],
        excepted_finding_ids: Set[str] = None,
        overall_score: float = 100.0,
    ) -> Tuple[str, bool, dict]:
        """Evaluate findings against hard veto policies.

        Args:
            findings: List of finding dicts or objects containing severity, status, id, title.
            excepted_finding_ids: Set of finding IDs that have authorized QAExceptions.
            overall_score: Weighted composite quality score (0.00 - 100.00).

        Returns:
            Tuple[veto_decision, can_publish, decision_breakdown]
        """
        excepted_finding_ids = excepted_finding_ids or set()

        critical_blockers: List[str] = []
        unexcepted_high_blockers: List[str] = []
        excepted_high_issues: List[str] = []
        medium_warnings: List[str] = []
        low_advisories: List[str] = []

        for f in findings:
            fid = str(f.get("id", ""))
            status = f.get("status", QAFindingStatus.OPEN.value)
            severity = f.get("severity", QASeverity.LOW.value)
            title = f.get("title", "Issue")

            # Resolved findings do not block
            if status == QAFindingStatus.RESOLVED.value:
                continue

            if severity == QASeverity.CRITICAL.value:
                # CRITICAL findings CANNOT be exempted by policy
                critical_blockers.append(title)
            elif severity == QASeverity.HIGH.value:
                if fid in excepted_finding_ids or status == QAFindingStatus.ACCEPTED_WITH_EXCEPTION.value:
                    excepted_high_issues.append(title)
                else:
                    unexcepted_high_blockers.append(title)
            elif severity == QASeverity.MEDIUM.value:
                medium_warnings.append(title)
            else:
                low_advisories.append(title)

        # Hard Veto Decision Matrix
        can_publish = False
        if len(critical_blockers) > 0:
            veto_decision = QAVetoDecision.BLOCKED.value
            reason = f"Blocked by {len(critical_blockers)} CRITICAL veto finding(s)."
        elif len(unexcepted_high_blockers) > 0:
            veto_decision = QAVetoDecision.BLOCKED.value
            reason = f"Blocked by {len(unexcepted_high_blockers)} unexempted HIGH severity finding(s)."
        elif len(medium_warnings) > 0:
            if overall_score < 75.0:
                veto_decision = QAVetoDecision.BLOCKED.value
                reason = f"Quality score {overall_score:.1f} below threshold (75.0) with {len(medium_warnings)} open warning(s)."
            else:
                veto_decision = QAVetoDecision.NEEDS_REVIEW.value
                can_publish = True
                reason = f"Publishable with review: {len(medium_warnings)} medium warning(s) flagged."
        elif overall_score < 80.0:
            veto_decision = QAVetoDecision.BLOCKED.value
            reason = f"Overall score {overall_score:.1f} below minimum publication standard (80.0)."
        else:
            veto_decision = QAVetoDecision.APPROVED.value
            can_publish = True
            reason = "All checks passed compliance and quality criteria."

        breakdown = {
            "can_publish": can_publish,
            "veto_decision": veto_decision,
            "reason": reason,
            "critical_count": len(critical_blockers),
            "critical_blockers": critical_blockers,
            "unexcepted_high_count": len(unexcepted_high_blockers),
            "unexcepted_high_blockers": unexcepted_high_blockers,
            "excepted_high_count": len(excepted_high_issues),
            "excepted_high_issues": excepted_high_issues,
            "medium_count": len(medium_warnings),
            "low_count": len(low_advisories),
            "overall_score": overall_score,
        }

        return veto_decision, can_publish, breakdown
