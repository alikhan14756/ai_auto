"""Tests for VisualPlanningService (storyboard generation, archetypes, scene ordering)."""

import pytest
import uuid
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.channel import Channel
from app.models.project import VideoProject
from app.models.script import Script
from app.models.scene import Scene
from app.models.voice import NarrationTrack, Voiceover
from app.models.storyboard import Storyboard
from app.models.media import MediaAsset
from app.services.visual_planning import VisualPlanningService


def test_keyword_extraction():
    """Verify technical keyword extraction strips common stopwords."""
    text = "In this video we will build a FastAPI microservice with PostgreSQL and asyncpg."
    keywords = VisualPlanningService.extract_keywords(text, max_keywords=5)
    assert "fastapi" in keywords
    assert "microservice" in keywords
    assert "postgresql" in keywords
    assert "asyncpg" in keywords
    assert "the" not in keywords
    assert "with" not in keywords


def test_archetype_inference():
    """Verify scene purpose and asset type classification based on narrative content."""
    # First scene is hook
    hook_cls = VisualPlanningService.infer_visual_purpose_and_type(
        scene_index=1,
        total_scenes=4,
        directive="High energy tech hook",
        narration="Here is why your code is slow.",
    )
    assert hook_cls["visual_purpose"] == "HOOK_ENGAGEMENT"

    # Terminal scene
    code_cls = VisualPlanningService.infer_visual_purpose_and_type(
        scene_index=2,
        total_scenes=4,
        directive="Show Python syntax and async function in terminal",
        narration="Let's write the code for our database session.",
    )
    assert code_cls["suggested_asset_type"] == "CODE_DEMONSTRATION"

    # Last scene is summary
    sum_cls = VisualPlanningService.infer_visual_purpose_and_type(
        scene_index=4,
        total_scenes=4,
        directive="Wrap up and call to action",
        narration="Subscribe for more deep dives into Python architecture.",
    )
    assert sum_cls["visual_purpose"] == "SUMMARY"


@pytest.mark.asyncio
async def test_generate_storyboard_end_to_end(db_session: AsyncSession):
    """Verify generate_storyboard creates a structured Storyboard and links scenes with timings."""
    # 1. Setup Channel and Project
    channel_id = uuid.uuid4()
    project_id = uuid.uuid4()
    channel = Channel(
        id=channel_id,
        user_id=uuid.uuid4(),
        youtube_channel_id=f"UC_{uuid.uuid4().hex[:12]}",
        title="Visual Tech Channel",
        oauth_refresh_token_encrypted="mock_token",
    )
    project = VideoProject(
        id=project_id,
        channel_id=channel_id,
        title="Building Real-time AI Storyboards",
        format="LONG_FORM",
        state="SCRIPT_APPROVED",
    )
    script = Script(
        project_id=project_id,
        version=1,
        full_text="Scene one. Scene two code. Scene three summary.",
        word_count=9,
        estimated_duration_seconds=5,
    )
    db_session.add_all([channel, project, script])
    await db_session.flush()

    # 2. Add Scenes
    s1 = Scene(
        project_id=project_id,
        scene_order=1,
        narration_text="Welcome to Creator Studio AI visual planning.",
        visual_archetype="INFOGRAPHIC",
        visual_directive="Show sleek platform architecture overview",
        duration_seconds=Decimal("3.50"),
    )
    s2 = Scene(
        project_id=project_id,
        scene_order=2,
        narration_text="Here is the terminal command to run your database migrations.",
        visual_archetype="CODE_TERMINAL",
        visual_directive="Display terminal window typing alembic upgrade head",
        duration_seconds=Decimal("4.20"),
    )
    db_session.add_all([s1, s2])
    await db_session.commit()

    # 3. Generate Storyboard
    planner = VisualPlanningService()
    storyboard = await planner.generate_storyboard(db=db_session, project_id=project_id)

    assert storyboard is not None
    assert storyboard.project_id == project_id
    assert storyboard.aspect_ratio == "16:9"
    assert storyboard.scene_count == 2
    assert len(storyboard.scenes) == 2

    first_scene = storyboard.scenes[0]
    assert first_scene.visual_purpose == "HOOK_ENGAGEMENT"
    assert len(first_scene.search_keywords) > 0
    assert "visual" in first_scene.image_prompt.lower() or "tech" in first_scene.image_prompt.lower()

    second_scene = storyboard.scenes[1]
    assert second_scene.suggested_asset_type == "CODE_DEMONSTRATION"


