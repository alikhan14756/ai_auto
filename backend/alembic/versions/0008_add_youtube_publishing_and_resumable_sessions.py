"""Add YouTube publishing enhancements and resumable upload sessions.

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-08 03:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add new columns to publishing_jobs
    op.add_column("publishing_jobs", sa.Column("publication_package_id", sa.Uuid(), nullable=True))
    op.add_column("publishing_jobs", sa.Column("idempotency_key", sa.String(length=128), nullable=True))
    op.add_column("publishing_jobs", sa.Column("self_declared_made_for_kids", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("publishing_jobs", sa.Column("current_stage", sa.String(length=64), nullable=False, server_default="DRAFT"))
    op.add_column("publishing_jobs", sa.Column("bytes_uploaded", sa.BigInteger(), nullable=False, server_default="0"))
    op.add_column("publishing_jobs", sa.Column("total_bytes", sa.BigInteger(), nullable=False, server_default="0"))
    op.add_column("publishing_jobs", sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("publishing_jobs", sa.Column("max_retries", sa.Integer(), nullable=False, server_default="5"))
    op.add_column("publishing_jobs", sa.Column("last_error_code", sa.String(length=64), nullable=True))
    op.add_column("publishing_jobs", sa.Column("last_error_message", sa.Text(), nullable=True))
    op.add_column("publishing_jobs", sa.Column("title", sa.String(length=255), nullable=True))
    op.add_column("publishing_jobs", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("publishing_jobs", sa.Column("tags", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))
    op.add_column("publishing_jobs", sa.Column("category_id", sa.String(length=16), nullable=False, server_default="28"))

    # Foreign key and indices on publishing_jobs
    try:
        op.create_foreign_key(
            "fk_publishing_jobs_publication_package_id",
            "publishing_jobs",
            "publication_packages",
            ["publication_package_id"],
            ["id"],
            ondelete="SET NULL",
        )
    except Exception:
        pass  # In SQLite batch mode might be needed, handled gracefully

    op.create_index(op.f("ix_publishing_jobs_publication_package_id"), "publishing_jobs", ["publication_package_id"], unique=False)
    op.create_index(op.f("ix_publishing_jobs_idempotency_key"), "publishing_jobs", ["idempotency_key"], unique=True)

    # 2. Create youtube_upload_sessions table
    op.create_table(
        "youtube_upload_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("publishing_job_id", sa.Uuid(), nullable=False),
        sa.Column("session_uri_encrypted", sa.Text(), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("bytes_uploaded", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("last_byte_offset", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("chunk_size_bytes", sa.BigInteger(), nullable=False, server_default="8388608"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["publishing_job_id"], ["publishing_jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("publishing_job_id", name="uq_youtube_upload_sessions_publishing_job_id"),
    )
    op.create_index(op.f("ix_youtube_upload_sessions_publishing_job_id"), "youtube_upload_sessions", ["publishing_job_id"], unique=True)
    op.create_index(op.f("ix_youtube_upload_sessions_status"), "youtube_upload_sessions", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_youtube_upload_sessions_status"), table_name="youtube_upload_sessions")
    op.drop_index(op.f("ix_youtube_upload_sessions_publishing_job_id"), table_name="youtube_upload_sessions")
    op.drop_table("youtube_upload_sessions")

    op.drop_index(op.f("ix_publishing_jobs_idempotency_key"), table_name="publishing_jobs")
    op.drop_index(op.f("ix_publishing_jobs_publication_package_id"), table_name="publishing_jobs")

    op.drop_column("publishing_jobs", "category_id")
    op.drop_column("publishing_jobs", "tags")
    op.drop_column("publishing_jobs", "description")
    op.drop_column("publishing_jobs", "title")
    op.drop_column("publishing_jobs", "last_error_message")
    op.drop_column("publishing_jobs", "last_error_code")
    op.drop_column("publishing_jobs", "max_retries")
    op.drop_column("publishing_jobs", "retry_count")
    op.drop_column("publishing_jobs", "total_bytes")
    op.drop_column("publishing_jobs", "bytes_uploaded")
    op.drop_column("publishing_jobs", "current_stage")
    op.drop_column("publishing_jobs", "self_declared_made_for_kids")
    op.drop_column("publishing_jobs", "idempotency_key")
    op.drop_column("publishing_jobs", "publication_package_id")
