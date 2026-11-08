"""Pydantic v2 schemas for Visual Planning, Asset Discovery, and Storyboards."""

from typing import List, Optional, Any
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict
from app.providers.visual.base import StockAssetResult, StockSearchResult


class MediaAssetResponse(BaseModel):
    """Media asset catalog item response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    channel_id: Optional[UUID] = None
    project_id: UUID
    scene_id: Optional[UUID] = None
    title: str
    description: Optional[str] = None
    asset_type: str
    asset_category: str
    source_provider: str
    source_url: Optional[str] = None
    preview_url: Optional[str] = None
    author_name: Optional[str] = None
    author_url: Optional[str] = None
    license_type: str
    license_status: str
    attribution_text: Optional[str] = None
    aspect_ratio: str
    width: Optional[int] = None
    height: Optional[int] = None
    mime_type: str
    duration_seconds: Optional[Decimal] = None
    file_size_bytes: int
    sha256_hash: str
    is_verified: bool
    is_archived: bool
    created_at: datetime


class MediaAssetListResponse(BaseModel):
    """Paginated list of media assets."""

    total: int
    assets: List[MediaAssetResponse]


class LicenseUpdateRequest(BaseModel):
    """Request schema for modifying asset licensing provenance."""

    license_status: str = Field(..., description="VERIFIED_COMMERCIAL, ATTRIBUTION_REQUIRED, LICENSE_REVIEW_REQUIRED, RESTRICTED")
    attribution_text: Optional[str] = None
    license_type: Optional[str] = None


class StoryboardSceneResponse(BaseModel):
    """Storyboard scene unit with assigned asset and visual specifications."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    storyboard_id: Optional[UUID] = None
    scene_order: int
    narration_text: str
    visual_archetype: str
    visual_directive: str
    visual_purpose: str
    suggested_asset_type: str
    search_keywords: List[str] = Field(default_factory=list)
    image_prompt: Optional[str] = None
    transition: str
    review_status: str
    duration_seconds: Decimal
    selected_asset_id: Optional[UUID] = None
    selected_asset: Optional[MediaAssetResponse] = None
    created_at: datetime


class StoryboardResponse(BaseModel):
    """Full visual storyboard representation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    script_id: Optional[UUID] = None
    narration_track_id: Optional[UUID] = None
    version: int
    status: str
    aspect_ratio: str
    scene_count: int
    approved_scene_count: int
    scenes: List[StoryboardSceneResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class StoryboardGenerateRequest(BaseModel):
    """Request to generate or synchronize a project's storyboard."""

    project_id: UUID


class SceneUpdateRequest(BaseModel):
    """Request to update a scene's visual specifications."""

    visual_directive: Optional[str] = None
    visual_purpose: Optional[str] = None
    suggested_asset_type: Optional[str] = None
    search_keywords: Optional[List[str]] = None
    image_prompt: Optional[str] = None
    transition: Optional[str] = None
    review_status: Optional[str] = None
    duration_seconds: Optional[Decimal] = None


class SceneReorderRequest(BaseModel):
    """Request to reorder storyboard scene sequence."""

    ordered_scene_ids: List[UUID]


class AssetAssignRequest(BaseModel):
    """Request to assign an existing media asset to a scene."""

    asset_id: UUID


class StockSearchRequest(BaseModel):
    """Request to search external stock media."""

    query: str
    aspect_ratio: str = "16:9"
    provider: Optional[str] = None
    page: int = 1
    per_page: int = 10


class StockAssetImportRequest(BaseModel):
    """Request to import a stock search result into project library."""

    channel_id: UUID
    project_id: UUID
    scene_id: Optional[UUID] = None
    stock_item: StockAssetResult


class ImageGenerateRequest(BaseModel):
    """Request to synthesize an AI image for a scene."""

    channel_id: UUID
    project_id: UUID
    scene_id: Optional[UUID] = None
    prompt: str
    aspect_ratio: str = "16:9"
    style: str = "photorealistic"
    provider: Optional[str] = None
