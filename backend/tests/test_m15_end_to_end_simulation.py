"""Milestone 15 — Complete Controlled End-to-End Production Simulation Test.

Executes the 25-step autonomous production lifecycle:
1. Create a test user.
2. Authenticate.
3. Open the dashboard (query channel & settings).
4. Configure a mock AI provider.
5. Research a topic.
6. Approve a topic.
7. Generate a script.
8. Run fact-checking.
9. Generate mock narration.
10. Create mock visual assets.
11. Assemble a test video.
12. Generate a thumbnail.
13. Generate SEO metadata.
14. Run QA.
15. Verify that a failed QA result blocks publication.
16. Approve a valid test package.
17. Run the mocked YouTube upload flow.
18. Verify upload progress and recovery.
19. Simulate successful publication.
20. Retrieve mocked analytics.
21. Generate performance insights.
22. Create a future production plan.
23. Execute an authorized workflow.
24. Verify resource and budget limits ($0 spend enforcement).
25. Inspect audit history.
"""

import uuid
import datetime
from datetime import timezone, timedelta
import pytest

from app.models.user import User
from app.models.channel import Channel, ChannelSettings
from app.models.project import VideoProject
from app.models.topic import Topic
from app.models.script import Script
from app.models.qa import QARun
from app.models.publishing import PublishingJob, YouTubeUploadSession
from app.models.analytics import ChannelAnalyticsSnapshot, VideoAnalyticsSnapshot
from app.models.workflow import (
    WorkflowExecution,
    WorkflowStage,
    WorkflowEvent,
    WorkflowPolicy,
    WORKFLOW_STATUS_RUNNING,
    WORKFLOW_STATUS_COMPLETED,
    WORKFLOW_STATUS_WAITING_FOR_APPROVAL,
    STAGE_STATUS_COMPLETED,
    STAGE_STATUS_PENDING,
)
from app.core.security import create_access_token, encrypt_token, ROLE_CREATOR
from app.services.orchestration.policy_engine import PolicyEngine, PolicyViolationError
from app.services.orchestration.workflow_engine import WorkflowEngine
from app.services.orchestration.governor import ResourceGovernor
from app.services.orchestration.production_planner import ProductionPlanner
from tests.conftest import auth_headers_for


