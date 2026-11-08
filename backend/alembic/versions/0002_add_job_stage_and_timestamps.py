"""Add current_stage, started_at, and completed_at to automation_jobs.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-07 20:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("automation_jobs", sa.Column("current_stage", sa.String(length=64), nullable=True))
    op.add_column("automation_jobs", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("automation_jobs", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("automation_jobs", "completed_at")
    op.drop_column("automation_jobs", "started_at")
    op.drop_column("automation_jobs", "current_stage")
