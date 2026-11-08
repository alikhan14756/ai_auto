"""Tests for Production Planner, Opportunity Engine, and Timezone Calendar."""

import datetime
from datetime import timezone, timedelta
import pytest
from app.models.topic import Topic
from app.models.workflow import WorkflowExecution, WORKFLOW_STATUS_RUNNING
from app.models.analytics import ChannelAnalyticsSnapshot
from app.services.orchestration.production_planner import ProductionPlanner


@pytest.mark.asyncio
async def test_generate_production_plan_long_form_and_shorts(db_session, test_channel):
    """Verify production plan generation builds format-specific durations and prerequisites."""
    planner = ProductionPlanner(db_session)

    topic = Topic(
        channel_id=test_channel.id,
        title="10x Developer Productivity Hacks",
        niche_category="AI Tools",
        opportunity_score=92.50,
        search_volume_score=85.00,
        competition_score=40.00,
        status="APPROVED",
    )
    db_session.add(topic)
    await db_session.flush()

    # 1. Long-form plan
    long_plan = await planner.generate_production_plan(test_channel.id, topic.id, "LONG_FORM")
    assert long_plan["content_format"] == "LONG_FORM"
    assert long_plan["target_duration_sec"] == 480
    assert long_plan["prerequisites_met"] is True
    assert len(long_plan["stages"]) == 8

    # 2. Shorts plan
    shorts_plan = await planner.generate_production_plan(test_channel.id, topic.id, "SHORTS")
    assert shorts_plan["content_format"] == "SHORTS"
    assert shorts_plan["target_duration_sec"] == 45
    assert shorts_plan["prerequisites_met"] is True


@pytest.mark.asyncio
async def test_prerequisite_validation_duplicate_detection(db_session, test_channel):
    """Verify duplicate active workflow detection halts conflicting plan execution."""
    planner = ProductionPlanner(db_session)

    topic = Topic(
        channel_id=test_channel.id,
        title="Duplicate Topic Test",
        niche_category="AI Tools",
        opportunity_score=88.00,
        status="APPROVED",
    )
    db_session.add(topic)
    await db_session.flush()

    # Simulate an active running workflow for this topic
    active_wf = WorkflowExecution(
        channel_id=test_channel.id,
        template_key="TEMPLATE_LONG_FORM",
        status=WORKFLOW_STATUS_RUNNING,
        context_data={"topic_id": str(topic.id)},
    )
    db_session.add(active_wf)
    await db_session.flush()

    plan = await planner.generate_production_plan(test_channel.id, topic.id, "LONG_FORM")
    assert plan["prerequisites_met"] is False
    assert "already exists for topic" in plan["validation_error"]


@pytest.mark.asyncio
async def test_timezone_aware_scheduling_and_conflict_detection(db_session, test_channel):
    """Verify timezone calendar scheduling and conflict detection within 2 hours."""
    planner = ProductionPlanner(db_session)

    now = datetime.datetime.now(timezone.utc)
    start_time = now + timedelta(hours=24)
    publish_time = now + timedelta(hours=48)

    # 1. Schedule initial video
    schedule_1 = await planner.schedule_production(
        channel_id=test_channel.id,
        title="First Scheduled Video",
        content_format="LONG_FORM",
        planned_start_at=start_time,
        planned_publish_at=publish_time,
        timezone_str="UTC",
    )
    assert schedule_1.id is not None
    assert schedule_1.timezone == "UTC"

    # 2. Attempt scheduling another video 1 hour later (within 2h conflict window)
    conflicting_publish = publish_time + timedelta(hours=1)
    with pytest.raises(ValueError) as excinfo:
        await planner.schedule_production(
            channel_id=test_channel.id,
            title="Conflicting Video",
            content_format="LONG_FORM",
            planned_start_at=start_time,
            planned_publish_at=conflicting_publish,
            timezone_str="UTC",
        )
    assert "Schedule conflict" in str(excinfo.value)


@pytest.mark.asyncio
async def test_discover_content_opportunities_from_analytics(db_session, test_channel):
    """Verify synthesis of M13 analytics snapshots into actionable content recommendations."""
    planner = ProductionPlanner(db_session)

    # Seed channel analytics snapshot
    snap = ChannelAnalyticsSnapshot(
        channel_id=test_channel.id,
        snapshot_date=datetime.datetime.now(timezone.utc) - timedelta(days=1),
        views=15000,
        watch_time_minutes=4200.0,
        average_view_percentage=68.5,
        subscribers_gained=240,
        net_subscribers=210,
        raw_metrics={},
    )
    db_session.add(snap)
    await db_session.flush()

    recs = await planner.discover_content_opportunities(test_channel.id)
    assert len(recs) >= 2

    types = [r.recommendation_type for r in recs]
    assert "TOPIC_EXPANSION" in types
    assert "HOOK_OPTIMIZATION" in types

    for r in recs:
        assert r.confidence_score >= 0.80
        assert r.status == "NEW"
        assert r.suggested_action is not None
