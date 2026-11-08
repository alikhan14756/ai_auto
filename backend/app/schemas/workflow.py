"""Pydantic v2 schemas for workflow orchestration, policies, schedules, and governance."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class WorkflowStageResponse(BaseModel):
    """Stage detail within an execution."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    execution_id: UUID
    stage_key: str
    stage_name: str
    job_type: str
    status: str
    order_index: int
    dependencies: List[str]
    stage_inputs: Dict[str, Any]
    stage_outputs: Dict[str, Any]
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class WorkflowExecutionCreate(BaseModel):
    """Payload to create a new workflow execution."""
    channel_id: UUID
    template_key: str = "TEMPLATE_LONG_FORM"
    project_id: Optional[UUID] = None
    definition_id: Optional[UUID] = None
    context_data: Optional[Dict[str, Any]] = None
    auto_start: bool = False


class WorkflowExecutionResponse(BaseModel):
    """Workflow execution state response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    channel_id: UUID
    definition_id: Optional[UUID] = None
    template_key: str
    project_id: Optional[UUID] = None
    status: str
    current_stage_key: Optional[str] = None
    progress_percentage: int
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    context_data: Dict[str, Any]
    failure_count: int
    error_message: Optional[str] = None
    checkpoint_required: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    stages: Optional[List[WorkflowStageResponse]] = None


class WorkflowExecutionListResponse(BaseModel):
    """List of workflow executions."""
    executions: List[WorkflowExecutionResponse]
    total: int


class WorkflowTemplateResponse(BaseModel):
    """Workflow template schema."""
    model_config = ConfigDict(from_attributes=True)

    id: Optional[UUID] = None
    template_key: str
    name: str
    description: str
    content_format: str
    estimated_duration_sec: int
    stages: List[Dict[str, Any]]
    default_settings: Dict[str, Any]
    is_system: bool = True
    channel_id: Optional[UUID] = None


class WorkflowTemplateCreate(BaseModel):
    """Create custom template."""
    name: str
    description: str
    content_format: str = "LONG_FORM"
    estimated_duration_sec: int = 480
    stages: List[Dict[str, Any]]
    default_settings: Optional[Dict[str, Any]] = None


class WorkflowTemplateUpdate(BaseModel):
    """Update custom template."""
    name: Optional[str] = None
    description: Optional[str] = None
    content_format: Optional[str] = None
    estimated_duration_sec: Optional[int] = None
    stages: Optional[List[Dict[str, Any]]] = None
    default_settings: Optional[Dict[str, Any]] = None


class WorkflowPolicyResponse(BaseModel):
    """Channel workflow policy response."""
    model_config = ConfigDict(from_attributes=True)

    channel_id: UUID
    automation_level: int
    allowed_workflow_types: List[str]
    allowed_content_formats: List[str]
    max_workflows_per_week: int
    max_concurrent_workflows: int
    permitted_execution_hours: Dict[str, Any]
    max_monthly_budget_usd: float
    require_topic_approval: bool
    require_script_approval: bool
    require_qa_approval: bool
    require_publish_authorization: bool
    auto_retry_transient_failures: bool
    max_retry_attempts: int


class WorkflowPolicyUpdate(BaseModel):
    """Update workflow policy payload."""
    automation_level: Optional[int] = None
    allowed_workflow_types: Optional[List[str]] = None
    allowed_content_formats: Optional[List[str]] = None
    max_workflows_per_week: Optional[int] = None
    max_concurrent_workflows: Optional[int] = None
    permitted_execution_hours: Optional[Dict[str, Any]] = None
    max_monthly_budget_usd: Optional[float] = None
    require_topic_approval: Optional[bool] = None
    require_script_approval: Optional[bool] = None
    require_qa_approval: Optional[bool] = None
    require_publish_authorization: Optional[bool] = None
    auto_retry_transient_failures: Optional[bool] = None
    max_retry_attempts: Optional[int] = None


class WorkflowScheduleCreate(BaseModel):
    """Create production calendar schedule."""
    channel_id: UUID
    title: str
    content_format: str = "LONG_FORM"
    cron_expression: Optional[str] = None
    planned_start_at: datetime
    planned_publish_at: Optional[datetime] = None
    timezone: str = "UTC"


class WorkflowScheduleUpdate(BaseModel):
    """Update production schedule."""
    title: Optional[str] = None
    planned_start_at: Optional[datetime] = None
    planned_publish_at: Optional[datetime] = None
    timezone: Optional[str] = None
    status: Optional[str] = None


class WorkflowScheduleResponse(BaseModel):
    """Calendar schedule item response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    channel_id: UUID
    definition_id: Optional[UUID] = None
    title: str
    content_format: str
    cron_expression: Optional[str] = None
    planned_start_at: Optional[datetime] = None
    planned_publish_at: Optional[datetime] = None
    timezone: str
    status: str
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    created_at: datetime


class ResourceUsageSummaryResponse(BaseModel):
    """Resource consumption summary."""
    channel_id: str
    current_month_spend_usd: float
    monthly_budget_usd: float
    budget_remaining_usd: float
    is_budget_capped: bool
    resource_breakdown: Dict[str, Any]


class ProductionHealthResponse(BaseModel):
    """System health response."""
    status: str
    active_workflows: int
    failed_workflows: int
    completed_workflows: int
    underlying_queued_jobs: int
    stalled_stages_count: int
    stalled_stage_keys: List[str]
    last_successful_completion: Optional[str] = None
    monitored_at: str


class OptimizationRecommendationResponse(BaseModel):
    """Content opportunity recommendation."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    channel_id: UUID
    topic_id: Optional[UUID] = None
    video_id: Optional[UUID] = None
    recommendation_type: str
    title: str
    description: str
    supporting_analytics: Dict[str, Any]
    confidence_score: float
    expected_effort: str
    status: str
    suggested_action: str
    created_at: datetime


class WorkflowEventResponse(BaseModel):
    """Audit event response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    channel_id: UUID
    execution_id: Optional[UUID] = None
    event_type: str
    stage_key: Optional[str] = None
    actor_type: str
    actor_id: Optional[str] = None
    details: Dict[str, Any]
    created_at: datetime


class WorkflowFailureResponse(BaseModel):
    """Diagnostic failure response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    channel_id: UUID
    execution_id: UUID
    stage_key: str
    job_id: Optional[UUID] = None
    error_category: str
    sanitized_error: str
    retry_count: int
    recovery_status: str
    suggested_resolution: Optional[str] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime
