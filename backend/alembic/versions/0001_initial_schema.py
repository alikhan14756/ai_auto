"""Initial schema migration: 21 core relational tables.

Revision ID: 0001
Revises: None
Create Date: 2026-11-07 18:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. users
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("supabase_user_id", sa.String(length=128), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("role", sa.String(length=32), nullable=False, server_default="CREATOR"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_supabase_user_id", "users", ["supabase_user_id"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # 2. prompt_templates
    op.create_table(
        "prompt_templates",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("template_key", sa.String(length=64), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("user_prompt_template", sa.Text(), nullable=False),
        sa.Column("schema_definition", sa.JSON(), nullable=False),
        sa.Column("version", sa.String(length=16), server_default="v1.0.0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_prompt_templates_template_key", "prompt_templates", ["template_key"], unique=True)

    # 3. channels
    op.create_table(
        "channels",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("youtube_channel_id", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("custom_url", sa.String(length=128), nullable=True),
        sa.Column("thumbnail_url", sa.Text(), nullable=True),
        sa.Column("subscriber_count", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("oauth_refresh_token_encrypted", sa.Text(), nullable=False),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_channels_user_id", "channels", ["user_id"])
    op.create_index("ix_channels_youtube_channel_id", "channels", ["youtube_channel_id"], unique=True)

    # 4. audit_logs
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("resource_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])

    # 5. channel_settings
    op.create_table(
        "channel_settings",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("channel_id", sa.Uuid(as_uuid=True), sa.ForeignKey("channels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("niche_keywords", sa.JSON(), nullable=False),
        sa.Column("default_privacy", sa.String(length=32), server_default="unlisted", nullable=False),
        sa.Column("default_category_id", sa.String(length=16), server_default="28", nullable=False),
        sa.Column("weekly_cadence_long", sa.BigInteger(), server_default="2", nullable=False),
        sa.Column("weekly_cadence_shorts", sa.BigInteger(), server_default="3", nullable=False),
        sa.Column("auto_publish_enabled", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("max_monthly_spend_usd", sa.Numeric(precision=8, scale=2), server_default="0.00", nullable=False),
        sa.Column("topic_retention_weights", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_channel_settings_channel_id", "channel_settings", ["channel_id"], unique=True)

    # 6. topics
    op.create_table(
        "topics",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("channel_id", sa.Uuid(as_uuid=True), sa.ForeignKey("channels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("niche_category", sa.String(length=128), nullable=False),
        sa.Column("opportunity_score", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("search_volume_score", sa.Numeric(precision=5, scale=2), server_default="0.00", nullable=False),
        sa.Column("competition_score", sa.Numeric(precision=5, scale=2), server_default="0.00", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="DISCOVERED", nullable=False),
        sa.Column("raw_discovery_payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_topics_channel_id", "topics", ["channel_id"])
    op.create_index("ix_topics_status", "topics", ["status"])

    # 7. automation_jobs
    op.create_table(
        "automation_jobs",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("channel_id", sa.Uuid(as_uuid=True), sa.ForeignKey("channels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_type", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="QUEUED", nullable=False),
        sa.Column("priority", sa.Integer(), server_default="10", nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_retries", sa.Integer(), server_default="3", nullable=False),
        sa.Column("locked_by", sa.String(length=128), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("progress_percentage", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_log", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_automation_jobs_channel_id", "automation_jobs", ["channel_id"])
    op.create_index("ix_automation_jobs_job_type", "automation_jobs", ["job_type"])
    op.create_index("ix_automation_jobs_idempotency_key", "automation_jobs", ["idempotency_key"], unique=True)
    op.create_index("ix_automation_jobs_status", "automation_jobs", ["status"])

    # 8. provider_usages
    op.create_table(
        "provider_usages",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("channel_id", sa.Uuid(as_uuid=True), sa.ForeignKey("channels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider_name", sa.String(length=64), nullable=False),
        sa.Column("model_name", sa.String(length=128), nullable=False),
        sa.Column("input_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("output_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("cost_usd", sa.Numeric(precision=8, scale=6), server_default="0.000000", nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_provider_usages_channel_id", "provider_usages", ["channel_id"])
    op.create_index("ix_provider_usages_provider_name", "provider_usages", ["provider_name"])
    op.create_index("ix_provider_usages_recorded_at", "provider_usages", ["recorded_at"])

    # 9. research_sources
    op.create_table(
        "research_sources",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("topic_id", sa.Uuid(as_uuid=True), sa.ForeignKey("topics.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("source_title", sa.String(length=512), nullable=True),
        sa.Column("extracted_summary", sa.Text(), nullable=False),
        sa.Column("relevance_score", sa.Numeric(precision=4, scale=3), server_default="1.000", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_research_sources_topic_id", "research_sources", ["topic_id"])

    # 10. video_projects
    op.create_table(
        "video_projects",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("channel_id", sa.Uuid(as_uuid=True), sa.ForeignKey("channels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("topic_id", sa.Uuid(as_uuid=True), sa.ForeignKey("topics.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("format", sa.String(length=32), server_default="LONG_FORM", nullable=False),
        sa.Column("state", sa.String(length=64), server_default="IDEA", nullable=False),
        sa.Column("target_duration_seconds", sa.Integer(), server_default="480", nullable=False),
        sa.Column("actual_duration_seconds", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("revision_number", sa.Integer(), server_default="1", nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_video_projects_channel_id", "video_projects", ["channel_id"])
    op.create_index("ix_video_projects_topic_id", "video_projects", ["topic_id"])
    op.create_index("ix_video_projects_state", "video_projects", ["state"])

    # 11. scripts
    op.create_table(
        "scripts",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", sa.Uuid(as_uuid=True), sa.ForeignKey("video_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("full_text", sa.Text(), nullable=False),
        sa.Column("word_count", sa.Integer(), nullable=False),
        sa.Column("estimated_duration_seconds", sa.Integer(), nullable=False),
        sa.Column("is_locked", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_scripts_project_id", "scripts", ["project_id"])

    # 12. scenes
    op.create_table(
        "scenes",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", sa.Uuid(as_uuid=True), sa.ForeignKey("video_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scene_order", sa.Integer(), nullable=False),
        sa.Column("narration_text", sa.Text(), nullable=False),
        sa.Column("visual_archetype", sa.String(length=64), nullable=False),
        sa.Column("visual_directive", sa.Text(), nullable=False),
        sa.Column("target_url", sa.Text(), nullable=True),
        sa.Column("duration_seconds", sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_scenes_project_id", "scenes", ["project_id"])

    # 13. thumbnails
    op.create_table(
        "thumbnails",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", sa.Uuid(as_uuid=True), sa.ForeignKey("video_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("variant_code", sa.String(length=16), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("headline_text", sa.String(length=128), nullable=False),
        sa.Column("accent_color_hex", sa.String(length=16), nullable=False),
        sa.Column("is_selected", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_thumbnails_project_id", "thumbnails", ["project_id"])

    # 14. render_jobs
    op.create_table(
        "render_jobs",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", sa.Uuid(as_uuid=True), sa.ForeignKey("video_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resolution", sa.String(length=32), server_default="1080p", nullable=False),
        sa.Column("output_video_path", sa.Text(), nullable=True),
        sa.Column("render_duration_seconds", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("ffmpeg_command_executed", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="QUEUED", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_render_jobs_project_id", "render_jobs", ["project_id"])
    op.create_index("ix_render_jobs_status", "render_jobs", ["status"])

    # 15. publishing_jobs
    op.create_table(
        "publishing_jobs",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", sa.Uuid(as_uuid=True), sa.ForeignKey("video_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel_id", sa.Uuid(as_uuid=True), sa.ForeignKey("channels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scheduled_publish_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("privacy_status", sa.String(length=32), server_default="unlisted", nullable=False),
        sa.Column("synthetic_media_declared", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="PENDING", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_publishing_jobs_project_id", "publishing_jobs", ["project_id"])
    op.create_index("ix_publishing_jobs_channel_id", "publishing_jobs", ["channel_id"])
    op.create_index("ix_publishing_jobs_status", "publishing_jobs", ["status"])

    # 16. script_claims
    op.create_table(
        "script_claims",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("script_id", sa.Uuid(as_uuid=True), sa.ForeignKey("scripts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", sa.Uuid(as_uuid=True), sa.ForeignKey("video_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_text", sa.Text(), nullable=False),
        sa.Column("extracted_entity", sa.String(length=255), nullable=True),
        sa.Column("claim_type", sa.String(length=64), nullable=False),
        sa.Column("is_verified", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("confidence_score", sa.Numeric(precision=4, scale=3), server_default="0.000", nullable=False),
        sa.Column("citation_url", sa.Text(), nullable=True),
        sa.Column("citation_snippet", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_script_claims_script_id", "script_claims", ["script_id"])
    op.create_index("ix_script_claims_project_id", "script_claims", ["project_id"])

    # 17. media_assets
    op.create_table(
        "media_assets",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("scene_id", sa.Uuid(as_uuid=True), sa.ForeignKey("scenes.id", ondelete="SET NULL"), nullable=True),
        sa.Column("project_id", sa.Uuid(as_uuid=True), sa.ForeignKey("video_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("asset_type", sa.String(length=32), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256_hash", sa.String(length=64), nullable=False),
        sa.Column("license_type", sa.String(length=64), nullable=False),
        sa.Column("is_verified", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_media_assets_scene_id", "media_assets", ["scene_id"])
    op.create_index("ix_media_assets_project_id", "media_assets", ["project_id"])

    # 18. voiceovers
    op.create_table(
        "voiceovers",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("scene_id", sa.Uuid(as_uuid=True), sa.ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", sa.Uuid(as_uuid=True), sa.ForeignKey("video_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tts_engine", sa.String(length=64), nullable=False),
        sa.Column("voice_id", sa.String(length=128), nullable=False),
        sa.Column("audio_storage_path", sa.Text(), nullable=False),
        sa.Column("duration_seconds", sa.Numeric(precision=6, scale=3), nullable=False),
        sa.Column("word_timestamps", sa.JSON(), nullable=False),
        sa.Column("loudness_lufs", sa.Numeric(precision=4, scale=2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_voiceovers_scene_id", "voiceovers", ["scene_id"], unique=True)
    op.create_index("ix_voiceovers_project_id", "voiceovers", ["project_id"])

    # 19. quality_reports
    op.create_table(
        "quality_reports",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", sa.Uuid(as_uuid=True), sa.ForeignKey("video_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("render_job_id", sa.Uuid(as_uuid=True), sa.ForeignKey("render_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("all_checks_passed", sa.Boolean(), nullable=False),
        sa.Column("black_frame_duration_max", sa.Numeric(precision=6, scale=3), nullable=False),
        sa.Column("freeze_duration_max", sa.Numeric(precision=6, scale=3), nullable=False),
        sa.Column("integrated_loudness_lufs", sa.Numeric(precision=4, scale=2), nullable=False),
        sa.Column("max_true_peak_dbtp", sa.Numeric(precision=4, scale=2), nullable=False),
        sa.Column("unverified_claims_count", sa.Integer(), nullable=False),
        sa.Column("transcript_similarity_ratio", sa.Numeric(precision=4, scale=3), nullable=False),
        sa.Column("diagnostic_details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_quality_reports_project_id", "quality_reports", ["project_id"])
    op.create_index("ix_quality_reports_render_job_id", "quality_reports", ["render_job_id"])

    # 20. youtube_videos
    op.create_table(
        "youtube_videos",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("publishing_job_id", sa.Uuid(as_uuid=True), sa.ForeignKey("publishing_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", sa.Uuid(as_uuid=True), sa.ForeignKey("video_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("youtube_video_id", sa.String(length=64), nullable=False),
        sa.Column("published_video_url", sa.Text(), nullable=False),
        sa.Column("view_count", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("like_count", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("comment_count", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_youtube_videos_publishing_job_id", "youtube_videos", ["publishing_job_id"], unique=True)
    op.create_index("ix_youtube_videos_project_id", "youtube_videos", ["project_id"])
    op.create_index("ix_youtube_videos_youtube_video_id", "youtube_videos", ["youtube_video_id"], unique=True)

    # 21. analytics_snapshots
    op.create_table(
        "analytics_snapshots",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("youtube_video_id", sa.String(length=64), sa.ForeignKey("youtube_videos.youtube_video_id", ondelete="CASCADE"), nullable=False),
        sa.Column("snapshot_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("views", sa.BigInteger(), nullable=False),
        sa.Column("watch_time_minutes", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("average_view_duration_seconds", sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column("click_through_rate", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("retention_at_30s", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_analytics_snapshots_youtube_video_id", "analytics_snapshots", ["youtube_video_id"])
    op.create_index("ix_analytics_snapshots_snapshot_time", "analytics_snapshots", ["snapshot_time"])


def downgrade() -> None:
    # Drop in strict reverse dependency order
    op.drop_table("analytics_snapshots")
    op.drop_table("youtube_videos")
    op.drop_table("quality_reports")
    op.drop_table("voiceovers")
    op.drop_table("media_assets")
    op.drop_table("script_claims")
    op.drop_table("publishing_jobs")
    op.drop_table("render_jobs")
    op.drop_table("thumbnails")
    op.drop_table("scenes")
    op.drop_table("scripts")
    op.drop_table("video_projects")
    op.drop_table("research_sources")
    op.drop_table("provider_usages")
    op.drop_table("automation_jobs")
    op.drop_table("topics")
    op.drop_table("channel_settings")
    op.drop_table("audit_logs")
    op.drop_table("channels")
    op.drop_table("prompt_templates")
    op.drop_table("users")
