"""Add QA runs, checks, findings, category scores, and exceptions models.

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-08 02:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. qa_runs table
    op.create_table(
        "qa_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("publication_package_id", sa.Uuid(), nullable=True),
        sa.Column("run_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="QUEUED"),
        sa.Column("overall_score", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("veto_decision", sa.String(length=32), nullable=False, server_default="BLOCKED"),
        sa.Column("can_publish", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("input_versions_snapshot", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("summary", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["video_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["publication_package_id"], ["publication_packages.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_qa_runs_project_id"), "qa_runs", ["project_id"], unique=False)
    op.create_index(op.f("ix_qa_runs_publication_package_id"), "qa_runs", ["publication_package_id"], unique=False)
    op.create_index(op.f("ix_qa_runs_status"), "qa_runs", ["status"], unique=False)
    op.create_index(op.f("ix_qa_runs_veto_decision"), "qa_runs", ["veto_decision"], unique=False)

    # 2. qa_checks table
    op.create_table(
        "qa_checks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("qa_run_id", sa.Uuid(), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("check_name", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PASSED"),
        sa.Column("score", sa.Numeric(precision=5, scale=2), nullable=False, server_default="100.00"),
        sa.Column("execution_time_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("metrics", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["qa_run_id"], ["qa_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_qa_checks_qa_run_id"), "qa_checks", ["qa_run_id"], unique=False)
    op.create_index(op.f("ix_qa_checks_category"), "qa_checks", ["category"], unique=False)
    op.create_index(op.f("ix_qa_checks_check_name"), "qa_checks", ["check_name"], unique=False)

    # 3. qa_findings table
    op.create_table(
        "qa_findings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("qa_run_id", sa.Uuid(), nullable=False),
        sa.Column("check_id", sa.Uuid(), nullable=True),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="OPEN"),
        sa.Column("affected_artifact", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("recommended_correction", sa.Text(), nullable=False),
        sa.Column("requires_human_review", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("resolved_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["qa_run_id"], ["qa_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["check_id"], ["qa_checks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["resolved_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_qa_findings_qa_run_id"), "qa_findings", ["qa_run_id"], unique=False)
    op.create_index(op.f("ix_qa_findings_check_id"), "qa_findings", ["check_id"], unique=False)
    op.create_index(op.f("ix_qa_findings_category"), "qa_findings", ["category"], unique=False)
    op.create_index(op.f("ix_qa_findings_severity"), "qa_findings", ["severity"], unique=False)
    op.create_index(op.f("ix_qa_findings_status"), "qa_findings", ["status"], unique=False)

    # 4. qa_category_scores table
    op.create_table(
        "qa_category_scores",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("qa_run_id", sa.Uuid(), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("weight", sa.Numeric(precision=4, scale=2), nullable=False),
        sa.Column("raw_score", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("weighted_score", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("deductions", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("check_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("passed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("warning_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["qa_run_id"], ["qa_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_qa_category_scores_qa_run_id"), "qa_category_scores", ["qa_run_id"], unique=False)
    op.create_index(op.f("ix_qa_category_scores_category"), "qa_category_scores", ["category"], unique=False)

    # 5. qa_exceptions table
    op.create_table(
        "qa_exceptions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("finding_id", sa.Uuid(), nullable=False),
        sa.Column("authorized_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["finding_id"], ["qa_findings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["authorized_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_qa_exceptions_finding_id"), "qa_exceptions", ["finding_id"], unique=False)
    op.create_index(op.f("ix_qa_exceptions_authorized_by_user_id"), "qa_exceptions", ["authorized_by_user_id"], unique=False)


def downgrade() -> None:
    op.drop_table("qa_exceptions")
    op.drop_table("qa_category_scores")
    op.drop_table("qa_findings")
    op.drop_table("qa_checks")
    op.drop_table("qa_runs")
