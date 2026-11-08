"""Automated migration verification tests: fresh installation and existing data preservation during upgrade."""

import os
import tempfile
import uuid
import pytest
from sqlalchemy import create_engine, text, inspect
from alembic.config import Config
from alembic import command


@pytest.fixture
def temp_alembic_db():
    """Create an isolated temporary SQLite database for migration lifecycle testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    sync_url = f"sqlite:///{db_path}"
    
    # Configure Alembic
    base_dir = os.path.dirname(os.path.dirname(__file__))
    alembic_ini = os.path.join(base_dir, "alembic.ini")
    
    cfg = Config(alembic_ini)
    cfg.set_main_option("script_location", os.path.join(base_dir, "alembic"))
    cfg.set_main_option("sqlalchemy.url", sync_url)

    yield {"path": db_path, "url": sync_url, "config": cfg}

    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except OSError:
            pass


def test_migration_fresh_installation_head(temp_alembic_db):
    """Verify that a brand new database installs completely from zero to head with all tables."""
    cfg = temp_alembic_db["config"]
    engine = create_engine(temp_alembic_db["url"])

    # Run upgrade head from scratch
    command.upgrade(cfg, "head")

    inspector = inspect(engine)
    tables = inspector.get_table_names()

    # Verify key tables from initial schema through latest revisions exist
    expected_tables = [
        "users",
        "channels",
        "channel_settings",
        "video_projects",
        "scripts",
        "script_claims",
        "narration_tracks",
        "media_assets",
        "video_timelines",
        "thumbnails",
        "video_metadata_drafts",
        "publication_packages",
        "qa_runs",
        "publishing_jobs",
        "channel_analytics_snapshots",
        "workflow_policies",
        "workflow_executions",
        "workflow_stages",
        "alembic_version",
    ]

    for table in expected_tables:
        assert table in tables, f"Expected table '{table}' not found in fresh migration."


def test_migration_upgrade_preserves_existing_data(temp_alembic_db):
    """Verify that upgrading an existing database from 0009 to 0010 preserves existing data without data loss."""
    cfg = temp_alembic_db["config"]
    engine = create_engine(temp_alembic_db["url"])

    # 1. Migrate up to revision 0009
    command.upgrade(cfg, "0009")

    # 2. Insert existing production-like records
    test_user_id = uuid.uuid4().hex
    test_channel_id = uuid.uuid4().hex
    test_project_id = uuid.uuid4().hex

    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO users (id, supabase_user_id, email, full_name, role, created_at, updated_at) "
                "VALUES (:id, :supa, :email, :name, :role, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ),
            {
                "id": test_user_id,
                "supa": "supa_pre_migration_123",
                "email": "pre_migration@example.com",
                "name": "Pre-Migration User",
                "role": "CREATOR",
            },
        )
        conn.execute(
            text(
                "INSERT INTO channels (id, user_id, youtube_channel_id, title, oauth_refresh_token_encrypted, is_active, subscriber_count, created_at, updated_at) "
                "VALUES (:id, :uid, :ytid, :title, :token, 1, 100, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ),
            {
                "id": test_channel_id,
                "uid": test_user_id,
                "ytid": "UC_pre_migration_channel",
                "title": "Legacy Channel",
                "token": "encrypted_token_value_pre_0010",
            },
        )
        conn.execute(
            text(
                "INSERT INTO video_projects (id, channel_id, title, state, target_duration_seconds, created_at, updated_at) "
                "VALUES (:id, :cid, :title, :state, 300, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ),
            {
                "id": test_project_id,
                "cid": test_channel_id,
                "title": "Existing Pre-Migration Video Project",
                "state": "PUBLISHED",
            },
        )

    # 3. Perform upgrade to latest head (revision 0010)
    command.upgrade(cfg, "head")

    # 4. Verify existing records remain 100% intact and uncorrupted
    with engine.connect() as conn:
        user_row = conn.execute(
            text("SELECT email, full_name FROM users WHERE id = :id"),
            {"id": test_user_id},
        ).fetchone()
        assert user_row is not None
        assert user_row[0] == "pre_migration@example.com"
        assert user_row[1] == "Pre-Migration User"

        channel_row = conn.execute(
            text("SELECT title, oauth_refresh_token_encrypted FROM channels WHERE id = :id"),
            {"id": test_channel_id},
        ).fetchone()
        assert channel_row is not None
        assert channel_row[0] == "Legacy Channel"
        assert channel_row[1] == "encrypted_token_value_pre_0010"

        project_row = conn.execute(
            text("SELECT title, state FROM video_projects WHERE id = :id"),
            {"id": test_project_id},
        ).fetchone()
        assert project_row is not None
        assert project_row[0] == "Existing Pre-Migration Video Project"
        assert project_row[1] == "PUBLISHED"

    # 5. Verify that new tables added in 0010 are accessible and operational
    with engine.begin() as conn:
        test_policy_id = uuid.uuid4().hex
        conn.execute(
            text(
                "INSERT INTO workflow_policies (id, channel_id, automation_level, max_workflows_per_week, max_concurrent_workflows, max_monthly_budget_usd, created_at, updated_at) "
                "VALUES (:id, :cid, 1, 5, 2, 0.0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ),
            {
                "id": test_policy_id,
                "cid": test_channel_id,
            },
        )
        policy_row = conn.execute(
            text("SELECT automation_level, max_monthly_budget_usd FROM workflow_policies WHERE id = :id"),
            {"id": test_policy_id},
        ).fetchone()
        assert policy_row is not None
        assert policy_row[0] == 1
        assert policy_row[1] == 0.0
