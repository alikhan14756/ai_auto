"""Autonomous Workflow Orchestration, Policies, Schedules and Governance models."""

from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
    UniqueConstraint,
)
from sqlalchemy.types import Uuid
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.models.base import UUIDPrimaryKeyMixin, TimestampMixin

# Workflow Execution Lifecycle States
WORKFLOW_STATUS_DRAFT = "DRAFT"
WORKFLOW_STATUS_SCHEDULED = "SCHEDULED"
WORKFLOW_STATUS_READY = "READY"
WORKFLOW_STATUS_RUNNING = "RUNNING"
WORKFLOW_STATUS_PAUSED = "PAUSED"
WORKFLOW_STATUS_WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
WORKFLOW_STATUS_RECOVERING = "RECOVERING"
WORKFLOW_STATUS_COMPLETED = "COMPLETED"
WORKFLOW_STATUS_FAILED = "FAILED"
WORKFLOW_STATUS_CANCELLED = "CANCELLED"

VALID_WORKFLOW_STATUSES = {
    WORKFLOW_STATUS_DRAFT,
    WORKFLOW_STATUS_SCHEDULED,
    WORKFLOW_STATUS_READY,
    WORKFLOW_STATUS_RUNNING,
    WORKFLOW_STATUS_PAUSED,
    WORKFLOW_STATUS_WAITING_FOR_APPROVAL,
    WORKFLOW_STATUS_RECOVERING,
    WORKFLOW_STATUS_COMPLETED,
    WORKFLOW_STATUS_FAILED,
    WORKFLOW_STATUS_CANCELLED,
}

# State Transitions Validation Matrix
ALLOWED_WORKFLOW_TRANSITIONS = {
    WORKFLOW_STATUS_DRAFT: {WORKFLOW_STATUS_SCHEDULED, WORKFLOW_STATUS_READY, WORKFLOW_STATUS_CANCELLED},
    WORKFLOW_STATUS_SCHEDULED: {WORKFLOW_STATUS_READY, WORKFLOW_STATUS_PAUSED, WORKFLOW_STATUS_CANCELLED},
    WORKFLOW_STATUS_READY: {WORKFLOW_STATUS_RUNNING, WORKFLOW_STATUS_PAUSED, WORKFLOW_STATUS_CANCELLED},
    WORKFLOW_STATUS_RUNNING: {
        WORKFLOW_STATUS_PAUSED,
        WORKFLOW_STATUS_WAITING_FOR_APPROVAL,
        WORKFLOW_STATUS_RECOVERING,
        WORKFLOW_STATUS_COMPLETED,
        WORKFLOW_STATUS_FAILED,
        WORKFLOW_STATUS_CANCELLED,
    },
    WORKFLOW_STATUS_PAUSED: {WORKFLOW_STATUS_RUNNING, WORKFLOW_STATUS_CANCELLED},
    WORKFLOW_STATUS_WAITING_FOR_APPROVAL: {WORKFLOW_STATUS_RUNNING, WORKFLOW_STATUS_CANCELLED, WORKFLOW_STATUS_FAILED},
    WORKFLOW_STATUS_RECOVERING: {WORKFLOW_STATUS_RUNNING, WORKFLOW_STATUS_FAILED, WORKFLOW_STATUS_PAUSED},
    WORKFLOW_STATUS_FAILED: {WORKFLOW_STATUS_READY},  # Manual retry/reset returns to READY
    WORKFLOW_STATUS_COMPLETED: set(),
    WORKFLOW_STATUS_CANCELLED: set(),
}

# Stage Status Constants
STAGE_STATUS_PENDING = "PENDING"
STAGE_STATUS_RUNNING = "RUNNING"
STAGE_STATUS_WAITING_APPROVAL = "WAITING_APPROVAL"
STAGE_STATUS_COMPLETED = "COMPLETED"
STAGE_STATUS_FAILED = "FAILED"
STAGE_STATUS_SKIPPED = "SKIPPED"

# Automation Tiers
AUTOMATION_LEVEL_MANUAL = 0
AUTOMATION_LEVEL_ASSISTED = 1  # Default
AUTOMATION_LEVEL_CONTROLLED = 2
AUTOMATION_LEVEL_SCHEDULED = 3


