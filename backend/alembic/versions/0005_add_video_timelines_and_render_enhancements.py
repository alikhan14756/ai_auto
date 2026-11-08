"""Add video timelines, timeline scenes, captions, and render enhancements.

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-08 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create video_timelines table
    op.create_table(
        "video_timelines",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("aspect_ratio", sa.String(length=16), nullable=False, server_default="16:9"),
        sa.Column("fps", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("width", sa.Integer(), nullable=False, server_default="1920"),
        sa.Column("height", sa.Integer(), nullable=False, server_default="1080"),
        sa.Column("total_duration_seconds", sa.Numeric(precision=8, scale=2), nullable=False, server_default="0.00"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="DRAFT"),
        sa.Column("music_asset_id", sa.Uuid(), nullable=True),
        sa.Column("music_volume", sa.Float(), nullable=False, server_default="0.15"),
        sa.Column("ducking_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("ducking_db", sa.Float(), nullable=False, server_default="-6.0"),
        sa.Column("narration_track_id", sa.Uuid(), nullable=True),
        sa.Column("settings", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["video_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["music_asset_id"], ["media_assets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["narration_track_id"], ["narration_tracks.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_video_timelines_project_id", "video_timelines", ["project_id"])
    op.create_index("ix_video_timelines_status", "video_timelines", ["status"])

    # 2. Create timeline_scenes table
    op.create_table(
        "timeline_scenes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("timeline_id", sa.Uuid(), nullable=False),
        sa.Column("scene_id", sa.Uuid(), nullable=True),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("start_time_seconds", sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column("end_time_seconds", sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column("duration_seconds", sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=True),
        sa.Column("visual_asset_path", sa.Text(), nullable=True),
        sa.Column("transition_type", sa.String(length=32), nullable=False, server_default="cut"),
        sa.Column("transition_duration", sa.Numeric(precision=4, scale=2), nullable=False, server_default="0.50"),
        sa.Column("motion_effect", sa.String(length=32), nullable=False, server_default="zoom_in"),
        sa.Column("motion_intensity", sa.Float(), nullable=False, server_default="1.15"),
        sa.Column("voiceover_segment_id", sa.Uuid(), nullable=True),
        sa.Column("clip_settings", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["timeline_id"], ["video_timelines.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scene_id"], ["scenes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["asset_id"], ["media_assets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["voiceover_segment_id"], ["voiceovers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_timeline_scenes_timeline_id", "timeline_scenes", ["timeline_id"])
    op.create_index("ix_timeline_scenes_sequence_number", "timeline_scenes", ["sequence_number"])

    # 3. Create caption_assets table
    op.create_table(
        "caption_assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("timeline_id", sa.Uuid(), nullable=False),
        sa.Column("format", sa.String(length=16), nullable=False, server_default="ass"),
        sa.Column("style_preset", sa.String(length=32), nullable=False, server_default="vivid_ember"),
        sa.Column("primary_color", sa.String(length=16), nullable=False, server_default="&H00007AFF"),
        sa.Column("highlight_color", sa.String(length=16), nullable=False, server_default="&H0000FFFF"),
        sa.Column("font_name", sa.String(length=64), nullable=False, server_default="Arial"),
        sa.Column("font_size", sa.Integer(), nullable=False, server_default="48"),
        sa.Column("file_path", sa.Text(), nullable=True),
        sa.Column("raw_content", sa.Text(), nullable=True),
        sa.Column("is_embedded", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["timeline_id"], ["video_timelines.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_caption_assets_timeline_id", "caption_assets", ["timeline_id"])

    # 4. Enhance render_jobs table
    op.add_column("render_jobs", sa.Column("timeline_id", sa.Uuid(), nullable=True))
    op.add_column("render_jobs", sa.Column("video_width", sa.Integer(), nullable=False, server_default="1920"))
    op.add_column("render_jobs", sa.Column("video_height", sa.Integer(), nullable=False, server_default="1080"))
    op.add_column("render_jobs", sa.Column("fps", sa.Integer(), nullable=False, server_default="30"))
    op.add_column("render_jobs", sa.Column("aspect_ratio", sa.String(length=16), nullable=False, server_default="16:9"))
    op.add_column("render_jobs", sa.Column("renderer_mode", sa.String(length=32), nullable=False, server_default="ffmpeg"))
    op.add_column("render_jobs", sa.Column("current_stage", sa.String(length=64), nullable=False, server_default="INIT"))
    op.add_column("render_jobs", sa.Column("progress_percentage", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("render_jobs", sa.Column("quality_status", sa.String(length=32), nullable=False, server_default="PENDING"))
    op.add_column("render_jobs", sa.Column("log_tail", sa.Text(), nullable=True))
    try:
        op.create_foreign_key(
            "fk_render_jobs_timeline_id",
            "render_jobs",
            "video_timelines",
            ["timeline_id"],
            ["id"],
            ondelete="SET NULL",
        )
    except Exception:
        pass
    op.create_index("ix_render_jobs_timeline_id", "render_jobs", ["timeline_id"])


def downgrade() -> None:
    op.drop_constraint("fk_render_jobs_timeline_id", "render_jobs", type_="foreignkey")
    op.drop_index("ix_render_jobs_timeline_id", table_name="render_jobs")
    op.drop_column("render_jobs", "log_tail")
    op.drop_column("render_jobs", "quality_status")
    op.drop_column("render_jobs", "progress_percentage")
    op.drop_column("render_jobs", "current_stage")
    op.drop_column("render_jobs", "renderer_mode")
    op.drop_column("render_jobs", "aspect_ratio")
    op.drop_column("render_jobs", "fps")
    op.drop_column("render_jobs", "video_height")
    op.drop_column("render_jobs", "video_width")
    op.drop_column("render_jobs", "timeline_id")

    op.drop_index("ix_caption_assets_timeline_id", table_name="caption_assets")
    op.drop_table("caption_assets")

    op.drop_index("ix_timeline_scenes_sequence_number", table_name="timeline_scenes")
    op.drop_index("ix_timeline_scenes_timeline_id", table_name="timeline_scenes")
    op.drop_table("timeline_scenes")

    op.drop_index("ix_video_timelines_status", table_name="video_timelines")
    op.drop_index("ix_video_timelines_project_id", table_name="video_timelines")
    op.drop_table("video_timelines")
