"""Channel and ChannelSettings Pydantic schemas."""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class ChannelSettingsBase(BaseModel):
    niche_keywords: List[str] = Field(default_factory=list)
    default_privacy: str = "unlisted"
    default_category_id: str = "28"
    weekly_cadence_long: int = 2
    weekly_cadence_shorts: int = 3
    auto_publish_enabled: bool = False
    max_monthly_spend_usd: float = 0.00
    topic_retention_weights: Dict[str, Any] = Field(default_factory=dict)


class ChannelSettingsUpdate(BaseModel):
    niche_keywords: Optional[List[str]] = None
    default_privacy: Optional[str] = None
    default_category_id: Optional[str] = None
    weekly_cadence_long: Optional[int] = None
    weekly_cadence_shorts: Optional[int] = None
    auto_publish_enabled: Optional[bool] = None
    max_monthly_spend_usd: Optional[float] = None
    topic_retention_weights: Optional[Dict[str, Any]] = None


class ChannelSettingsRead(ChannelSettingsBase):
    id: uuid.UUID
    channel_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChannelBase(BaseModel):
    youtube_channel_id: str
    title: str
    description: Optional[str] = None
    custom_url: Optional[str] = None
    thumbnail_url: Optional[str] = None


class ChannelCreate(ChannelBase):
    oauth_refresh_token: str
    token_expires_at: Optional[datetime] = None


class ChannelUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    custom_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    is_active: Optional[bool] = None


class ChannelRead(ChannelBase):
    id: uuid.UUID
    user_id: uuid.UUID
    subscriber_count: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    settings: Optional[ChannelSettingsRead] = None

    model_config = ConfigDict(from_attributes=True)
