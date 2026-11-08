"""Unit tests for Script Evaluation, Spoken Duration, Readability, and Repetition."""

import pytest
from app.services.script_evaluation import ScriptEvaluationService


def test_word_count_and_duration():
    text = "PostgreSQL is an advanced, enterprise-class open source relational database."
    count = ScriptEvaluationService.calculate_word_count(text)
    assert count == 9

    # 140 WPM -> 70 words is 30 seconds
    words_70 = " ".join(["word"] * 70)
    duration = ScriptEvaluationService.estimate_duration_seconds(70)
    assert duration == 30


def test_hook_strength_evaluation():
    # Strong curiosity hook
    strong_hook = "Why are modern backend engineers replacing Redis with PostgreSQL in production architectures?"
    score_strong = ScriptEvaluationService.evaluate_hook_strength(strong_hook)
    assert score_strong >= 80.0

    # Weak / empty hook
    weak_hook = "Hello everyone."
    score_weak = ScriptEvaluationService.evaluate_hook_strength(weak_hook)
    assert score_weak < 70.0


def test_clarity_evaluation():
    # Crisp spoken sentences (around 12-15 words)
    good_text = (
        "Building a background worker queue does not require dedicated cache clusters. "
        "PostgreSQL provides non-blocking row acquisition directly through the SKIP LOCKED clause. "
        "This architectural pattern guarantees zero lock contention across concurrent workers."
    )
    score_good = ScriptEvaluationService.evaluate_clarity(good_text)
    assert score_good >= 85.0

    # Excessively long run-on sentence (> 35 words)
    bad_text = (
        "When you consider the architectural tradeoffs of deploying a distributed message broker "
        "like Apache Kafka or RabbitMQ alongside Redis in an enterprise cloud infrastructure "
        "you might quickly discover that maintaining cross-service idempotency and schema migrations "
        "creates tremendous overhead that overwhelms your team without adding real business value."
    )
    score_bad = ScriptEvaluationService.evaluate_clarity(bad_text)
    assert score_bad < score_good


def test_repetition_detection():
    # Clean text with diverse phrases
    clean_text = (
        "PostgreSQL 17 includes powerful concurrency features. "
        "Concurrent workers claim jobs independently. "
        "Streaming replication provides disaster recovery."
    )
    rep_clean = ScriptEvaluationService.detect_repetition(clean_text)
    assert rep_clean == 0.0

    # Highly repetitive text
    repeated_text = (
        "You must avoid this failure. You must avoid this failure. "
        "You must avoid this failure. You must avoid this failure."
    )
    rep_high = ScriptEvaluationService.detect_repetition(repeated_text)
    assert rep_high > 0.0


def test_composite_script_evaluation():
    text = (
        "Why do high-scale startups avoid Redis for mission-critical background jobs? "
        "PostgreSQL provides transactional durability with zero external infrastructure overhead."
    )
    metrics = ScriptEvaluationService.evaluate_script(
        full_text=text,
        hook_text=text.split("?")[0],
        total_claims=2,
        verified_claims=2,
        unverified_claims=0,
    )
    assert metrics.overall_score >= 80.0
    assert metrics.word_count > 0
    assert metrics.estimated_duration_seconds > 0
    assert metrics.evidence_coverage == 100.0
