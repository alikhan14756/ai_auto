"""Unit and component tests for SEO Metadata Generation, Scorer, and Thumbnail Pairing."""

import pytest
from app.services.seo.metadata_generator import SEOMetadataGenerator
from app.services.seo.scorer import SEOMetadataScorer


def test_seo_metadata_generator_full_package():
    """Verify metadata generator builds compliant YouTube package."""
    scenes = [
        {"title": "Hook & Problem", "duration_seconds": 15.0},
        {"title": "Architecture Overview", "duration_seconds": 60.0},
        {"title": "Code Implementation", "duration_seconds": 120.0},
        {"title": "Benchmarks & Summary", "duration_seconds": 45.0},
    ]
    sources = [
        {"title": "PostgreSQL Explicit Locking", "url": "https://www.postgresql.org/docs/current/explicit-locking.html"},
        {"title": "FastAPI Background Tasks", "url": "https://fastapi.tiangolo.com/tutorial/background-tasks/"},
    ]

    payload = SEOMetadataGenerator.generate_full_metadata(
        topic_title="PostgreSQL Durable Queue Architecture",
        script_summary="Learn how to build high-throughput job queues with Python and PostgreSQL without Celery or Redis.",
        keywords=["postgresql", "fastapi", "job queue", "asyncio"],
        scenes=scenes,
        research_sources=sources,
        total_duration_seconds=240.0,
    )

    # 1. Title candidates
    assert "title" in payload
    assert len(payload["title"]) <= 95
    assert len(payload["title_candidates"]) >= 3

    # 2. Chapters
    chapters = payload["chapters"]
    assert len(chapters) >= 3
    assert chapters[0]["timestamp"] == "00:00"  # Mandatory YouTube starting chapter

    # 3. Description checks
    desc = payload["description"]
    assert "Timestamps" in desc
    assert "00:00" in desc
    assert "Verified Sources" in desc
    assert "Disclosure:" in desc

    # 4. Tags limit
    tags_str = ", ".join(payload["tags"])
    assert len(tags_str) <= 500

    # 5. Hashtags
    assert len(payload["hashtags"]) <= 5

    # 6. Pinned comment
    assert payload.get("pinned_comment") is not None


def test_seo_metadata_scorer_clean_package():
    """Verify deterministic scoring gives high marks to a fully compliant package."""
    chapters = [
        {"timestamp": "00:00", "title": "Introduction"},
        {"timestamp": "01:30", "title": "Architecture"},
        {"timestamp": "04:00", "title": "Benchmarks"},
    ]
    description = (
        "Complete production guide to scalable job queues in Python.\n\n"
        "TIMESTAMPS:\n00:00 - Intro\n01:30 - Architecture\n04:00 - Benchmarks\n\n"
        "SOURCES:\n- Docs: https://example.com\n\n"
        "Disclosure: This video features AI-assisted scriptwriting and neural voice narration."
    )
    report = SEOMetadataScorer.score_metadata_package(
        title="Production Background Tasks with Python and FastAPI",
        description=description,
        tags=["python", "fastapi", "queue", "postgresql", "backend"],
        chapters=chapters,
        thumbnail_headline="STOP USING REDIS",
    )

    assert report["seo_score"] >= 80.0
    assert report["status"] in ["EXCELLENT", "GOOD"]
    assert len([i for i in report["issues"] if "clickbait" in i.lower()]) == 0


def test_seo_metadata_scorer_penalizes_clickbait_and_missing_disclosure():
    """Verify clickbait phrases and missing disclosures incur score penalties."""
    chapters = [{"timestamp": "00:05", "title": "Late Start"}]  # Missing 00:00
    description = "Short desc."
    report = SEOMetadataScorer.score_metadata_package(
        title="YOU WON'T BELIEVE WHAT HAPPENS NEXT!! SHOCKING TRUTH",
        description=description,
        tags=[],
        chapters=chapters,
        thumbnail_headline=None,
    )

    assert report["seo_score"] < 60.0
    assert any("clickbait" in iss.lower() for iss in report["issues"])
    assert any("transparency" in iss.lower() or "synthetic" in iss.lower() for iss in report["issues"])


def test_seo_metadata_pairing_score():
    """Verify thumbnail and title pairing evaluation works properly."""
    pairing = SEOMetadataScorer.evaluate_pairing(
        thumbnail_headline="JOB QUEUE IN PYTHON",
        video_title="How We Built an Asynchronous Job Queue in Python",
    )

    assert pairing["score"] > 10.0
    assert any("complements" in s.lower() for s in pairing["strengths"])