class WorkflowTemplate(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Reusable template defining stages, dependencies and defaults."""

    __tablename__ = "workflow_templates"

    template_key = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=False)
    content_format = Column(String(32), default="LONG_FORM", nullable=False)  # LONG_FORM, SHORTS
    estimated_duration_sec = Column(Integer, default=480, nullable=False)
    stages = Column(JSON, default=list, nullable=False)
    default_settings = Column(JSON, default=dict, nullable=False)
    is_system = Column(Boolean, default=True, nullable=False)
    channel_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("channels.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    channel = relationship("Channel")


class WorkflowDefinition(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Configured workflow instance for a channel."""

    __tablename__ = "workflow_definitions"

    channel_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("channels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    template_key = Column(String(64), nullable=False, index=True)
    content_format = Column(String(32), default="LONG_FORM", nullable=False)
    stage_definitions = Column(JSON, default=list, nullable=False)
    default_inputs = Column(JSON, default=dict, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    channel = relationship("Channel", back_populates="workflow_definitions")
    executions = relationship("WorkflowExecution", back_populates="definition", cascade="all, delete-orphan")
    schedules = relationship("WorkflowSchedule", back_populates="definition", cascade="all, delete-orphan")


class WorkflowExecution(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Live or historical run of a workflow through its state machine."""

    __tablename__ = "workflow_executions"

    channel_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("channels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    definition_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("workflow_definitions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    template_key = Column(String(64), nullable=False, index=True)
    project_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("video_projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status = Column(String(32), default=WORKFLOW_STATUS_DRAFT, nullable=False, index=True)
    current_stage_key = Column(String(64), nullable=True)
    progress_percentage = Column(Integer, default=0, nullable=False)
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    context_data = Column(JSON, default=dict, nullable=False)
    failure_count = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)
    checkpoint_required = Column(String(64), nullable=True)  # SCRIPT_APPROVAL, QA_APPROVAL, PUBLISH_AUTHORIZATION

    channel = relationship("Channel", back_populates="workflow_executions", lazy="selectin")
    definition = relationship("WorkflowDefinition", back_populates="executions", lazy="selectin")
    project = relationship("VideoProject", lazy="selectin")
    stages = relationship("WorkflowStage", back_populates="execution", cascade="all, delete-orphan", order_by="WorkflowStage.order_index", lazy="selectin")
    events = relationship("WorkflowEvent", back_populates="execution", cascade="all, delete-orphan", lazy="selectin")
    failures = relationship("WorkflowFailure", back_populates="execution", cascade="all, delete-orphan", lazy="selectin")
    resource_usages = relationship("ResourceUsageRecord", back_populates="execution", cascade="all, delete-orphan", lazy="selectin")

    def can_transition_to(self, target_status: str) -> bool:
        """Verify whether status transition is permissible under state graph."""
        return target_status in ALLOWED_WORKFLOW_TRANSITIONS.get(self.status, set())


class WorkflowStage(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Individual stage step within a workflow execution."""

    __tablename__ = "workflow_stages"

    execution_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("workflow_executions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stage_key = Column(String(64), nullable=False)
    stage_name = Column(String(128), nullable=False)
    job_type = Column(String(64), nullable=False)
    job_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("automation_jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status = Column(String(32), default=STAGE_STATUS_PENDING, nullable=False, index=True)
    order_index = Column(Integer, default=0, nullable=False)
    dependencies = Column(JSON, default=list, nullable=False)
    stage_inputs = Column(JSON, default=dict, nullable=False)
    stage_outputs = Column(JSON, default=dict, nullable=False)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    execution = relationship("WorkflowExecution", back_populates="stages")
    job = relationship("AutomationJob", lazy="selectin")


class WorkflowPolicy(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Channel-scoped autonomous execution policies, permissions and safety limits."""

    __tablename__ = "workflow_policies"

    channel_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("channels.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    automation_level = Column(Integer, default=AUTOMATION_LEVEL_ASSISTED, nullable=False)
    allowed_workflow_types = Column(JSON, default=list, nullable=False)
    allowed_content_formats = Column(JSON, default=list, nullable=False)
    max_workflows_per_week = Column(Integer, default=5, nullable=False)
    max_concurrent_workflows = Column(Integer, default=2, nullable=False)
    permitted_execution_hours = Column(JSON, default=dict, nullable=False)  # {"start": 0, "end": 23}
    max_monthly_budget_usd = Column(Float, default=0.0, nullable=False)
    require_topic_approval = Column(Boolean, default=True, nullable=False)
    require_script_approval = Column(Boolean, default=True, nullable=False)
    require_qa_approval = Column(Boolean, default=True, nullable=False)
    require_publish_authorization = Column(Boolean, default=True, nullable=False)
    auto_retry_transient_failures = Column(Boolean, default=True, nullable=False)
    max_retry_attempts = Column(Integer, default=3, nullable=False)

    channel = relationship("Channel", back_populates="workflow_policy", lazy="selectin")


class WorkflowSchedule(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Timezone-aware production calendar schedule item."""

    __tablename__ = "workflow_schedules"

    channel_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("channels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    definition_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("workflow_definitions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title = Column(String(128), nullable=False)
    content_format = Column(String(32), default="LONG_FORM", nullable=False)
    cron_expression = Column(String(64), nullable=True)
    planned_start_at = Column(DateTime(timezone=True), nullable=True, index=True)
    planned_publish_at = Column(DateTime(timezone=True), nullable=True, index=True)
    timezone = Column(String(64), default="UTC", nullable=False)
    status = Column(String(32), default="SCHEDULED", nullable=False, index=True)
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    next_run_at = Column(DateTime(timezone=True), nullable=True)

    channel = relationship("Channel", back_populates="workflow_schedules", lazy="selectin")
    definition = relationship("WorkflowDefinition", back_populates="schedules", lazy="selectin")


class ResourceUsageRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Meters consumption of compute, tokens, and storage."""

    __tablename__ = "resource_usage_records"

    channel_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("channels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    execution_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("workflow_executions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    resource_type = Column(String(64), nullable=False, index=True)  # GEMINI_TOKENS, TTS_CHARS, RENDER_SECONDS, STORAGE_BYTES
    amount_used = Column(Float, default=0.0, nullable=False)
    unit = Column(String(32), nullable=False)
    estimated_cost_usd = Column(Float, default=0.0, nullable=False)
    measured_at = Column(DateTime(timezone=True), nullable=False, index=True)

    channel = relationship("Channel", back_populates="resource_usage_records")
    execution = relationship("WorkflowExecution", back_populates="resource_usages")


class WorkflowEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Append-only audit trail of orchestration state changes."""

    __tablename__ = "workflow_events"

    channel_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("channels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    execution_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("workflow_executions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    event_type = Column(String(64), nullable=False, index=True)
    stage_key = Column(String(64), nullable=True)
    actor_type = Column(String(32), default="SYSTEM", nullable=False)  # USER, WORKER_DAEMON, POLICY_ENGINE, SYSTEM
    actor_id = Column(String(128), nullable=True)
    details = Column(JSON, default=dict, nullable=False)

    channel = relationship("Channel")
    execution = relationship("WorkflowExecution", back_populates="events")


class WorkflowFailure(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Diagnostic record of stalled, crashed, or vetoed production jobs."""

    __tablename__ = "workflow_failures"

    channel_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("channels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    execution_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("workflow_executions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stage_key = Column(String(64), nullable=False)
    job_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("automation_jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    error_category = Column(String(64), nullable=False, index=True)  # PROVIDER_TIMEOUT, WORKER_CRASH, RETRY_EXHAUSTED, etc.
    sanitized_error = Column(Text, nullable=False)
    retry_count = Column(Integer, default=0, nullable=False)
    recovery_status = Column(String(32), default="UNRESOLVED", nullable=False, index=True)  # UNRESOLVED, RECOVERING, RESOLVED, MANUAL_REQUIRED
    suggested_resolution = Column(Text, nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    channel = relationship("Channel")
    execution = relationship("WorkflowExecution", back_populates="failures")


class OptimizationRecommendation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Analytics-driven strategic recommendation generated by opportunity engine."""

    __tablename__ = "optimization_recommendations"

    channel_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("channels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    topic_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("topics.id", ondelete="SET NULL"),
        nullable=True,
    )
    video_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("video_projects.id", ondelete="SET NULL"),
        nullable=True,
    )
    recommendation_type = Column(String(64), nullable=False, index=True)  # HOOK_OPTIMIZATION, PACING_ADJUSTMENT, TOPIC_EXPANSION, etc.
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    supporting_analytics = Column(JSON, default=dict, nullable=False)
    confidence_score = Column(Float, default=0.8, nullable=False)
    expected_effort = Column(String(32), default="MEDIUM", nullable=False)
    status = Column(String(32), default="NEW", nullable=False, index=True)  # NEW, ACCEPTED, DISMISSED, APPLIED
    suggested_action = Column(String(128), nullable=False)

    channel = relationship("Channel", lazy="selectin")
    topic = relationship("Topic", lazy="selectin")
    video = relationship("VideoProject", lazy="selectin")
