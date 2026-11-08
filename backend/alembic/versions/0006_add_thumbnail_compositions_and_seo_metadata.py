"""Add thumbnail compositions, video metadata drafts, and publication packages.

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-08 01:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enhance thumbnails table
    op.add_column("thumbnails", sa.Column("style_preset", sa.String(length=64), nullable=False, server_default="modern_tech_editorial"))
    op.add_column("thumbnails", sa.Column("width", sa.Integer(), nullable=False, server_default="1280"))
    op.add_column("thumbnails", sa.Column("height", sa.Integer(), nullable=False, server_default="720"))
    op.add_column("thumbnails", sa.Column("file_size_bytes", sa.BigInteger(), nullable=False, server_default="0"))
    op.add_column("thumbnails", sa.Column("format", sa.String(length=16), nullable=False, server_default="PNG"))
    op.add_column("thumbnails", sa.Column("composition_data", sa.JSON(), nullable=False, server_default="{}"))
    op.add_column("thumbnails", sa.Column("concept_data", sa.JSON(), nullable=False, server_default="{}"))
    op.add_column("thumbnails", sa.Column("quality_status", sa.String(length=32), nullable=False, server_default="PENDING"))
    op.add_column("thumbnails", sa.Column("quality_report", sa.JSON(), nullable=False, server_default="{}"))
    op.add_column("thumbnails", sa.Column("version", sa.Integer(), nullable=False, server_default="1"))

    # 2. Create video_metadata_drafts table
    op.create_table(
        "video_metadata_drafts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("title_candidates", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("hashtags", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("chapters", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("pinned_comment", sa.Text(), nullable=True),
        sa.Column("synthetic_media_disclosure", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("seo_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("seo_report", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("pairing_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("pairing_report", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_approved", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["video_projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_video_metadata_drafts_project_id", "video_metadata_drafts", ["project_id"])

    # 3. Create publication_packages table
    op.create_table(
        "publication_packages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("render_job_id", sa.Uuid(), nullable=True),
        sa.Column("thumbnail_id", sa.Uuid(), nullable=True),
        sa.Column("metadata_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="DRAFT"),
        sa.Column("package_manifest", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["video_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["render_job_id"], ["render_jobs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["thumbnail_id"], ["thumbnails.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["metadata_id"], ["video_metadata_drafts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_publication_packages_project_id", "publication_packages", ["project_id"])
    op.create_index("ix_publication_packages_status", "publication_packages", ["status"])


def downgrade() -> None:
    op.drop_index("ix_publication_packages_status", table_name="publication_packages")
    op.drop_index("ix_publication_packages_project_id", table_name="publication_packages")
    op.drop_table("publication_packages")

    op.drop_index("ix_video_metadata_drafts_project_id", table_name="video_metadata_drafts")
    op.drop_table("video_metadata_drafts")

    op.drop_column("thumbnails", "version")
    op.drop_column("thumbnails", "quality_report")
    op.drop_column("thumbnails", "quality_status")
    op.drop_column("thumbnails", "concept_data")
    op.drop_column("thumbnails", "composition_data")
    op.drop_column("thumbnails", "format")
    op.drop_column("thumbnails", "file_size_bytes")
    op.drop_column("thumbnails", "height")
    op.drop_column("thumbnails", "width")
    op.drop_column("thumbnails", "style_preset")
