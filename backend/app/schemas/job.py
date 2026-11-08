"""Job Queue and Automation Pydantic schemas."""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict, Field


class JobCreate(BaseModel):
    channel_id: uuid.UUID
    job_type: str = Field(..., max_length=64, description="Registered job type name")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Job parameters and arguments")
    idempotency_key: Optional[str] = Field(None, max_length=128, description="Unique client key preventing duplicates")
    priority: int = Field(10, ge=1, le=100, description="Execution priority (lower runs sooner)")
    scheduled_at: Optional[datetime] = Field(None, description="Delayed execution time")


class JobRead(BaseModel):
    id: uuid.UUID
    channel_id: uuid.UUID
    job_type: str
    payload: Dict[str, Any]
    idempotency_key: str
    status: str
    priority: int
    progress_percentage: int
    current_stage: Optional[str] = None
    attempt_count: int
    max_retries: int
    error_log: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    locked_by: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JobProgressRead(BaseModel):
    id: uuid.UUID
    status: str
    progress_percentage: int
    current_stage: Optional[str] = None
    error_log: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class JobListResponse(BaseModel):
    items: List[JobRead]
    total: int
    page: int
    page_size: int
