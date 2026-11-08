"""VideoProject Pydantic schemas."""

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class VideoProjectBase(BaseModel):
    title: str = Field(..., max_length=255)
    format: str = "LONG_FORM"  # LONG_FORM, SHORTS
    target_duration_seconds: int = 480


class VideoProjectCreate(VideoProjectBase):
    channel_id: uuid.UUID
    topic_id: Optional[uuid.UUID] = None


class VideoProjectUpdate(BaseModel):
    title: Optional[str] = None
    format: Optional[str] = None
    state: Optional[str] = None
    target_duration_seconds: Optional[int] = None
    actual_duration_seconds: Optional[float] = None


class VideoProjectRead(VideoProjectBase):
    id: uuid.UUID
    channel_id: uuid.UUID
    topic_id: Optional[uuid.UUID] = None
    state: str
    actual_duration_seconds: Optional[float] = None
    revision_number: int
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
