"""Pydantic v2 schemas for Video Timelines, Scenes, Captions, and Render Jobs."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class TimelineSceneBase(BaseModel):
    sequence_number: int
    duration_seconds: Decimal
    transition_type: str = "cut"
    transition_duration: Decimal = Decimal("0.50")
    motion_effect: str = "zoom_in"
    motion_intensity: float = 1.15
    visual_asset_path: Optional[str] = None


class TimelineSceneUpdate(BaseModel):
    duration_seconds: Optional[float] = Field(None, gt=0.0, description="Duration in seconds")
    transition_type: Optional[str] = Field(None, description="cut, fade, dissolve, wipeleft, wiperight")
    motion_effect: Optional[str] = Field(None, description="static, zoom_in, zoom_out, pan_left, pan_right")
    asset_id: Optional[UUID] = None
    visual_asset_path: Optional[str] = None


class TimelineSceneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    timeline_id: UUID
    scene_id: Optional[UUID] = None
    sequence_number: int
    start_time_seconds: Decimal
    end_time_seconds: Decimal
    duration_seconds: Decimal
    asset_id: Optional[UUID] = None
    visual_asset_path: Optional[str] = None
    transition_type: str
    transition_duration: Decimal
    motion_effect: str
    motion_intensity: float
    voiceover_segment_id: Optional[UUID] = None
    clip_settings: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class SceneReorderRequest(BaseModel):
    scene_ids: List[UUID] = Field(..., min_length=1, description="Ordered list of timeline scene IDs")


class CaptionAssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    timeline_id: UUID
    format: str
    style_preset: str
    primary_color: str
    highlight_color: str
    font_name: str
    font_size: int
    file_path: Optional[str] = None
    is_embedded: bool
    created_at: datetime


class TimelineCreateRequest(BaseModel):
    storyboard_id: UUID
    aspect_ratio: Optional[str] = Field(None, description="'16:9' or '9:16'")
    fps: int = Field(30, ge=24, le=60)
    music_asset_id: Optional[UUID] = None
    music_volume: float = Field(0.15, ge=0.0, le=1.0)
    ducking_enabled: bool = True


class VideoTimelineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    aspect_ratio: str
    fps: int
    width: int
    height: int
    total_duration_seconds: Decimal
    status: str
    music_asset_id: Optional[UUID] = None
    music_volume: float
    ducking_enabled: bool
    ducking_db: float
    narration_track_id: Optional[UUID] = None
    settings: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    timeline_scenes: List[TimelineSceneResponse] = Field(default_factory=list)
    captions: List[CaptionAssetResponse] = Field(default_factory=list)


class RenderTriggerRequest(BaseModel):
    timeline_id: UUID
    mode: Optional[str] = Field(None, description="'auto', 'ffmpeg', or 'mock'")
    resolution: Optional[str] = Field("1080p", description="Resolution name")


class RenderJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    timeline_id: Optional[UUID] = None
    resolution: str
    video_width: int
    video_height: int
    fps: int
    aspect_ratio: str
    renderer_mode: str
    current_stage: str
    progress_percentage: int
    output_video_path: Optional[str] = None
    render_duration_seconds: Optional[Decimal] = None
    status: str
    quality_status: str
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class QualityReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    render_job_id: UUID
    all_checks_passed: bool
    black_frame_duration_max: Decimal
    freeze_duration_max: Decimal
    integrated_loudness_lufs: Decimal
    max_true_peak_dbtp: Decimal
    unverified_claims_count: int
    transcript_similarity_ratio: Decimal
    diagnostic_details: Dict[str, Any]
    created_at: datetime
