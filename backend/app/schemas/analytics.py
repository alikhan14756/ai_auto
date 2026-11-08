"""Pydantic v2 schemas for YouTube Analytics and Performance Intelligence API."""

from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class ChannelKPIOverview(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    channel_id: str
    total_views: int
    total_watch_time_minutes: float
    total_subscribers: int
    net_subscribers: int
    average_view_duration_seconds: float
    average_click_through_rate: float
    previous_period_views: Optional[int] = None
    views_growth_pct: Optional[float] = None
    watch_time_growth_pct: Optional[float] = None
    subscribers_growth_pct: Optional[float] = None
    data_freshness: str = "FRESH"
    start_date: str
    end_date: str


class DailyTrendPoint(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: str
    views: int
    watch_time_minutes: float
    subscribers_gained: int
    subscribers_lost: int
    likes: int
    comments: int


class VideoAnalyticsItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    youtube_video_id: str
    title: Optional[str] = None
    thumbnail_url: Optional[str] = None
    content_type: str = "LONG_FORM"
    published_at: Optional[str] = None
    views: int
    watch_time_minutes: float
    average_view_duration_seconds: float
    average_view_percentage: float
    likes: int
    comments: int
    shares: int
    click_through_rate: float
    retention_at_30s: float
    benchmark_status: str = "AVERAGE"  # OUTPERFORMING, AVERAGE, UNDERPERFORMING


class AudienceRetentionData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    youtube_video_id: str
    relative_retention_points: List[Dict[str, Any]] = Field(default_factory=list)
    drop_off_points: List[Dict[str, Any]] = Field(default_factory=list)
    average_view_duration_seconds: float
    retention_at_30s: float
    sample_size: int


class TrafficSourceItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    traffic_source_type: str
    views: int
    estimated_minutes_watched: float
    percentage: float


class PerformanceInsightItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    youtube_video_id: Optional[str] = None
    insight_type: str
    category: str
    title: str
    explanation: str
    evidence_metrics: Dict[str, Any] = Field(default_factory=dict)
    confidence_score: float
    limitations: Optional[str] = None
    status: str


class PerformanceRecommendationItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    recommendation_type: str
    title: str
    explanation: str
    supporting_metrics: Dict[str, Any] = Field(default_factory=dict)
    suggested_action: Dict[str, Any] = Field(default_factory=dict)
    confidence_level: str
    status: str
    applied_at: Optional[datetime] = None


class ContentStrategyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    channel_id: str
    topic_retention_weights: Dict[str, float]
    median_hook_retention: float
    top_performing_topics: List[Dict[str, Any]]
    recommended_formats: Dict[str, Any]


class AnalyticsSyncRequest(BaseModel):
    channel_id: UUID
    sync_type: str = "FULL"
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class AnalyticsSyncStatusResponse(BaseModel):
    channel_id: str
    last_sync_status: str
    last_sync_time: Optional[datetime] = None
    records_synced: int = 0
    active_jobs_count: int = 0
