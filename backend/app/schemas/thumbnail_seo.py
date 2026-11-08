"""Pydantic v2 schemas for Thumbnails, SEO Metadata Drafts, and Publication Packages."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


# ============================================================================
# Thumbnail Schemas
# ============================================================================

class ThumbnailConceptItem(BaseModel):
    variant: str
    concept_name: str
    headline_text: str
    badge_text: Optional[str] = None
    style_preset: str
    focal_element: str
    color_palette: List[str]
    composition_strategy: str
    visual_hook: str
    target_emotion: str


class ThumbnailConceptGenerateRequest(BaseModel):
    project_id: Optional[UUID] = None
    custom_guidance: Optional[str] = None
    headline: Optional[str] = None
    style_preset: Optional[str] = None


class ThumbnailComposeRequest(BaseModel):
    project_id: UUID
    variant: str = "A"
    headline_text: str = Field(..., max_length=100)
    badge_text: Optional[str] = Field(None, max_length=50)
    style_preset: str = "modern_tech_editorial"
    accent_color: Optional[str] = "#FF7A00"
    background_image_path: Optional[str] = None
    show_grid: bool = True
    show_glow: bool = True
    darken_background: float = Field(0.55, ge=0.0, le=1.0)


class ThumbnailUpdateRequest(BaseModel):
    headline_text: Optional[str] = Field(None, max_length=100)
    badge_text: Optional[str] = Field(None, max_length=50)
    style_preset: Optional[str] = None
    accent_color: Optional[str] = None
    is_selected: Optional[bool] = None
    composition_data: Optional[Dict[str, Any]] = None


class ThumbnailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    variant_code: str
    storage_path: str
    headline_text: str
    accent_color_hex: str = "#FF7A00"
    style_preset: Optional[str] = "modern_tech_editorial"
    width: int = 1280
    height: int = 720
    file_size_bytes: int = 0
    format: str = "PNG"
    is_selected: bool = False
    composition_data: Optional[Dict[str, Any]] = None
    concept_data: Optional[Dict[str, Any]] = None
    quality_status: str = "PENDING"
    quality_report: Optional[Dict[str, Any]] = None
    version: int = 1
    created_at: datetime
    updated_at: datetime


# ============================================================================
# SEO Metadata Schemas
# ============================================================================

class ChapterItem(BaseModel):
    timestamp: str
    title: str


class MetadataGenerateRequest(BaseModel):
    project_id: UUID
    channel_name: Optional[str] = "Creator Studio AI"
    social_links: Optional[Dict[str, str]] = None


class MetadataUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=5000)
    tags: Optional[List[str]] = None
    hashtags: Optional[List[str]] = None
    chapters: Optional[List[Dict[str, Any]]] = None
    pinned_comment: Optional[str] = Field(None, max_length=2000)


class SEOScoreReportResponse(BaseModel):
    seo_score: float
    pairing_score: float
    status: str
    issues: List[str] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    title_analysis: Dict[str, Any] = Field(default_factory=dict)
    description_analysis: Dict[str, Any] = Field(default_factory=dict)
    tags_analysis: Dict[str, Any] = Field(default_factory=dict)
    pairing_analysis: Optional[Dict[str, Any]] = None


class MetadataDraftResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    title: str
    title_candidates: List[Any] = Field(default_factory=list)
    description: str
    tags: List[str] = Field(default_factory=list)
    hashtags: List[str] = Field(default_factory=list)
    chapters: List[Dict[str, Any]] = Field(default_factory=list)
    pinned_comment: Optional[str] = None
    synthetic_media_disclosure: bool = True
    seo_score: float = 0.0
    seo_report: Dict[str, Any] = Field(default_factory=dict)
    pairing_score: float = 0.0
    pairing_report: Dict[str, Any] = Field(default_factory=dict)
    version: int = 1
    is_approved: bool = False
    created_at: datetime
    updated_at: datetime


# ============================================================================
# Publication Package Schemas
# ============================================================================

class PublicationPackageCreateRequest(BaseModel):
    project_id: UUID


class PublicationPackageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    render_job_id: Optional[UUID] = None
    thumbnail_id: Optional[UUID] = None
    metadata_id: Optional[UUID] = None
    status: str
    package_manifest: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