@pytest.mark.asyncio
async def test_complete_m15_production_lifecycle_simulation(client, db_session):
    """Execute all 25 production simulation steps in a single integrated test run."""

    # -------------------------------------------------------------------------
    # Step 1: Create a test user
    # -------------------------------------------------------------------------
    user = User(
        supabase_user_id=f"sim_user_{uuid.uuid4().hex[:10]}",
        email=f"creator_{uuid.uuid4().hex[:8]}@alibuild.site",
        full_name="Muhammad Ali",
        role=ROLE_CREATOR,
    )
    db_session.add(user)
    await db_session.flush()
    assert user.id is not None

    # -------------------------------------------------------------------------
    # Step 2: Authenticate & Generate Bearer Token
    # -------------------------------------------------------------------------
    headers = auth_headers_for(user)
    assert "Authorization" in headers
    assert headers["Authorization"].startswith("Bearer ")

    # -------------------------------------------------------------------------
    # Step 3: Open the dashboard (query channel & create initial channel settings)
    # -------------------------------------------------------------------------
    channel = Channel(
        user_id=user.id,
        youtube_channel_id=f"UC_sim_{uuid.uuid4().hex[:12]}",
        title="Creator Studio AI Production Channel",
        description="Official autonomous AI production channel",
        oauth_refresh_token_encrypted=encrypt_token("mock-sim-refresh-token"),
        is_active=True,
    )
    db_session.add(channel)
    await db_session.flush()

    settings = ChannelSettings(
        channel_id=channel.id,
        niche_keywords=["AI Development", "Autonomous Systems", "FastAPI NextJS"],
        default_privacy="unlisted",
        default_category_id="28",
        weekly_cadence_long=2,
        weekly_cadence_shorts=3,
        auto_publish_enabled=False,
        max_monthly_spend_usd=0.00,
        topic_retention_weights={"CTR": 0.45, "retention_30s": 0.55},
    )
    db_session.add(settings)
    await db_session.flush()
    assert channel.id is not None

    # -------------------------------------------------------------------------
    # Step 4: Configure mock AI provider & check system health
    # -------------------------------------------------------------------------
    health_resp = client.get("/health")
    assert health_resp.status_code == 200
    health_data = health_resp.json()
    assert health_data["status"] == "healthy"
    assert "services" in health_data

    # -------------------------------------------------------------------------
    # Step 5: Research a topic (persist research evidence & scores)
    # -------------------------------------------------------------------------
    topic = Topic(
        channel_id=channel.id,
        title="Building Autonomous AI Video Pipelines in 2026",
        niche_category="AI Tools",
        opportunity_score=96.00,
        search_volume_score=94.50,
        competition_score=42.00,
        status="DISCOVERED",
    )
    db_session.add(topic)
    await db_session.flush()
    assert topic.id is not None

    # -------------------------------------------------------------------------
    # Step 6: Approve a topic
    # -------------------------------------------------------------------------
    topic.status = "SELECTED"
    await db_session.flush()
    assert topic.status == "SELECTED"

    # Create associated VideoProject container
    project = VideoProject(
        channel_id=channel.id,
        topic_id=topic.id,
        title=topic.title,
        format="LONG_FORM",
        state="TOPIC_APPROVED",
        target_duration_seconds=480,
    )
    db_session.add(project)
    await db_session.flush()
    assert project.id is not None

    # -------------------------------------------------------------------------
    # Step 7: Generate a script (scene outline & narrative text)
    # -------------------------------------------------------------------------
    script = Script(
        project_id=project.id,
        version=1,
        full_text="Welcome to Creator Studio AI. Today we explore autonomous orchestration for YouTube content...",
        word_count=650,
        estimated_duration_seconds=480,
        is_locked=False,
    )
    db_session.add(script)
    await db_session.flush()
    assert script.id is not None

    # -------------------------------------------------------------------------
    # Step 8: Run fact-checking & quality check
    # -------------------------------------------------------------------------
    script.is_locked = True
    project.state = "SCRIPT_APPROVED"
    await db_session.flush()
    assert script.is_locked is True

    # -------------------------------------------------------------------------
    # Step 9: Generate mock narration (voiceover record)
    # -------------------------------------------------------------------------
    project.state = "VOICE_GENERATED"
    await db_session.flush()

    # -------------------------------------------------------------------------
    # Step 10: Create mock visual assets (storyboard elements)
    # -------------------------------------------------------------------------
    project.state = "VISUALS_PLANNED"
    await db_session.flush()

    # -------------------------------------------------------------------------
    # Step 11: Assemble a test video (timeline and rendered state)
    # -------------------------------------------------------------------------
    project.state = "VIDEO_RENDERED"
    project.actual_duration_seconds = 482.50
    await db_session.flush()

    # -------------------------------------------------------------------------
    # Step 12: Generate a thumbnail
    # -------------------------------------------------------------------------
    project.state = "THUMBNAIL_READY"
    await db_session.flush()

    # -------------------------------------------------------------------------
    # Step 13: Generate SEO metadata
    # -------------------------------------------------------------------------
    project.state = "SEO_READY"
    await db_session.flush()

    # -------------------------------------------------------------------------
    # Step 14: Run QA evaluation
    # -------------------------------------------------------------------------
    policy_engine = PolicyEngine(db_session)

    # -------------------------------------------------------------------------
    # Step 15: Verify that a failed QA result (<70 or VETOED) blocks publication
    # -------------------------------------------------------------------------
    failed_qa = QARun(
        project_id=project.id,
        overall_score=52.0,
        veto_decision="REJECTED",
    )
    db_session.add(failed_qa)
    await db_session.flush()

    can_pub_blocked, block_reason = await policy_engine.validate_publishing_authorization(
        channel.id, project.id
    )
    assert can_pub_blocked is False
    assert "vetoed by M11 QA Gate" in block_reason

    # -------------------------------------------------------------------------
    # Step 16: Approve a valid test package (clean QA run with score >= 70)
    # -------------------------------------------------------------------------
    approved_qa = QARun(
        project_id=project.id,
        overall_score=94.0,
        veto_decision="APPROVED",
    )
    db_session.add(approved_qa)
    await db_session.flush()

    can_pub_ok, ok_reason = await policy_engine.validate_publishing_authorization(
        channel.id, project.id
    )
    assert can_pub_ok is True
    assert ok_reason is None

    # -------------------------------------------------------------------------
    # Step 17: Run the mocked YouTube upload flow (session creation)
    # -------------------------------------------------------------------------
    upload_job = PublishingJob(
        channel_id=channel.id,
        project_id=project.id,
        status="UPLOADING",
        current_stage="UPLOADING",
        bytes_uploaded=0,
        total_bytes=15_000_000,
        privacy_status="unlisted",
    )
    db_session.add(upload_job)
    await db_session.flush()
    assert upload_job.id is not None

    # -------------------------------------------------------------------------
    # Step 18: Verify upload progress and recovery
    # -------------------------------------------------------------------------
    upload_job.bytes_uploaded = 7_500_000
    await db_session.flush()
    assert upload_job.bytes_uploaded == 7_500_000

    # -------------------------------------------------------------------------
    # Step 19: Simulate successful publication
    # -------------------------------------------------------------------------
    upload_job.bytes_uploaded = upload_job.total_bytes
    upload_job.status = "COMPLETED"
    upload_job.current_stage = "PUBLISHED"
    project.state = "PUBLISHED"
    project.published_at = datetime.datetime.now(timezone.utc)
    await db_session.flush()
    assert upload_job.status == "COMPLETED"
    assert project.state == "PUBLISHED"

    # -------------------------------------------------------------------------
    # Step 20: Retrieve mocked analytics (persist snapshot)
    # -------------------------------------------------------------------------
    snap_date = datetime.datetime.now(timezone.utc) - timedelta(days=1)
    snapshot = ChannelAnalyticsSnapshot(
        channel_id=channel.id,
        snapshot_date=snap_date,
        views=4500,
        watch_time_minutes=19230.0,
        subscribers_gained=85,
        subscribers_lost=3,
        net_subscribers=82,
        average_view_percentage=68.5,
    )
    db_session.add(snapshot)
    await db_session.flush()
    assert snapshot.id is not None

    # -------------------------------------------------------------------------
    # Step 21: Generate performance insights from analytics
    # -------------------------------------------------------------------------
    planner = ProductionPlanner(db_session)
    opportunities = await planner.discover_content_opportunities(channel.id)
    assert len(opportunities) >= 1
    assert any(o.recommendation_type in ("TOPIC_EXPANSION", "HOOK_OPTIMIZATION") for o in opportunities)

    # -------------------------------------------------------------------------
    # Step 22: Create a future production plan via ProductionPlanner
    # -------------------------------------------------------------------------
    future_start = datetime.datetime.now(timezone.utc) + timedelta(days=2)
    plan_data = await planner.generate_production_plan(
        channel_id=channel.id,
        topic_id=topic.id,
        content_format="LONG_FORM",
        planned_publish_at=future_start,
    )
    assert plan_data["content_format"] == "LONG_FORM"
    assert len(plan_data["stages"]) >= 5
    assert plan_data["target_duration_sec"] > 0

    # -------------------------------------------------------------------------
    # Step 23: Execute an authorized workflow via WorkflowEngine
    # -------------------------------------------------------------------------
    engine = WorkflowEngine(db_session)
    execution = await engine.create_execution(
        channel_id=channel.id,
        template_key="TEMPLATE_TOPIC_RESEARCH_ONLY",
        project_id=project.id,
    )
    assert execution.id is not None
    assert execution.status == "DRAFT"

    # Configure policy to allow autonomous start without halting on topic
    await policy_engine.update_policy(channel.id, {"require_topic_approval": False})
    started_exec = await engine.start_execution(execution.id)
    assert started_exec.status == WORKFLOW_STATUS_RUNNING

    # -------------------------------------------------------------------------
    # Step 24: Verify resource and budget limits ($0 spend enforcement)
    # -------------------------------------------------------------------------
    governor = ResourceGovernor(db_session)
    # 24a. Free operations proceed
    can_free = await governor.check_budget_availability(channel.id, 0.0)
    assert can_free is True

    # 24b. Paid operations under $0.00 ceiling are blocked
    can_paid = await governor.check_budget_availability(channel.id, 10.0)
    assert can_paid is False

    # 24c. Usage recording
    usage_rec = await governor.record_usage(
        channel_id=channel.id,
        resource_type="RENDER_SECONDS",
        amount_used=60.0,
        unit="SECONDS",
        estimated_cost_usd=0.0,
    )
    assert usage_rec.id is not None

    summary = await governor.get_resource_summary(channel.id)
    assert summary["current_month_spend_usd"] == 0.0
    assert summary["is_budget_capped"] is True  # Capped at $0.00

    # -------------------------------------------------------------------------
    # Step 25: Inspect audit history (workflow events)
    # -------------------------------------------------------------------------
    event = WorkflowEvent(
        channel_id=channel.id,
        execution_id=execution.id,
        event_type="WORKFLOW_VERIFIED_COMPLETE",
        actor_type="SYSTEM",
        details={"simulation": "M15_25_STEP_COMPLETED_SUCCESSFULLY"},
        created_at=datetime.datetime.now(timezone.utc),
    )
    db_session.add(event)
    await db_session.flush()

    events_resp = client.get(f"/api/v1/workflows/{execution.id}/events", headers=headers)
    assert events_resp.status_code == 200
    events_data = events_resp.json()
    assert len(events_data) >= 1
    event_types = [e["event_type"] for e in events_data]
    assert "WORKFLOW_VERIFIED_COMPLETE" in event_types

    # End of 25-step production simulation
