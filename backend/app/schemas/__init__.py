"""Pydantic schemas package."""

from app.schemas.user import UserBase, UserCreate, UserUpdate, UserRead
from app.schemas.channel import (
    ChannelBase,
    ChannelCreate,
    ChannelUpdate,
    ChannelRead,
    ChannelSettingsBase,
    ChannelSettingsUpdate,
    ChannelSettingsRead,
)
from app.schemas.project import (
    VideoProjectBase,
    VideoProjectCreate,
    VideoProjectUpdate,
    VideoProjectRead,
)
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.script import (
    ScriptSectionSchema,
    ScriptClaimSchema,
    ScriptQualityMetrics,
    GeneratedScriptSchema,
    ScriptGenerateRequest,
    ScriptResponse,
    ScriptClaimResponse,
    ScriptUpdateRequest,
    SectionRegenerateRequest,
)
from app.schemas.job import JobCreate, JobRead, JobProgressRead, JobListResponse
from app.schemas.topic import (
    TopicCandidate,
    TopicDiscoveryBatch,
    TopicResearchTriggerRequest,
    TopicResponse,
    TopicListResponse,
    TopicStatusUpdate,
    ResearchSourceResponse,
)
from app.schemas.provider import (
    ProviderHealthResponse,
    ProviderStatusResponse,
    UsageSummaryResponse,
    ProviderTestRequest,
    ProviderTestResponse,
)
from app.schemas.thumbnail_seo import (
    ThumbnailResponse,
    ThumbnailComposeRequest,
    ThumbnailUpdateRequest,
    ThumbnailConceptGenerateRequest,
    MetadataDraftResponse,
    MetadataGenerateRequest,
    MetadataUpdateRequest,
    SEOScoreReportResponse,
    PublicationPackageResponse,
    PublicationPackageCreateRequest,
)

__all__ = [
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserRead",
    "ChannelBase",
    "ChannelCreate",
    "ChannelUpdate",
    "ChannelRead",
    "ChannelSettingsBase",
    "ChannelSettingsUpdate",
    "ChannelSettingsRead",
    "VideoProjectBase",
    "VideoProjectCreate",
    "VideoProjectUpdate",
    "VideoProjectRead",
    "LoginRequest",
    "RegisterRequest",
    "TokenResponse",
    "JobCreate",
    "JobRead",
    "JobProgressRead",
    "JobListResponse",
]