@pytest.mark.asyncio
async def test_update_and_approve_storyboard(db_session: AsyncSession):
    """Verify scene directive updating, reordering, and storyboard approval workflow."""
    channel_id = uuid.uuid4()
    project_id = uuid.uuid4()
    channel = Channel(
        id=channel_id,
        user_id=uuid.uuid4(),
        youtube_channel_id=f"UC_{uuid.uuid4().hex[:12]}",
        title="Approval Channel",
        oauth_refresh_token_encrypted="mock_token",
    )
    project = VideoProject(
        id=project_id,
        channel_id=channel_id,
        title="Approval Flow Project",
        format="SHORTS",
        state="SCRIPT_APPROVED",
    )
    db_session.add_all([channel, project])
    await db_session.flush()

    s1 = Scene(
        project_id=project_id,
        scene_order=1,
        narration_text="Scene one for mobile shorts.",
        visual_archetype="INFOGRAPHIC",
        visual_directive="Show intro graphic",
        duration_seconds=Decimal("2.00"),
    )
    s2 = Scene(
        project_id=project_id,
        scene_order=2,
        narration_text="Scene two for mobile shorts.",
        visual_archetype="INFOGRAPHIC",
        visual_directive="Show outro graphic",
        duration_seconds=Decimal("2.00"),
    )
    db_session.add_all([s1, s2])
    await db_session.commit()

    planner = VisualPlanningService()
    sb = await planner.generate_storyboard(db=db_session, project_id=project_id)
    assert sb.aspect_ratio == "9:16"

    # Update scene
    updated_s1 = await planner.update_scene(
        db=db_session,
        scene_id=s1.id,
        updates={"visual_directive": "Updated high energy mobile intro", "transition": "ZOOM_IN"},
    )
    assert updated_s1.visual_directive == "Updated high energy mobile intro"
    assert updated_s1.transition == "ZOOM_IN"

    # Reorder scenes
    reordered = await planner.reorder_scenes(db=db_session, storyboard_id=sb.id, ordered_scene_ids=[s2.id, s1.id])
    assert reordered[0].id == s2.id
    assert reordered[0].scene_order == 1
    assert reordered[1].id == s1.id
    assert reordered[1].scene_order == 2

    # Approve storyboard
    approved_sb = await planner.approve_storyboard(db=db_session, storyboard_id=sb.id)
    assert approved_sb.status == "APPROVED"
    assert approved_sb.approved_scene_count == 2
    assert approved_sb.project.state == "STORYBOARD_APPROVED"


@pytest.mark.asyncio
async def test_approve_storyboard_licensing_gate_rejects_unverified_media(db_session: AsyncSession):
    """Verify approve_storyboard blocks approval when a scene has unverified or restricted media."""
    channel_id = uuid.uuid4()
    project_id = uuid.uuid4()
    channel = Channel(
        id=channel_id,
        user_id=uuid.uuid4(),
        youtube_channel_id=f"UC_{uuid.uuid4().hex[:12]}",
        title="Gate Channel",
        oauth_refresh_token_encrypted="mock_token",
    )
    project = VideoProject(
        id=project_id,
        channel_id=channel_id,
        title="Gate Project",
        state="SCRIPT_APPROVED",
    )
    scene = Scene(
        project_id=project_id,
        scene_order=1,
        narration_text="Scene with restricted media.",
        visual_archetype="INFOGRAPHIC",
        visual_directive="Display unverified asset",
        duration_seconds=Decimal("3.00"),
    )
    unverified_asset = MediaAsset(
        channel_id=channel_id,
        project_id=project_id,
        title="Unverified Media Asset",
        asset_category="EXTERNAL_STOCK",
        source_provider="MOCK",
        storage_path="media/mock.png",
        file_size_bytes=1000,
        sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        license_type="CUSTOM",
        license_status="LICENSE_REVIEW_REQUIRED",
    )
    db_session.add_all([channel, project, scene, unverified_asset])
    await db_session.flush()

    planner = VisualPlanningService()
    sb = await planner.generate_storyboard(db=db_session, project_id=project_id)

    # Assign the unverified asset to scene
    scene.selected_asset_id = unverified_asset.id
    await db_session.commit()

    # Attempting to approve storyboard must raise ValueError
    with pytest.raises(ValueError, match="requires license review"):
        await planner.approve_storyboard(db=db_session, storyboard_id=sb.id)
