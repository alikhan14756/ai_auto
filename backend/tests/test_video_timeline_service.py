"""Unit and component tests for TimelineService."""

from decimal import Decimal
import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.channel import Channel
from app.models.project import VideoProject
from app.models.storyboard import Storyboard
from app.models.scene import Scene
from app.models.timeline import VideoTimeline, TimelineScene
from app.models.user import User
from app.services.timeline import TimelineService


@pytest.mark.asyncio
async def test_create_and_reorder_timeline(db_session: AsyncSession, test_user, test_channel):
    """Test full lifecycle of timeline creation, duration recalculation, and scene reordering."""
    test_project = VideoProject(
        id=uuid.uuid4(),
        channel_id=test_channel.id,
        title="Timeline Test Project",
        format="LONG_FORM",
        state="IDEA",
    )
    db_session.add(test_project)
    await db_session.commit()

    # 1. Setup Storyboard with 3 scenes
    storyboard = Storyboard(
        id=uuid.uuid4(),
        project_id=test_project.id,
        version=1,
        status="APPROVED",
        aspect_ratio="16:9",
        scene_count=3,
        approved_scene_count=3,
    )
    db_session.add(storyboard)
    await db_session.flush()

    s1 = Scene(
        id=uuid.uuid4(),
        project_id=test_project.id,
        storyboard_id=storyboard.id,
        scene_order=1,
        duration_seconds=Decimal("4.00"),
        narration_text="Scene one narration",
        visual_archetype="CONCEPT_EXPLANATION",
        visual_directive="Display conceptual overview",
    )
    s2 = Scene(
        id=uuid.uuid4(),
        project_id=test_project.id,
        storyboard_id=storyboard.id,
        scene_order=2,
        duration_seconds=Decimal("6.00"),
        narration_text="Scene two narration",
        visual_archetype="CODE_TERMINAL",
        visual_directive="Display terminal code",
    )
    s3 = Scene(
        id=uuid.uuid4(),
        project_id=test_project.id,
        storyboard_id=storyboard.id,
        scene_order=3,
        duration_seconds=Decimal("5.00"),
        narration_text="Scene three narration",
        visual_archetype="INFOGRAPHIC",
        visual_directive="Show performance graph",
    )
    db_session.add_all([s1, s2, s3])
    await db_session.commit()

    # 2. Create timeline from storyboard
    timeline = await TimelineService.create_timeline_from_storyboard(
        db=db_session,
        storyboard_id=storyboard.id,
        user=test_user,
        aspect_ratio="16:9",
        fps=30,
    )

    assert timeline.project_id == test_project.id
    assert timeline.total_duration_seconds == Decimal("15.00")
    assert len(timeline.timeline_scenes) == 3
    assert len(timeline.captions) == 1

    # Check sequential start/end times
    scenes = timeline.timeline_scenes
    assert scenes[0].start_time_seconds == Decimal("0.00")
    assert scenes[0].end_time_seconds == Decimal("4.00")
    assert scenes[1].start_time_seconds == Decimal("4.00")
    assert scenes[1].end_time_seconds == Decimal("10.00")
    assert scenes[2].start_time_seconds == Decimal("10.00")
    assert scenes[2].end_time_seconds == Decimal("15.00")

    # 3. Update scene 1 duration to 8.0 seconds and verify downstream recalculation
    updated_scene = await TimelineService.update_timeline_scene(
        db=db_session,
        timeline_id=timeline.id,
        timeline_scene_id=scenes[0].id,
        user=test_user,
        duration_seconds=8.0,
    )
    assert updated_scene.duration_seconds == Decimal("8.00")
    assert updated_scene.end_time_seconds == Decimal("8.00")

    # Re-fetch timeline to verify ripple effect
    tl_fresh = await TimelineService.verify_timeline_ownership(db_session, timeline.id, test_user)
    assert tl_fresh.total_duration_seconds == Decimal("19.00")

    # 4. Reorder scenes: put scene 3 first, then scene 1, then scene 2
    new_order = [scenes[2].id, scenes[0].id, scenes[1].id]
    reordered_tl = await TimelineService.reorder_timeline_scenes(
        db=db_session,
        timeline_id=timeline.id,
        new_scene_order_ids=new_order,
        user=test_user,
    )

    reordered = sorted(reordered_tl.timeline_scenes, key=lambda s: s.sequence_number)
    assert reordered[0].id == scenes[2].id
    assert reordered[0].start_time_seconds == Decimal("0.00")
    assert reordered[0].duration_seconds == Decimal("5.00")
    assert reordered[0].end_time_seconds == Decimal("5.00")


@pytest.mark.asyncio
async def test_timeline_service_tenant_isolation(db_session: AsyncSession, test_user, test_channel):
    """Verify unauthorized users cannot access or edit other channels' timelines."""
    test_project = VideoProject(
        id=uuid.uuid4(),
        channel_id=test_channel.id,
        title="Tenant Project",
        format="LONG_FORM",
        state="IDEA",
    )
    db_session.add(test_project)
    await db_session.commit()

    # Create another user
    other_user = User(
        id=uuid.uuid4(),
        email="other_creator@example.com",
        supabase_user_id=f"other-sub-{uuid.uuid4()}",
        full_name="Other Creator",
        role="CREATOR",
    )
    db_session.add(other_user)
    await db_session.commit()

    timeline = VideoTimeline(
        id=uuid.uuid4(),
        project_id=test_project.id,
        aspect_ratio="16:9",
        fps=30,
        width=1920,
        height=1080,
        total_duration_seconds=Decimal("10.00"),
        status="READY",
    )
    db_session.add(timeline)
    await db_session.commit()

    with pytest.raises(PermissionError):
        await TimelineService.verify_timeline_ownership(db_session, timeline.id, other_user)
