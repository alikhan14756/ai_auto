"""Unit tests for Topic Opportunity Scoring, Tokenizing, and Semantic Deduplication."""

import pytest
from app.services.topic_scoring import TopicScoringService


def test_tokenize():
    tokens = TopicScoringService._tokenize("Why Postgres SKIP LOCKED Replaces Redis in 2026")
    assert "postgres" in tokens
    assert "skip" in tokens
    assert "locked" in tokens
    assert "replaces" in tokens
    assert "redis" in tokens
    # Stop words like 'why', 'in', '2026' excluded
    assert "why" not in tokens
    assert "2026" not in tokens


def test_jaccard_similarity():
    title_a = "Building Reliable Autonomous AI Agents with FastAPI"
    title_b = "Building Autonomous AI Agents with FastAPI in Production"
    similarity = TopicScoringService.calculate_similarity(title_a, title_b)
    assert similarity >= 0.60

    unrelated = "PostgreSQL Index Tuning and Partitioning Guide"
    assert TopicScoringService.calculate_similarity(title_a, unrelated) == 0.0


def test_find_max_historical_similarity():
    history = [
        "How to Build Fast Python Microservices with FastAPI",
        "Deep Dive into PostgreSQL Connection Pooling and PgBouncer",
        "Autonomous Multi-Agent Systems in Production",
    ]

    candidate_dup = "Building Autonomous Multi-Agent Systems for Production"
    sim, matched = TopicScoringService.find_max_historical_similarity(candidate_dup, history)
    assert sim >= 0.60
    assert matched == "Autonomous Multi-Agent Systems in Production"

    candidate_fresh = "Zero-Downtime SQLite Streaming with Litestream"
    sim_fresh, _ = TopicScoringService.find_max_historical_similarity(candidate_fresh, history)
    assert sim_fresh == 0.0


def test_calculate_opportunity_score_default_weights():
    score = TopicScoringService.calculate_opportunity_score(
        audience_relevance=90.0,
        practical_value=90.0,
        originality=80.0,
        search_volume_score=70.0,
        competition_score=30.0,  # competition advantage is 100 - 30 = 70.0
    )
    # 0.25*90 + 0.25*90 + 0.20*80 + 0.15*70 + 0.15*70 = 22.5 + 22.5 + 16.0 + 10.5 + 10.5 = 82.0
    assert score == 82.0


def test_opportunity_score_clamping():
    # Over 100 inputs should clamp to 100
    perfect = TopicScoringService.calculate_opportunity_score(150.0, 120.0, 200.0, 100.0, 0.0)
    assert perfect == 100.0

    # Negative inputs should clamp to 0
    terrible = TopicScoringService.calculate_opportunity_score(-10.0, 0.0, -50.0, 0.0, 100.0)
    assert terrible == 0.0


def test_opportunity_score_custom_weights():
    custom = {
        "audience_relevance": 0.50,
        "practical_value": 0.50,
        "originality": 0.0,
        "search_volume": 0.0,
        "competition_advantage": 0.0,
    }
    score = TopicScoringService.calculate_opportunity_score(
        audience_relevance=80.0,
        practical_value=60.0,
        originality=100.0,
        search_volume_score=100.0,
        competition_score=0.0,
        custom_weights=custom,
    )
    # 0.50*80 + 0.50*60 = 40 + 30 = 70.0
    assert score == 70.0
