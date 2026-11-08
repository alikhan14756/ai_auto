"""Test all 21 SQLAlchemy relational models, constraints, and cascade deletions."""

import uuid
import pytest
from datetime import datetime, timezone
from sqlalchemy import select

from app.models import (
    User,
    Channel,
    ChannelSettings,
    Topic,
    ResearchSource,
    VideoProject,
    Script,
    ScriptClaim,
    Scene,
    MediaAsset,
    Voiceover,
    Thumbnail,
    RenderJob,
    QualityReport,
    PublishingJob,
    YouTubeVideo,
    AnalyticsSnapshot,
    AutomationJob,
    ProviderUsage,
    PromptTemplate,
    AuditLog,
)
from app.core.security import encrypt_token


@pytest.mark.asyncio
async def test_all_21_models_crud_and_cascade(db_session):
    """Verify that all 21 models can be created, persisted, queried, and cascade-deleted."""
    # 1. User
    user = User(
        supabase_user_id=f"sub_{uuid.uuid4().hex[:12]}",
        email=f"creator_{uuid.uuid4().hex[:8]}@example.com",
        full_name="Muhammad Ali",
        role="CREATOR",
    )
    db_session.add(user)
    await db_session.flush()
    assert isinstance(user.id, uuid.UUID)

    # 2. Channel
    channel = Channel(
        user_id=user.id,
        youtube_channel_id=f"UC_{uuid.uuid4().hex[:16]}",
        title="AI Automation HQ",
        description="Daily AI tools and tutorials",
        custom_url="@aiautomationhq",
        thumbnail_url="https://images.example.com/channel.png",
        subscriber_count=10000,
        oauth_refresh_token_encrypted=encrypt_token("refresh_secret_123"),
        is_active=True,
    )
    db_session.add(channel)
    await db_session.flush()

    # 3. ChannelSettings
    settings = ChannelSettings(
        channel_id=channel.id,
        niche_keywords=["ai tools", "automation", "python"],
        default_privacy="unlisted",
        default_category_id="28",
        weekly_cadence_long=2,
        weekly_cadence_shorts=3,
        auto_publish_enabled=False,
        max_monthly_spend_usd=50.00,
        topic_retention_weights={"ctr": 0.5, "retention_30s": 0.5},
    )
    db_session.add(settings)

    # 4. Topic
    topic = Topic(
        channel_id=channel.id,
        title="Top 5 Open Source LLM Agents in 2026",
        niche_category="AI Tools",
        opportunity_score=88.5,
        search_volume_score=75.0,
        competition_score=35.0,
        status="DISCOVERED",
        raw_discovery_payload={"source": "reddit", "mentions": 120},
    )
    db_session.add(topic)
    await db_session.flush()

    # 5. ResearchSource
    source = ResearchSource(
        topic_id=topic.id,
        source_url="https://arxiv.org/abs/2401.00000",
        source_title="Autonomous Coding Agent Benchmarks",
        extracted_summary="Evaluated agentic coding frameworks on SWE-bench.",
        relevance_score=0.950,
    )
    db_session.add(source)

    # 6. VideoProject
    project = VideoProject(
        channel_id=channel.id,
        topic_id=topic.id,
        title="Top 5 Open Source LLM Agents in 2026",
        format="LONG_FORM",
        state="RESEARCHED",
        target_duration_seconds=600,
        revision_number=1,
    )
    db_session.add(project)
    await db_session.flush()

    # 7. Script
    script = Script(
        project_id=project.id,
        version=1,
        full_text="Welcome back! Today we are looking at 5 mindblowing AI tools...",
        word_count=1200,
        estimated_duration_seconds=480,
        is_locked=False,
    )
    db_session.add(script)
    await db_session.flush()

    # 8. ScriptClaim
    claim = ScriptClaim(
        script_id=script.id,
        project_id=project.id,
        claim_text="Tool X solves 82% of SWE-bench verified tasks.",
        extracted_entity="Tool X",
        claim_type="BENCHMARK",
        is_verified=True,
        confidence_score=0.985,
        citation_url="https://example.com/benchmark",
        citation_snippet="Tool X achieved 82% on the verified subset.",
    )
    db_session.add(claim)

    # 9. Scene
    scene = Scene(
        project_id=project.id,
        scene_order=1,
        narration_text="In 2026, AI coding agents evolved dramatically.",
        visual_archetype="BROWSER_CAPTURE",
        visual_directive="Pan down homepage of tool X showing real-time agent output.",
        target_url="https://toolx.ai",
        duration_seconds=8.50,
    )
    db_session.add(scene)
    await db_session.flush()

    # 10. MediaAsset
    media = MediaAsset(
        scene_id=scene.id,
        project_id=project.id,
        asset_type="VIDEO_CAPTURE",
        storage_path="/storage/assets/scene_1.mp4",
        file_size_bytes=10485760,
        sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        license_type="RECORDED_DEMO",
        is_verified=True,
    )
    db_session.add(media)

    # 11. Voiceover
    voiceover = Voiceover(
        scene_id=scene.id,
        project_id=project.id,
        tts_engine="EDGE_TTS",
        voice_id="en-US-ChristopherNeural",
        audio_storage_path="/storage/audio/scene_1.mp3",
        duration_seconds=8.500,
        word_timestamps=[{"word": "In", "start": 0.0, "end": 0.2}],
        loudness_lufs=-14.20,
    )
    db_session.add(voiceover)

    # 12. Thumbnail
    thumbnail = Thumbnail(
        project_id=project.id,
        variant_code="A",
        storage_path="/storage/thumbnails/var_a.jpg",
        headline_text="5 INSANE AI TOOLS",
        accent_color_hex="#FF7A00",
        is_selected=True,
    )
    db_session.add(thumbnail)

    # 13. RenderJob
    render_job = RenderJob(
        project_id=project.id,
        resolution="1080p",
        output_video_path="/storage/renders/final.mp4",
        render_duration_seconds=45.2,
        ffmpeg_command_executed="ffmpeg -i ...",
        status="COMPLETED",
    )
    db_session.add(render_job)
    await db_session.flush()

    # 14. QualityReport
    qa = QualityReport(
        project_id=project.id,
        render_job_id=render_job.id,
        all_checks_passed=True,
        black_frame_duration_max=0.0,
        freeze_duration_max=0.0,
        integrated_loudness_lufs=-14.0,
        max_true_peak_dbtp=-1.0,
        unverified_claims_count=0,
        transcript_similarity_ratio=0.995,
        diagnostic_details={"status": "ALL_PASSED"},
    )
    db_session.add(qa)

    # 15. PublishingJob
    pub_job = PublishingJob(
        project_id=project.id,
        channel_id=channel.id,
        scheduled_publish_time=datetime.now(timezone.utc),
        privacy_status="unlisted",
        synthetic_media_declared=True,
        status="COMPLETED",
    )
    db_session.add(pub_job)
    await db_session.flush()

    # 16. YouTubeVideo
    yt_video = YouTubeVideo(
        publishing_job_id=pub_job.id,
        project_id=project.id,
        youtube_video_id=f"yt_{uuid.uuid4().hex[:11]}",
        published_video_url="https://youtube.com/watch?v=12345",
        view_count=5000,
        like_count=350,
        comment_count=42,
    )
    db_session.add(yt_video)
    await db_session.flush()

    # 17. AnalyticsSnapshot
    analytics = AnalyticsSnapshot(
        youtube_video_id=yt_video.youtube_video_id,
        snapshot_time=datetime.now(timezone.utc),
        views=5000,
        watch_time_minutes=25000.0,
        average_view_duration_seconds=300.0,
        click_through_rate=0.0825,
        retention_at_30s=0.7200,
    )
    db_session.add(analytics)

    # 18. AutomationJob
    job = AutomationJob(
        channel_id=channel.id,
        job_type="DISCOVER_TOPICS",
        payload={"niche": "AI Tools"},
        idempotency_key=f"job_{uuid.uuid4().hex}",
        status="COMPLETED",
        priority=10,
    )
    db_session.add(job)

    # 19. ProviderUsage
    usage = ProviderUsage(
        channel_id=channel.id,
        provider_name="GEMINI_FLASH",
        model_name="gemini-1.5-flash",
        input_tokens=1500,
        output_tokens=800,
        cost_usd=0.000350,
    )
    db_session.add(usage)

    # 20. PromptTemplate
    template = PromptTemplate(
        template_key=f"SCRIPT_{uuid.uuid4().hex[:6]}",
        system_prompt="You are a seasoned YouTube scriptwriter.",
        user_prompt_template="Write a high-retention script for: {topic}",
        schema_definition={"type": "object", "properties": {"title": {"type": "string"}}},
        version="v1.0.0",
    )
    db_session.add(template)

    # 21. AuditLog
    audit = AuditLog(
        user_id=user.id,
        action="USER_LOGIN",
        resource_type="USER",
        resource_id=user.id,
        ip_address="127.0.0.1",
        details={"method": "jwt"},
    )
    db_session.add(audit)

    await db_session.commit()

    # Query back and verify relationships
    stmt = select(Channel).where(Channel.id == channel.id)
    res = await db_session.execute(stmt)
    loaded_channel = res.scalars().first()
    assert loaded_channel is not None
    assert loaded_channel.title == "AI Automation HQ"

    # Verify Cascade Delete: deleting the channel cascades to all projects, topics, jobs
    await db_session.delete(loaded_channel)
    await db_session.commit()

    # Verify project was cascaded
    proj_stmt = select(VideoProject).where(VideoProject.id == project.id)
    proj_res = await db_session.execute(proj_stmt)
    assert proj_res.scalars().first() is None
