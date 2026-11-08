"""Integration tests for NarrationService, Scene Audio Synthesis, and Stitching."""

import pytest
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.channel import Channel, ChannelSettings
from app.models.project import VideoProject
from app.models.scene import Scene
from app.models.script import Script
from app.models.user import User
from app.models.voice import NarrationTrack, Voiceover, VoiceProfile
from app.providers.voice.mock import MockVoiceProvider
from app.providers.voice.factory import set_active_voice_provider
from app.services.narration import NarrationService
from app.services.storage import StorageService


@pytest.fixture(autouse=True)
def ensure_mock_provider():
    set_active_voice_provider(MockVoiceProvider())


@pytest.mark.asyncio
async def test_narration_service_full_generation_and_stitching(db_session: AsyncSession, tmp_path):
    storage = StorageService(base_dir=str(tmp_path))

    user = User(supabase_user_id=f"test-sub-{uuid4()}", email="voice@example.com")
    db_session.add(user)
    await db_session.flush()

    channel = Channel(
        user_id=user.id,
        youtube_channel_id=f"UC_{uuid4().hex[:16]}",
        title="Voice Channel",
        oauth_refresh_token_encrypted="token",
    )
    db_session.add(channel)
    await db_session.flush()

    settings = ChannelSettings(channel_id=channel.id, max_monthly_spend_usd=50.00)
    db_session.add(settings)
    await db_session.flush()

    project = VideoProject(
        channel_id=channel.id,
        title="PostgreSQL Voice Architecture",
        format="LONG_FORM",
        target_duration_seconds=480,
    )
    db_session.add(project)
    await db_session.flush()

    script = Script(
        project_id=project.id,
        version=1,
        full_text="PostgreSQL SKIP LOCKED eliminates queue infrastructure overhead.",
        word_count=8,
        estimated_duration_seconds=4,
        is_locked=True,
    )
    db_session.add(script)
    await db_session.flush()

    scene1 = Scene(
        project_id=project.id,
        scene_order=1,
        narration_text="Most developers think background workers require Redis.",
        visual_archetype="INFOGRAPHIC",
        visual_directive="Redis architecture overview",
        duration_seconds=3,
    )
    scene2 = Scene(
        project_id=project.id,
        scene_order=2,
        narration_text="PostgreSQL 9.5 introduced SELECT FOR UPDATE SKIP LOCKED.",
        visual_archetype="CODE_TERMINAL",
        visual_directive="SQL query terminal",
        duration_seconds=4,
    )
    db_session.add_all([scene1, scene2])
    await db_session.flush()
    scene2_id = scene2.id
    await db_session.commit()

    service = NarrationService(provider=MockVoiceProvider(), storage=storage)
    track = await service.generate_narration_for_project(
        project_id=project.id,
        db=db_session,
    )

    assert track.id is not None
    assert track.project_id == project.id
    assert track.track_version == 1
    assert track.duration_seconds > 0.0
    assert track.file_format == "wav"
    assert track.quality_status in ("PASSED", "WARNING")
    assert len(track.voiceovers) == 2

    # Verify project state
    await db_session.refresh(project)
    assert project.state == "VOICE_GENERATED"

    # Verify master audio exists on disk
    master_bytes = await storage.read_audio_file(track.audio_storage_path)
    assert len(master_bytes) > 100

    # 2. Test Section-Level Audio Regeneration
    updated_track = await service.regenerate_scene_audio(
        narration_track_id=track.id,
        scene_id=scene2_id,
        db=db_session,
        custom_speed=1.1,
    )
    assert updated_track.id == track.id
    assert updated_track.duration_seconds > 0.0

    # 3. Second full generation increments track_version to 2
    track_v2 = await service.generate_narration_for_project(
        project_id=project.id,
        db=db_session,
    )
    assert track_v2.track_version == 2
