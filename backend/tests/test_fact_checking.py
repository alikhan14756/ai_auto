"""Unit and integration tests for Fact Checking and Source Cross-Referencing."""

import pytest
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.channel import Channel
from app.models.project import VideoProject
from app.models.topic import Topic, ResearchSource
from app.models.user import User
from app.schemas.script import ScriptClaimSchema
from app.services.fact_checking import FactCheckingService


def test_verify_claim_against_sources():
    sources = [
        ResearchSource(
            source_url="https://www.postgresql.org/docs/current/sql-select.html",
            source_title="PostgreSQL Documentation: SKIP LOCKED Clause",
            extracted_summary="The SKIP LOCKED clause in PostgreSQL ensures non-blocking concurrent row selection.",
            relevance_score=0.98,
        ),
        ResearchSource(
            source_url="https://brandur.org/postgres-queues",
            source_title="PostgreSQL Queues Benchmark",
            extracted_summary="Empirical benchmarks demonstrate 5,000 jobs per second throughput on modern cloud instances.",
            relevance_score=0.95,
        ),
    ]

    # 1. Supported Claim
    claim_supported = ScriptClaimSchema(
        claim_text="PostgreSQL provides non-blocking row selection with the SKIP LOCKED clause.",
        claim_type="FEATURE",
    )
    result_supported = FactCheckingService.verify_claim_against_sources(claim_supported, sources)
    assert result_supported.is_verified is True
    assert result_supported.confidence_score >= 0.70
    assert result_supported.citation_url == "https://www.postgresql.org/docs/current/sql-select.html"
    assert "authoritative source" in result_supported.verification_explanation.lower()

    # 2. Unsupported / False Claim
    claim_unsupported = ScriptClaimSchema(
        claim_text="Quantum computers can decrypt Bitcoin blockchain in three seconds.",
        claim_type="BENCHMARK",
    )
    result_unsupported = FactCheckingService.verify_claim_against_sources(claim_unsupported, sources)
    assert result_unsupported.is_verified is False
    assert result_unsupported.confidence_score < 0.40
    assert result_unsupported.citation_url is None
    assert "no supporting documentation" in result_unsupported.verification_explanation.lower()


@pytest.mark.asyncio
async def test_verify_script_claims_database_integration(db_session: AsyncSession):
    # Setup user, channel, topic, sources, project
    user = User(supabase_user_id=f"test-sub-{uuid4()}", email="factcheck@example.com")
    db_session.add(user)
    await db_session.flush()

    channel = Channel(
        user_id=user.id,
        youtube_channel_id=f"UC_{uuid4().hex[:16]}",
        title="Engineering Channel",
        oauth_refresh_token_encrypted="token",
    )
    db_session.add(channel)
    await db_session.flush()

    topic = Topic(
        channel_id=channel.id,
        title="PostgreSQL Queues",
        niche_category="Databases",
        opportunity_score=90.0,
        status="SELECTED",
    )
    db_session.add(topic)
    await db_session.flush()

    source = ResearchSource(
        topic_id=topic.id,
        source_url="https://postgresql.org/docs",
        source_title="PostgreSQL Documentation",
        extracted_summary="PostgreSQL transactional worker queue supports ACID rollbacks and crash recovery.",
        relevance_score=0.96,
    )
    db_session.add(source)

    project = VideoProject(
        channel_id=channel.id,
        topic_id=topic.id,
        title="PostgreSQL Worker Queue Architecture",
    )
    db_session.add(project)
    await db_session.commit()

    claims = [
        ScriptClaimSchema(
            claim_text="PostgreSQL worker queue supports ACID rollbacks and crash recovery.",
            claim_type="FEATURE",
        ),
        ScriptClaimSchema(
            claim_text="Invented statistical claim about machine learning latency.",
            claim_type="BENCHMARK",
        ),
    ]

    verified = await FactCheckingService.verify_script_claims(claims, project.id, db_session)
    assert len(verified) == 2
    assert verified[0].is_verified is True
    assert verified[1].is_verified is False
