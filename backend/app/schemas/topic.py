"""Pydantic schemas for Topic Research, Discovery, Scoring, and Sources."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, HttpUrl


# ============================================================================
# LLM Structured Generation Schemas
# ============================================================================

class ResearchSourceCandidate(BaseModel):
    """Factual reference or documentation link supporting a topic candidate."""
    source_url: str = Field(..., description="Absolute URL to authoritative paper, documentation, or post")
    source_title: str = Field(..., description="Descriptive headline of the source")
    extracted_summary: str = Field(..., description="Key facts, benchmarks, or insights extracted")
    relevance_score: float = Field(default=0.90, ge=0.0, le=1.0)


class TopicCandidate(BaseModel):
    """Raw structured candidate returned by the AI provider."""
    title: str = Field(..., min_length=10, max_length=200, description="Compelling YouTube video title")
    niche_category: str = Field(..., description="Specific sub-niche or technical domain")
    angle: str = Field(..., description="Unique narrative perspective or problem-solution thesis")
    target_audience: str = Field(..., description="Target developer persona or viewer demographic")
    audience_relevance: float = Field(default=85.0, ge=0.0, le=100.0)
    practical_value: float = Field(default=85.0, ge=0.0, le=100.0)
    originality: float = Field(default=80.0, ge=0.0, le=100.0)
    search_volume_score: float = Field(default=75.0, ge=0.0, le=100.0)
    competition_score: float = Field(default=40.0, ge=0.0, le=100.0)
    rationale: str = Field(..., description="Why this topic will perform strongly right now")
    sources: List[ResearchSourceCandidate] = Field(default_factory=list)


class TopicDiscoveryBatch(BaseModel):
    """Top-level schema for structured AI generation."""
    topics: List[TopicCandidate] = Field(default_factory=list)


# ============================================================================
# API Input / Output Schemas
# ============================================================================

class TopicResearchTriggerRequest(BaseModel):
    """Request payload to initiate a background topic discovery job."""
    channel_id: UUID
    niche_override: Optional[str] = None
    count: int = Field(default=5, ge=1, le=15)


class ResearchSourceResponse(BaseModel):
    """API view for a topic's verified research reference."""
    id: UUID
    topic_id: UUID
    source_url: str
    source_title: Optional[str] = None
    extracted_summary: str
    relevance_score: float
    created_at: datetime

    model_config = {"from_attributes": True}


class TopicResponse(BaseModel):
    """API view for a scored and persisted topic."""
    id: UUID
    channel_id: UUID
    title: str
    niche_category: str
    opportunity_score: float
    search_volume_score: float
    competition_score: float
    status: str
    raw_discovery_payload: Optional[Dict[str, Any]] = None
    research_sources: List[ResearchSourceResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TopicListResponse(BaseModel):
    """Paginated collection of topics."""
    items: List[TopicResponse]
    total: int


class TopicStatusUpdate(BaseModel):
    """Payload to update topic status (e.g. approve or archive)."""
    status: str = Field(..., pattern="^(DISCOVERED|SELECTED|ARCHIVED)$")
