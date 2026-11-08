"""Add workflow orchestration, policies, schedules, resource governance, and optimization recommendations.

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-08 06:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. workflow_templates
    op.create_table(
        "workflow_templates",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("template_key", sa.String(length=64), unique=True, nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("content_format", sa.String(length=32), nullable=False, server_default="LONG_FORM"),
        sa.Column("estimated_duration_sec", sa.Integer(), nullable=False, server_default="480"),
        sa.Column("stages", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("default_settings", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("channel_id", sa.Uuid(), sa.ForeignKey("channels.id", ondelete="CASCADE"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_workflow_templates_template_key", "workflow_templates", ["template_key"])
    op.create_index("ix_workflow_templates_channel_id", "workflow_templates", ["channel_id"])

    # 2. workflow_definitions
    op.create_table(
        "workflow_definitions",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("channel_id", sa.Uuid(), sa.ForeignKey("channels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("template_key", sa.String(length=64), nullable=False),
        sa.Column("content_format", sa.String(length=32), nullable=False, server_default="LONG_FORM"),
        sa.Column("stage_definitions", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("default_inputs", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_workflow_definitions_channel_id", "workflow_definitions", ["channel_id"])
    op.create_index("ix_workflow_definitions_template_key", "workflow_definitions", ["template_key"])

    # 3. workflow_executions
    op.create_table(
        "workflow_executions",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("channel_id", sa.Uuid(), sa.ForeignKey("channels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("definition_id", sa.Uuid(), sa.ForeignKey("workflow_definitions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("template_key", sa.String(length=64), nullable=False),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("video_projects.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="DRAFT"),
        sa.Column("current_stage_key", sa.String(length=64), nullable=True),
        sa.Column("progress_percentage", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("context_data", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("failure_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("checkpoint_required", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_workflow_executions_channel_id", "workflow_executions", ["channel_id"])
    op.create_index("ix_workflow_executions_definition_id", "workflow_executions", ["definition_id"])
    op.create_index("ix_workflow_executions_project_id", "workflow_executions", ["project_id"])
    op.create_index("ix_workflow_executions_status", "workflow_executions", ["status"])

    # 4. workflow_stages
    op.create_table(
        "workflow_stages",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("execution_id", sa.Uuid(), sa.ForeignKey("workflow_executions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stage_key", sa.String(length=64), nullable=False),
        sa.Column("stage_name", sa.String(length=128), nullable=False),
        sa.Column("job_type", sa.String(length=64), nullable=False),
        sa.Column("job_id", sa.Uuid(), sa.ForeignKey("automation_jobs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("dependencies", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("stage_inputs", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("stage_outputs", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_workflow_stages_execution_id", "workflow_stages", ["execution_id"])
    op.create_index("ix_workflow_stages_job_id", "workflow_stages", ["job_id"])
    op.create_index("ix_workflow_stages_status", "workflow_stages", ["status"])

    # 5. workflow_policies
    op.create_table(
        "workflow_policies",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("channel_id", sa.Uuid(), sa.ForeignKey("channels.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("automation_level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("allowed_workflow_types", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("allowed_content_formats", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("max_workflows_per_week", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("max_concurrent_workflows", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("permitted_execution_hours", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("max_monthly_budget_usd", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("require_topic_approval", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("require_script_approval", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("require_qa_approval", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("require_publish_authorization", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("auto_retry_transient_failures", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("max_retry_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_workflow_policies_channel_id", "workflow_policies", ["channel_id"])

    # 6. workflow_schedules
    op.create_table(
        "workflow_schedules",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("channel_id", sa.Uuid(), sa.ForeignKey("channels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("definition_id", sa.Uuid(), sa.ForeignKey("workflow_definitions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(length=128), nullable=False),
        sa.Column("content_format", sa.String(length=32), nullable=False, server_default="LONG_FORM"),
        sa.Column("cron_expression", sa.String(length=64), nullable=True),
        sa.Column("planned_start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("planned_publish_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("timezone", sa.String(length=64), nullable=False, server_default="UTC"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="SCHEDULED"),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_workflow_schedules_channel_id", "workflow_schedules", ["channel_id"])
    op.create_index("ix_workflow_schedules_planned_start_at", "workflow_schedules", ["planned_start_at"])
    op.create_index("ix_workflow_schedules_planned_publish_at", "workflow_schedules", ["planned_publish_at"])

    # 7. resource_usage_records
    op.create_table(
        "resource_usage_records",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("channel_id", sa.Uuid(), sa.ForeignKey("channels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("execution_id", sa.Uuid(), sa.ForeignKey("workflow_executions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("amount_used", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("unit", sa.String(length=32), nullable=False),
        sa.Column("estimated_cost_usd", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("measured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_resource_usage_records_channel_id", "resource_usage_records", ["channel_id"])
    op.create_index("ix_resource_usage_records_resource_type", "resource_usage_records", ["resource_type"])
    op.create_index("ix_resource_usage_records_measured_at", "resource_usage_records", ["measured_at"])

    # 8. workflow_events
    op.create_table(
        "workflow_events",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("channel_id", sa.Uuid(), sa.ForeignKey("channels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("execution_id", sa.Uuid(), sa.ForeignKey("workflow_executions.id", ondelete="CASCADE"), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("stage_key", sa.String(length=64), nullable=True),
        sa.Column("actor_type", sa.String(length=32), nullable=False, server_default="SYSTEM"),
        sa.Column("actor_id", sa.String(length=128), nullable=True),
        sa.Column("details", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_workflow_events_channel_id", "workflow_events", ["channel_id"])
    op.create_index("ix_workflow_events_execution_id", "workflow_events", ["execution_id"])
    op.create_index("ix_workflow_events_event_type", "workflow_events", ["event_type"])

    # 9. workflow_failures
    op.create_table(
        "workflow_failures",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("channel_id", sa.Uuid(), sa.ForeignKey("channels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("execution_id", sa.Uuid(), sa.ForeignKey("workflow_executions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stage_key", sa.String(length=64), nullable=False),
        sa.Column("job_id", sa.Uuid(), sa.ForeignKey("automation_jobs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("error_category", sa.String(length=64), nullable=False),
        sa.Column("sanitized_error", sa.Text(), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("recovery_status", sa.String(length=32), nullable=False, server_default="UNRESOLVED"),
        sa.Column("suggested_resolution", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_workflow_failures_channel_id", "workflow_failures", ["channel_id"])
    op.create_index("ix_workflow_failures_execution_id", "workflow_failures", ["execution_id"])
    op.create_index("ix_workflow_failures_error_category", "workflow_failures", ["error_category"])

    # 10. optimization_recommendations
    op.create_table(
        "optimization_recommendations",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("channel_id", sa.Uuid(), sa.ForeignKey("channels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("topic_id", sa.Uuid(), sa.ForeignKey("topics.id", ondelete="SET NULL"), nullable=True),
        sa.Column("video_id", sa.Uuid(), sa.ForeignKey("video_projects.id", ondelete="SET NULL"), nullable=True),
        sa.Column("recommendation_type", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("supporting_analytics", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0.8"),
        sa.Column("expected_effort", sa.String(length=32), nullable=False, server_default="MEDIUM"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="NEW"),
        sa.Column("suggested_action", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_optimization_recommendations_channel_id", "optimization_recommendations", ["channel_id"])
    op.create_index("ix_optimization_recommendations_type", "optimization_recommendations", ["recommendation_type"])
    op.create_index("ix_optimization_recommendations_status", "optimization_recommendations", ["status"])


def downgrade() -> None:
    op.drop_table("optimization_recommendations")
    op.drop_table("workflow_failures")
    op.drop_table("workflow_events")
    op.drop_table("resource_usage_records")
    op.drop_table("workflow_schedules")
    op.drop_table("workflow_policies")
    op.drop_table("workflow_stages")
    op.drop_table("workflow_executions")
    op.drop_table("workflow_definitions")
    op.drop_table("workflow_templates")
