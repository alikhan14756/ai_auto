"""Integration tests for ScriptGenerationService and Scene synchronization."""

import pytest
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.channel import Channel, ChannelSettings
from app.models.project import VideoProject
from app.models.scene import Scene
from app.models.script import Script, ScriptClaim
from app.models.topic import Topic, ResearchSource
from app.models.user import User
from app.providers.ai.mock import MockAIProvider
from app.services.script_generation import ScriptGenerationService


@pytest.mark.asyncio
async def test_generate_and_persist_script_pipeline(db_session: AsyncSession):
    user = User(supabase_user_id=f"test-sub-{uuid4()}", email="scriptwriter@example.com")
    db_session.add(user)
    await db_session.flush()

    channel = Channel(
        user_id=user.id,
        youtube_channel_id=f"UC_{uuid4().hex[:16]}",
        title="Full Stack Channel",
        oauth_refresh_token_encrypted="token",
    )
    db_session.add(channel)
    await db_session.flush()

    settings = ChannelSettings(channel_id=channel.id, max_monthly_spend_usd=50.00)
    db_session.add(settings)
    await db_session.flush()

    topic = Topic(
        channel_id=channel.id,
        title="PostgreSQL SKIP LOCKED Queues",
        niche_category="Databases",
        opportunity_score=92.0,
        status="SELECTED",
    )
    db_session.add(topic)
    await db_session.flush()

    source = ResearchSource(
        topic_id=topic.id,
        source_url="https://postgresql.org",
        source_title="PostgreSQL Documentation",
        extracted_summary="PostgreSQL 9.5 introduced the SKIP LOCKED clause for non-blocking row selection.",
        relevance_score=0.95,
    )
    db_session.add(source)

    project = VideoProject(
        channel_id=channel.id,
        topic_id=topic.id,
        title="PostgreSQL Queues Video",
        format="LONG_FORM",
        target_duration_seconds=480,
    )
    db_session.add(project)
    await db_session.commit()

    service = ScriptGenerationService(provider=MockAIProvider())
    script = await service.generate_and_persist_script(
        project_id=project.id,
        db=db_session,
        target_duration_seconds=480,
    )

    assert script.id is not None
    assert script.project_id == project.id
    assert script.version == 1
    assert script.word_count > 0
    assert script.estimated_duration_seconds > 0
    assert len(script.claims) >= 1

    # Verify project state was updated
    await db_session.refresh(project)
    assert project.state == "SCRIPT_DRAFTED"

    # Verify scenes were created in scenes table
    scene_stmt = select(Scene).where(Scene.project_id == project.id)
    scene_res = await db_session.execute(scene_stmt)
    scenes = list(scene_res.scalars().all())
    assert len(scenes) >= 1

    # Test version increment on second generation
    second_script = await service.generate_and_persist_script(
        project_id=project.id,
        db=db_session,
    )
    assert second_script.version == 2


@pytest.mark.asyncio
async def test_regenerate_individual_section(db_session: AsyncSession):
    user = User(supabase_user_id=f"test-sub-{uuid4()}", email="section@example.com")
    db_session.add(user)
    await db_session.flush()

    channel = Channel(
        user_id=user.id,
        youtube_channel_id=f"UC_{uuid4().hex[:16]}",
        title="Section Channel",
        oauth_refresh_token_encrypted="token",
    )
    db_session.add(channel)
    await db_session.flush()

    project = VideoProject(
        channel_id=channel.id,
        title="Test Project",
    )
    db_session.add(project)
    await db_session.flush()

    script = Script(
        project_id=project.id,
        version=1,
        full_text="Initial full script content covering background jobs.",
        word_count=7,
        estimated_duration_seconds=3,
    )
    db_session.add(script)
    await db_session.commit()

    service = ScriptGenerationService(provider=MockAIProvider())
    revised = await service.regenerate_section(
        script_id=script.id,
        section_id="sec_02",
        custom_prompt="Include code example in Python",
        db=db_session,
    )

    assert "[Revised Section sec_02]" in revised.full_text
    assert revised.word_count > 7


@pytest.mark.asyncio
async def test_generate_outline_service(db_session: AsyncSession):
    user = User(supabase_user_id=f"test-sub-{uuid4()}", email="outline@example.com")
    db_session.add(user)
    await db_session.flush()

    channel = Channel(
        user_id=user.id,
        youtube_channel_id=f"UC_{uuid4().hex[:16]}",
        title="Outline Channel",
        oauth_refresh_token_encrypted="token",
    )
    db_session.add(channel)
    await db_session.flush()

    settings = ChannelSettings(channel_id=channel.id, max_monthly_spend_usd=25.00)
    db_session.add(settings)
    await db_session.flush()

    project = VideoProject(
        channel_id=channel.id,
        title="System Design Video",
        format="LONG_FORM",
        target_duration_seconds=600,
    )
    db_session.add(project)
    await db_session.commit()

    service = ScriptGenerationService(provider=MockAIProvider())
    outline = await service.generate_outline(
        project_id=project.id,
        db=db_session,
        target_duration_seconds=600,
        tone="authoritative",
    )

    assert outline.project_id == project.id
    assert outline.target_duration_seconds == 600
    assert outline.format == "LONG_FORM"
    assert len(outline.sections) >= 1
    assert outline.video_title != ""
    assert outline.hook_concept != ""
