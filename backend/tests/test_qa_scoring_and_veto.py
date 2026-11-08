"""Unit tests for QA Scoring Engine, Veto Gate, Invalidation Tracker, and Correction Engine."""

import pytest
from app.services.qa.constants import (
    CATEGORY_WEIGHTS,
    QACategory,
    QASeverity,
    QAVetoDecision,
    QAFindingStatus,
)
from app.services.qa.models import CheckResult, CheckFindingSpec, QAExecutionContext
from app.services.qa.scorer import QAScoringEngine
from app.services.qa.veto import QAVetoGate
from app.services.qa.invalidation import QAInvalidationTracker
from app.services.qa.corrections import QACorrectionEngine


def test_category_weights_sum_to_unity():
    total_weight = sum(CATEGORY_WEIGHTS.values())
    assert abs(total_weight - 1.0) < 0.001


def test_scoring_engine_clean_scores():
    checks = [
        CheckResult(category=cat.value, check_name="check_1", status="PASSED", score=100.0)
        for cat in QACategory
    ]
    summaries, overall = QAScoringEngine.calculate_category_scores(checks)
    assert overall == 100.0
    for cat in QACategory:
        assert summaries[cat.value]["raw_score"] == 100.0


def test_scoring_engine_critical_finding_zeros_category():
    finding = CheckFindingSpec(
        category=QACategory.SECURITY_PRIVACY.value,
        severity=QASeverity.CRITICAL.value,
        affected_artifact="script",
        title="Secret exposed",
        explanation="Secret key exposed in script",
    )
    checks = [
        CheckResult(
            category=QACategory.SECURITY_PRIVACY.value,
            check_name="secret_scan",
            status="FAILED",
            score=0.0,
            findings=[finding],
        )
    ]
    summaries, overall = QAScoringEngine.calculate_category_scores(checks)
    sec_summary = summaries[QACategory.SECURITY_PRIVACY.value]
    assert sec_summary["raw_score"] == 0.0
    assert sec_summary["weighted_score"] == 0.0
    assert overall < 100.0


def test_veto_gate_critical_blocks_never_bypassable():
    findings = [
        {
            "id": "find-1",
            "severity": QASeverity.CRITICAL.value,
            "status": QAFindingStatus.OPEN.value,
            "title": "Severe Corrupted MP4",
        }
    ]
    # Even if finding is in excepted set, CRITICAL must never be bypassed!
    decision, can_publish, breakdown = QAVetoGate.evaluate(
        findings=findings,
        excepted_finding_ids={"find-1"},
        overall_score=98.0,
    )
    assert decision == QAVetoDecision.BLOCKED.value
    assert can_publish is False
    assert breakdown["critical_count"] == 1


def test_veto_gate_high_unexempted_blocks():
    findings = [
        {
            "id": "find-2",
            "severity": QASeverity.HIGH.value,
            "status": QAFindingStatus.OPEN.value,
            "title": "Unverified Claim",
        }
    ]
    decision, can_publish, breakdown = QAVetoGate.evaluate(
        findings=findings,
        excepted_finding_ids=set(),
        overall_score=90.0,
    )
    assert decision == QAVetoDecision.BLOCKED.value
    assert can_publish is False
    assert breakdown["unexcepted_high_count"] == 1


def test_veto_gate_high_excepted_allows_publish():
    findings = [
        {
            "id": "find-3",
            "severity": QASeverity.HIGH.value,
            "status": QAFindingStatus.OPEN.value,
            "title": "Historical Unverified Metric",
        }
    ]
    decision, can_publish, breakdown = QAVetoGate.evaluate(
        findings=findings,
        excepted_finding_ids={"find-3"},
        overall_score=85.0,
    )
    assert decision == QAVetoDecision.APPROVED.value
    assert can_publish is True
    assert breakdown["excepted_high_count"] == 1


def test_veto_gate_medium_needs_review():
    findings = [
        {
            "id": "find-4",
            "severity": QASeverity.MEDIUM.value,
            "status": QAFindingStatus.OPEN.value,
            "title": "Slight Loudness Drift",
        }
    ]
    decision, can_publish, breakdown = QAVetoGate.evaluate(
        findings=findings,
        excepted_finding_ids=set(),
        overall_score=82.0,
    )
    assert decision == QAVetoDecision.NEEDS_REVIEW.value
    assert can_publish is True
    assert breakdown["medium_count"] == 1


def test_veto_gate_clean_approved():
    decision, can_publish, breakdown = QAVetoGate.evaluate(
        findings=[],
        excepted_finding_ids=set(),
        overall_score=95.0,
    )
    assert decision == QAVetoDecision.APPROVED.value
    assert can_publish is True


def test_invalidation_tracker_detects_changes():
    old_snap = {
        "script": "hash_a",
        "narration": "hash_b",
        "visual_assets": "hash_c",
        "render": "hash_d",
        "thumbnail": "hash_e",
        "metadata": "hash_f",
    }
    new_snap = dict(old_snap)
    new_snap["thumbnail"] = "hash_e_new"

    invalidated = QAInvalidationTracker.get_invalidated_categories(old_snap, new_snap)
    assert QACategory.THUMBNAIL_QUALITY.value in invalidated
    assert QACategory.PACKAGE_COMPLETENESS.value in invalidated
    # Script quality should NOT be invalidated by thumbnail change
    assert QACategory.SCRIPT_QUALITY.value not in invalidated


def test_correction_engine_guidance():
    guide = QACorrectionEngine.generate_correction_guide({
        "category": QACategory.SECURITY_PRIVACY.value,
        "severity": QASeverity.CRITICAL.value,
        "title": "Exposed API key in script",
        "affected_artifact": "script",
    })
    assert guide["navigation_target"] == "/script-studio"
    assert len(guide["actionable_steps"]) >= 2
