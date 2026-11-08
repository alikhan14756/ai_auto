"""Lightweight in-memory schemas and execution contexts for QA validators."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from uuid import UUID


@dataclass
class CheckFindingSpec:
    """Specification of an issue or compliance finding discovered during a check."""
    category: str
    severity: str
    affected_artifact: str
    title: str
    explanation: str
    evidence: Dict[str, Any] = field(default_factory=dict)
    recommended_correction: str = ""
    requires_human_review: bool = False


@dataclass
class CheckResult:
    """Result of a single QA inspection check."""
    category: str
    check_name: str
    status: str
    score: float = 100.0
    execution_time_ms: int = 0
    metrics: Dict[str, Any] = field(default_factory=dict)
    findings: List[CheckFindingSpec] = field(default_factory=list)
    error_message: Optional[str] = None


@dataclass
class QAExecutionContext:
    """Consolidated production context passed to all QA validators."""
    project_id: UUID
    project_title: str
    project_format: str
    channel_id: UUID
    package_id: Optional[UUID] = None
    
    # Artifact objects / payloads
    script: Optional[Any] = None
    script_claims: List[Any] = field(default_factory=list)
    scenes: List[Any] = field(default_factory=list)
    narration_track: Optional[Any] = None
    voiceover: Optional[Any] = None
    timeline: Optional[Any] = None
    caption_asset: Optional[Any] = None
    render_job: Optional[Any] = None
    thumbnail: Optional[Any] = None
    metadata_draft: Optional[Any] = None
    media_assets: List[Any] = field(default_factory=list)
    quality_report: Optional[Any] = None
    
    # Local filesystem paths
    video_path: Optional[str] = None
    audio_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    subtitles_path: Optional[str] = None
    
    # Execution options
    strict_mode: bool = True
