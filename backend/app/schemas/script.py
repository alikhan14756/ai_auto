"""Pydantic schemas for Video Script Generation, Sections, Claims, and Quality Metrics."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


# ============================================================================
# LLM Structured Generation Schemas
# ============================================================================

class ScriptClaimSchema(BaseModel):
    """Atomic factual statement extracted from narration for verification."""
    claim_text: str = Field(..., description="Exact factual statement made in the script")
    extracted_entity: Optional[str] = Field(None, description="Primary subject or entity cited")
    claim_type: str = Field(default="FEATURE", description="BENCHMARK, PRICING, RELEASE_DATE, FEATURE")
    is_verified: bool = Field(default=False)
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    citation_url: Optional[str] = None
    citation_snippet: Optional[str] = None
    verification_explanation: Optional[str] = None


class ScriptSectionSchema(BaseModel):
    """Discrete narrative section with visual cues and estimated duration."""
    section_id: str = Field(..., description="Stable section identifier (e.g. sec_01)")
    section_order: int = Field(default=1, ge=1)
    title: str = Field(..., description="Section headline or topic")
    narration: str = Field(..., description="Spoken voiceover script for this section")
    visual_directive: str = Field(..., description="Visual scene directive or screen recording cue")
    estimated_seconds: int = Field(default=60, ge=5)
    transition_note: Optional[str] = None


class ScriptQualityMetrics(BaseModel):
    """Deterministic and algorithmic quality metrics for a script draft."""
    overall_score: float = Field(default=85.0, ge=0.0, le=100.0)
    hook_strength: float = Field(default=85.0, ge=0.0, le=100.0)
    clarity_score: float = Field(default=90.0, ge=0.0, le=100.0)
    evidence_coverage: float = Field(default=80.0, ge=0.0, le=100.0)
    repetition_index: float = Field(default=0.05, ge=0.0, le=1.0)
    historical_similarity: float = Field(default=0.0, ge=0.0, le=1.0)
    word_count: int = Field(default=0, ge=0)
    estimated_duration_seconds: int = Field(default=0, ge=0)
    unverified_claims_count: int = Field(default=0, ge=0)


class GeneratedScriptSchema(BaseModel):
    """Structured LLM output container for complete video script."""
    video_title: str
    format: str = Field(default="LONG_FORM", description="LONG_FORM or SHORTS")
    hook: str
    introduction: Optional[str] = None
    sections: List[ScriptSectionSchema] = Field(default_factory=list)
    conclusion: str
    call_to_action: str
    full_text: str
    claims: List[ScriptClaimSchema] = Field(default_factory=list)


class ScriptOutlineSectionSchema(BaseModel):
    """Section blueprint within an outline."""
    section_id: str = Field(..., description="Unique section ID")
    section_order: int = Field(default=1, ge=1)
    title: str
    key_points: List[str] = Field(default_factory=list)
    visual_concept: str
    estimated_seconds: int = 60


class ScriptOutlineResponse(BaseModel):
    """Response containing an early structured script outline."""
    project_id: UUID
    video_title: str
    format: str = "LONG_FORM"
    hook_concept: str
    target_duration_seconds: int
    sections: List[ScriptOutlineSectionSchema] = Field(default_factory=list)
    conclusion_concept: str
    call_to_action: str


class ScriptOutlineRequest(BaseModel):
    """Request payload to produce a structural outline prior to drafting."""
    project_id: UUID
    target_duration_seconds: Optional[int] = Field(None, ge=30, le=3600)
    tone: Optional[str] = "authoritative"
    custom_instructions: Optional[str] = None


# ============================================================================
# API Input / Output Schemas
# ============================================================================

class ScriptGenerateRequest(BaseModel):
    """Request payload to initiate AI script generation for a project."""
    project_id: UUID
    target_duration_seconds: Optional[int] = Field(None, ge=30, le=3600)
    tone: Optional[str] = Field(default="authoritative", description="authoritative, conversational, fast-paced")
    custom_instructions: Optional[str] = None


class ScriptClaimResponse(BaseModel):
    """API representation of a fact-checked claim."""
    id: UUID
    script_id: UUID
    project_id: UUID
    claim_text: str
    extracted_entity: Optional[str] = None
    claim_type: str
    is_verified: bool
    confidence_score: float
    citation_url: Optional[str] = None
    citation_snippet: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ScriptResponse(BaseModel):
    """API representation of a complete video script."""
    id: UUID
    project_id: UUID
    version: int
    full_text: str
    word_count: int
    estimated_duration_seconds: int
    is_locked: bool
    claims: List[ScriptClaimResponse] = Field(default_factory=list)
    quality_metrics: Optional[ScriptQualityMetrics] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ScriptUpdateRequest(BaseModel):
    """Payload to edit script content or lock state."""
    full_text: Optional[str] = None
    is_locked: Optional[bool] = None


class SectionRegenerateRequest(BaseModel):
    """Request to regenerate a single section without altering the rest of the script."""
    section_id: str
    custom_prompt: Optional[str] = None
