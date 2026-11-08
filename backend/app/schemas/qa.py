"""Pydantic schemas for QA evaluation runs, findings, scores, and exceptions."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class QACheckResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    qa_run_id: UUID
    category: str
    check_name: str
    status: str
    score: float
    execution_time_ms: int
    metrics: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    created_at: datetime


class QAExceptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    finding_id: UUID
    authorized_by_user_id: UUID
    reason: str
    expires_at: Optional[datetime] = None
    created_at: datetime


class QAFindingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    qa_run_id: UUID
    check_id: Optional[UUID] = None
    category: str
    severity: str
    status: str
    affected_artifact: str
    title: str
    explanation: str
    evidence: Dict[str, Any] = Field(default_factory=dict)
    recommended_correction: str
    requires_human_review: bool
    resolved_by_user_id: Optional[UUID] = None
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    exceptions: List[QAExceptionResponse] = Field(default_factory=list)
    created_at: datetime


class QACategoryScoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    qa_run_id: UUID
    category: str
    weight: float
    raw_score: float
    weighted_score: float
    deductions: List[Dict[str, Any]] = Field(default_factory=list)
    check_count: int
    passed_count: int
    warning_count: int
    failed_count: int
    created_at: datetime


class QARunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    publication_package_id: Optional[UUID] = None
    run_number: int
    status: str
    overall_score: Optional[float] = None
    veto_decision: str
    can_publish: bool
    summary: Dict[str, Any] = Field(default_factory=dict)
    input_versions_snapshot: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    checks: List[QACheckResponse] = Field(default_factory=list)
    findings: List[QAFindingResponse] = Field(default_factory=list)
    category_scores: List[QACategoryScoreResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class QARunTriggerRequest(BaseModel):
    project_id: UUID
    publication_package_id: Optional[UUID] = None
    target_categories: Optional[List[str]] = None
    run_async: bool = False


class QAFindingResolveRequest(BaseModel):
    resolution_notes: str = Field(..., min_length=3, description="Explanation of how the defect was fixed")


class QAExceptionCreateRequest(BaseModel):
    reason: str = Field(..., min_length=5, description="Administrative business justification for exception")
    expires_at: Optional[datetime] = None


class QAReadinessResponse(BaseModel):
    project_id: UUID
    can_publish: bool
    veto_decision: str
    overall_score: float
    summary: Dict[str, Any]
