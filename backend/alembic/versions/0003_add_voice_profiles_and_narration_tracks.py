"""Add voice_profiles and narration_tracks tables, update voiceovers.

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-07 22:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create voice_profiles table
    op.create_table(
        "voice_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("channel_id", sa.Uuid(), nullable=True),
        sa.Column("display_name", sa.String(length=128), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("provider_voice_id", sa.String(length=128), nullable=False),
        sa.Column("language_code", sa.String(length=32), nullable=False, server_default="en-US"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("gender", sa.String(length=32), nullable=True),
        sa.Column("speed_ratio", sa.Numeric(precision=4, scale=2), nullable=False, server_default="1.00"),
        sa.Column("pitch_semitones", sa.Numeric(precision=4, scale=2), nullable=False, server_default="0.00"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("settings", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["channel_id"], ["channels.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_voice_profiles_channel_id", "voice_profiles", ["channel_id"])

    # 2. Create narration_tracks table
    op.create_table(
        "narration_tracks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("script_id", sa.Uuid(), nullable=True),
        sa.Column("voice_profile_id", sa.Uuid(), nullable=True),
        sa.Column("script_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("track_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("audio_storage_path", sa.Text(), nullable=False),
        sa.Column("file_format", sa.String(length=16), nullable=False, server_default="wav"),
        sa.Column("sample_rate", sa.Integer(), nullable=False, server_default="24000"),
        sa.Column("channels", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("duration_seconds", sa.Numeric(precision=8, scale=3), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("loudness_lufs", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("is_approved", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="READY"),
        sa.Column("quality_status", sa.String(length=32), nullable=False, server_default="PASSED"),
        sa.Column("quality_report", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["video_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["script_id"], ["scripts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["voice_profile_id"], ["voice_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_narration_tracks_project_id", "narration_tracks", ["project_id"])
    op.create_index("ix_narration_tracks_script_id", "narration_tracks", ["script_id"])
    op.create_index("ix_narration_tracks_voice_profile_id", "narration_tracks", ["voice_profile_id"])

    # 3. Update voiceovers table
    op.add_column("voiceovers", sa.Column("narration_track_id", sa.Uuid(), nullable=True))
    op.add_column("voiceovers", sa.Column("chunk_index", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("voiceovers", sa.Column("status", sa.String(length=32), nullable=False, server_default="GENERATED"))
    try:
        op.create_foreign_key(
            "fk_voiceovers_narration_track_id",
            "voiceovers",
            "narration_tracks",
            ["narration_track_id"],
            ["id"],
            ondelete="CASCADE",
        )
    except Exception:
        pass
    op.create_index("ix_voiceovers_narration_track_id", "voiceovers", ["narration_track_id"])


def downgrade() -> None:
    op.drop_index("ix_voiceovers_narration_track_id", table_name="voiceovers")
    op.drop_constraint("fk_voiceovers_narration_track_id", "voiceovers", type_="foreignkey")
    op.drop_column("voiceovers", "status")
    op.drop_column("voiceovers", "chunk_index")
    op.drop_column("voiceovers", "narration_track_id")
    op.drop_index("ix_narration_tracks_voice_profile_id", table_name="narration_tracks")
    op.drop_index("ix_narration_tracks_script_id", table_name="narration_tracks")
    op.drop_index("ix_narration_tracks_project_id", table_name="narration_tracks")
    op.drop_table("narration_tracks")
    op.drop_index("ix_voice_profiles_channel_id", table_name="voice_profiles")
    op.drop_table("voice_profiles")
