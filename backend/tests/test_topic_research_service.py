"""Integration tests for TopicResearchService with persistent database models."""

import pytest
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.channel import Channel, ChannelSettings
from app.models.topic import Topic, ResearchSource
from app.models.user import User
from app.models.usage import ProviderUsage
from app.providers.ai.mock import MockAIProvider
from app.services.topic_research import TopicResearchService


@pytest.mark.asyncio
async def test_topic_discovery_and_persistence(db_session: AsyncSession):
    # Setup test channel
    user = User(
        supabase_user_id=f"test-sub-{uuid4()}",
        email=f"researcher-{uuid4()}@example.com",
    )
    db_session.add(user)
    await db_session.flush()

    channel = Channel(
        user_id=user.id,
        youtube_channel_id=f"UC_{uuid4().hex[:16]}",
        title="High Scale Systems",
        oauth_refresh_token_encrypted="encrypted-test-token",
    )
    db_session.add(channel)
    await db_session.flush()

    settings = ChannelSettings(
        channel_id=channel.id,
        niche_keywords=["PostgreSQL", "FastAPI", "Async Architecture"],
        max_monthly_spend_usd=100.00,
    )
    db_session.add(settings)
    await db_session.commit()

    # Run topic discovery using MockAIProvider
    mock_provider = MockAIProvider()
    service = TopicResearchService(provider=mock_provider)

    topics = await service.discover_and_persist_topics(
        channel_id=channel.id,
        db=db_session,
        count=3,
    )

    assert len(topics) >= 1
    for topic in topics:
        assert topic.channel_id == channel.id
        assert topic.status == "DISCOVERED"
        assert topic.opportunity_score > 0.0
        assert topic.search_volume_score > 0.0
        assert len(topic.research_sources) >= 1

        for src in topic.research_sources:
            assert src.source_url.startswith("http")
            assert len(src.extracted_summary) > 10
            assert src.relevance_score > 0.0

    # Verify that usage was recorded in ProviderUsage
    usage_stmt = select(ProviderUsage).where(ProviderUsage.channel_id == channel.id)
    usage_res = await db_session.execute(usage_stmt)
    usages = list(usage_res.scalars().all())
    assert len(usages) >= 1
    assert usages[0].input_tokens > 0
    assert usages[0].output_tokens > 0


@pytest.mark.asyncio
async def test_topic_discovery_duplicate_penalty(db_session: AsyncSession):
    user = User(
        supabase_user_id=f"test-sub-{uuid4()}",
        email=f"dup-{uuid4()}@example.com",
    )
    db_session.add(user)
    await db_session.flush()

    channel = Channel(
        user_id=user.id,
        youtube_channel_id=f"UC_{uuid4().hex[:16]}",
        title="Duplicate Testing Channel",
        oauth_refresh_token_encrypted="encrypted-test-token",
    )
    db_session.add(channel)
    await db_session.flush()

    # Pre-populate historical topic with exact title from default mock
    existing = Topic(
        channel_id=channel.id,
        title="Autonomous AI Agents in Production: 5 Failure Modes You Must Avoid",
        niche_category="AI Architecture",
        opportunity_score=85.0,
        search_volume_score=80.0,
        competition_score=40.0,
        status="DISCOVERED",
    )
    db_session.add(existing)
    await db_session.commit()

    service = TopicResearchService(provider=MockAIProvider())
    new_topics = await service.discover_and_persist_topics(
        channel_id=channel.id,
        db=db_session,
        count=3,
    )

    # The exact duplicate candidate must be skipped/filtered out
    new_titles = [t.title for t in new_topics]
    assert "Autonomous AI Agents in Production: 5 Failure Modes You Must Avoid" not in new_titles
