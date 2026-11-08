"""Add storyboards table and media asset enhancements.

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-07 23:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create storyboards table
    op.create_table(
        "storyboards",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("script_id", sa.Uuid(), nullable=True),
        sa.Column("narration_track_id", sa.Uuid(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="DRAFT"),
        sa.Column("aspect_ratio", sa.String(length=16), nullable=False, server_default="16:9"),
        sa.Column("scene_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("approved_scene_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["video_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["script_id"], ["scripts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["narration_track_id"], ["narration_tracks.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_storyboards_project_id", "storyboards", ["project_id"])
    op.create_index("ix_storyboards_script_id", "storyboards", ["script_id"])
    op.create_index("ix_storyboards_narration_track_id", "storyboards", ["narration_track_id"])

    # 2. Enhance scenes table
    op.add_column("scenes", sa.Column("storyboard_id", sa.Uuid(), nullable=True))
    op.add_column("scenes", sa.Column("visual_purpose", sa.String(length=64), nullable=False, server_default="CONCEPT_EXPLANATION"))
    op.add_column("scenes", sa.Column("suggested_asset_type", sa.String(length=64), nullable=False, server_default="GENERATED_IMAGE"))
    op.add_column("scenes", sa.Column("search_keywords", sa.JSON(), nullable=False, server_default="[]"))
    op.add_column("scenes", sa.Column("image_prompt", sa.Text(), nullable=True))
    op.add_column("scenes", sa.Column("transition", sa.String(length=32), nullable=False, server_default="CUT"))
    op.add_column("scenes", sa.Column("review_status", sa.String(length=32), nullable=False, server_default="DRAFT"))
    op.add_column("scenes", sa.Column("selected_asset_id", sa.Uuid(), nullable=True))
    try:
        op.create_foreign_key(
            "fk_scenes_storyboard_id",
            "scenes",
            "storyboards",
            ["storyboard_id"],
            ["id"],
            ondelete="CASCADE",
        )
        op.create_foreign_key(
            "fk_scenes_selected_asset_id",
            "scenes",
            "media_assets",
            ["selected_asset_id"],
            ["id"],
            ondelete="SET NULL",
        )
    except Exception:
        pass
    op.create_index("ix_scenes_storyboard_id", "scenes", ["storyboard_id"])
    op.create_index("ix_scenes_selected_asset_id", "scenes", ["selected_asset_id"])

    # 3. Enhance media_assets table
    op.add_column("media_assets", sa.Column("channel_id", sa.Uuid(), nullable=True))
    op.add_column("media_assets", sa.Column("title", sa.String(length=255), nullable=False, server_default="Untitled Asset"))
    op.add_column("media_assets", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("media_assets", sa.Column("asset_category", sa.String(length=64), nullable=False, server_default="GENERATED"))
    op.add_column("media_assets", sa.Column("source_provider", sa.String(length=64), nullable=False, server_default="MOCK"))
    op.add_column("media_assets", sa.Column("source_url", sa.Text(), nullable=True))
    op.add_column("media_assets", sa.Column("preview_url", sa.Text(), nullable=True))
    op.add_column("media_assets", sa.Column("author_name", sa.String(length=255), nullable=True))
    op.add_column("media_assets", sa.Column("author_url", sa.Text(), nullable=True))
    op.add_column("media_assets", sa.Column("license_status", sa.String(length=64), nullable=False, server_default="VERIFIED_COMMERCIAL"))
    op.add_column("media_assets", sa.Column("attribution_text", sa.Text(), nullable=True))
    op.add_column("media_assets", sa.Column("aspect_ratio", sa.String(length=16), nullable=False, server_default="16:9"))
    op.add_column("media_assets", sa.Column("width", sa.Integer(), nullable=True))
    op.add_column("media_assets", sa.Column("height", sa.Integer(), nullable=True))
    op.add_column("media_assets", sa.Column("mime_type", sa.String(length=64), nullable=False, server_default="image/png"))
    op.add_column("media_assets", sa.Column("duration_seconds", sa.Numeric(precision=8, scale=2), nullable=True))
    op.add_column("media_assets", sa.Column("is_archived", sa.Boolean(), nullable=False, server_default="false"))
    try:
        op.create_foreign_key(
            "fk_media_assets_channel_id",
            "media_assets",
            "channels",
            ["channel_id"],
            ["id"],
            ondelete="CASCADE",
        )
    except Exception:
        pass
    op.create_index("ix_media_assets_channel_id", "media_assets", ["channel_id"])


def downgrade() -> None:
    # 1. Downgrade media_assets
    op.drop_index("ix_media_assets_channel_id", table_name="media_assets")
    op.drop_constraint("fk_media_assets_channel_id", "media_assets", type_="foreignkey")
    op.drop_column("media_assets", "is_archived")
    op.drop_column("media_assets", "duration_seconds")
    op.drop_column("media_assets", "mime_type")
    op.drop_column("media_assets", "height")
    op.drop_column("media_assets", "width")
    op.drop_column("media_assets", "aspect_ratio")
    op.drop_column("media_assets", "attribution_text")
    op.drop_column("media_assets", "license_status")
    op.drop_column("media_assets", "author_url")
    op.drop_column("media_assets", "author_name")
    op.drop_column("media_assets", "preview_url")
    op.drop_column("media_assets", "source_url")
    op.drop_column("media_assets", "source_provider")
    op.drop_column("media_assets", "asset_category")
    op.drop_column("media_assets", "description")
    op.drop_column("media_assets", "title")
    op.drop_column("media_assets", "channel_id")

    # 2. Downgrade scenes
    op.drop_index("ix_scenes_selected_asset_id", table_name="scenes")
    op.drop_index("ix_scenes_storyboard_id", table_name="scenes")
    op.drop_constraint("fk_scenes_selected_asset_id", "scenes", type_="foreignkey")
    op.drop_constraint("fk_scenes_storyboard_id", "scenes", type_="foreignkey")
    op.drop_column("scenes", "selected_asset_id")
    op.drop_column("scenes", "review_status")
    op.drop_column("scenes", "transition")
    op.drop_column("scenes", "image_prompt")
    op.drop_column("scenes", "search_keywords")
    op.drop_column("scenes", "suggested_asset_type")
    op.drop_column("scenes", "visual_purpose")
    op.drop_column("scenes", "storyboard_id")

    # 3. Downgrade storyboards
    op.drop_index("ix_storyboards_narration_track_id", table_name="storyboards")
    op.drop_index("ix_storyboards_script_id", table_name="storyboards")
    op.drop_index("ix_storyboards_project_id", table_name="storyboards")
    op.drop_table("storyboards")
