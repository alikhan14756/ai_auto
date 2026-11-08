"""Pydantic schemas for YouTube OAuth and Resumable Publishing endpoints."""

import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class YouTubeConnectResponse(BaseModel):
    """OAuth URL response for initiating YouTube consent flow."""
    authorization_url: str
    state: str


class YouTubeConnectionStatusResponse(BaseModel):
    """Sanitized channel connection status without tokens or credentials."""
    connected: bool
    channel_id: Optional[uuid.UUID] = None
    youtube_channel_id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    custom_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    subscriber_count: int = 0
    token_expires_at: Optional[datetime] = None


class PublicationCreateRequest(BaseModel):
    """Payload to initiate a verified YouTube publication."""
    project_id: uuid.UUID
    channel_id: uuid.UUID
    publication_package_id: uuid.UUID
    privacy_status: str = Field(default="unlisted", description="private, unlisted, or public")
    scheduled_publish_time: Optional[datetime] = Field(default=None, description="ISO-8601 UTC timestamp")
    self_declared_made_for_kids: bool = Field(default=False)
    synthetic_media_declared: bool = Field(default=True)
    idempotency_key: Optional[str] = Field(default=None, max_length=128)
    override_title: Optional[str] = Field(default=None, max_length=100)
    override_description: Optional[str] = Field(default=None, max_length=5000)
    override_tags: Optional[List[str]] = Field(default=None)


class PublicationJobResponse(BaseModel):
    """Complete publishing job status and progress telemetry."""
    id: uuid.UUID
    project_id: uuid.UUID
    channel_id: uuid.UUID
    publication_package_id: Optional[uuid.UUID] = None
    idempotency_key: Optional[str] = None
    status: str
    current_stage: str
    privacy_status: str
    scheduled_publish_time: Optional[datetime] = None
    synthetic_media_declared: bool
    self_declared_made_for_kids: bool
    bytes_uploaded: int = 0
    total_bytes: int = 0
    progress_percent: float = 0.0
    retry_count: int = 0
    last_error_code: Optional[str] = None
    last_error_message: Optional[str] = None
    title: Optional[str] = None
    youtube_video_id: Optional[str] = None
    published_video_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PublicationProgressResponse(BaseModel):
    """Real-time upload progress monitor."""
    publishing_job_id: uuid.UUID
    status: str
    current_stage: str
    bytes_uploaded: int
    total_bytes: int
    progress_percent: float
    last_byte_offset: int
    is_resuming: bool
    retry_count: int
