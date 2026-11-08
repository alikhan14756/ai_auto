"""Creator Studio AI Relational Models Package.
Exports all 21 core domain models for SQLAlchemy discovery.
"""

from app.models.base import UUIDPrimaryKeyMixin, TimestampMixin
from app.models.user import User
from app.models.channel import Channel, ChannelSettings
from app.models.topic import Topic, ResearchSource
from app.models.project import VideoProject
from app.models.script import Script, ScriptClaim
from app.models.scene import Scene
from app.models.storyboard import Storyboard
from app.models.media import MediaAsset
from app.models.voice import Voiceover, VoiceProfile, NarrationTrack
from app.models.timeline import VideoTimeline, TimelineScene, CaptionAsset
from app.models.thumbnail import Thumbnail
from app.models.metadata import VideoMetadataDraft
from app.models.publication import PublicationPackage
from app.models.render import RenderJob
from app.models.qa import (
    QualityReport,
    QARun,
    QACheck,
    QAFinding,
    QACategoryScore,
    QAException,
)
from app.models.publishing import PublishingJob, YouTubeVideo, YouTubeUploadSession
from app.models.analytics import (
    AnalyticsSnapshot,
    ChannelAnalyticsSnapshot,
    VideoAnalyticsSnapshot,
    AudienceRetentionSnapshot,
    TrafficSourceSnapshot,
    PerformanceInsight,
    PerformanceRecommendation,
    AnalyticsSyncRun,
)
from app.models.job import AutomationJob
from app.models.usage import ProviderUsage
from app.models.template import PromptTemplate
from app.models.audit import AuditLog
from app.models.workflow import (
    WorkflowTemplate,
    WorkflowDefinition,
    WorkflowExecution,
    WorkflowStage,
    WorkflowPolicy,
    WorkflowSchedule,
    ResourceUsageRecord,
    WorkflowEvent,
    WorkflowFailure,
    OptimizationRecommendation,
    WORKFLOW_STATUS_DRAFT,
    WORKFLOW_STATUS_SCHEDULED,
    WORKFLOW_STATUS_READY,
    WORKFLOW_STATUS_RUNNING,
    WORKFLOW_STATUS_PAUSED,
    WORKFLOW_STATUS_WAITING_FOR_APPROVAL,
    WORKFLOW_STATUS_RECOVERING,
    WORKFLOW_STATUS_COMPLETED,
    WORKFLOW_STATUS_FAILED,
    WORKFLOW_STATUS_CANCELLED,
    VALID_WORKFLOW_STATUSES,
    ALLOWED_WORKFLOW_TRANSITIONS,
    STAGE_STATUS_PENDING,
    STAGE_STATUS_RUNNING,
    STAGE_STATUS_WAITING_APPROVAL,
    STAGE_STATUS_COMPLETED,
    STAGE_STATUS_FAILED,
    STAGE_STATUS_SKIPPED,
    AUTOMATION_LEVEL_MANUAL,
    AUTOMATION_LEVEL_ASSISTED,
    AUTOMATION_LEVEL_CONTROLLED,
    AUTOMATION_LEVEL_SCHEDULED,
)

__all__ = [
    "UUIDPrimaryKeyMixin",
    "TimestampMixin",
    "User",
    "Channel",
    "ChannelSettings",
    "Topic",
    "ResearchSource",
    "VideoProject",
    "Script",
    "ScriptClaim",
    "Scene",
    "Storyboard",
    "MediaAsset",
    "Voiceover",
    "VoiceProfile",
    "NarrationTrack",
    "VideoTimeline",
    "TimelineScene",
    "CaptionAsset",
    "Thumbnail",
    "VideoMetadataDraft",
    "PublicationPackage",
    "RenderJob",
    "QualityReport",
    "QARun",
    "QACheck",
    "QAFinding",
    "QACategoryScore",
    "QAException",
    "PublishingJob",
    "YouTubeVideo",
    "YouTubeUploadSession",
    "AnalyticsSnapshot",
    "ChannelAnalyticsSnapshot",
    "VideoAnalyticsSnapshot",
    "AudienceRetentionSnapshot",
    "TrafficSourceSnapshot",
    "PerformanceInsight",
    "PerformanceRecommendation",
    "AnalyticsSyncRun",
    "AutomationJob",
    "ProviderUsage",
    "PromptTemplate",
    "AuditLog",
    "WorkflowTemplate",
    "WorkflowDefinition",
    "WorkflowExecution",
    "WorkflowStage",
    "WorkflowPolicy",
    "WorkflowSchedule",
    "ResourceUsageRecord",
    "WorkflowEvent",
    "WorkflowFailure",
    "OptimizationRecommendation",
    "WORKFLOW_STATUS_DRAFT",
    "WORKFLOW_STATUS_SCHEDULED",
    "WORKFLOW_STATUS_READY",
    "WORKFLOW_STATUS_RUNNING",
    "WORKFLOW_STATUS_PAUSED",
    "WORKFLOW_STATUS_WAITING_FOR_APPROVAL",
    "WORKFLOW_STATUS_RECOVERING",
    "WORKFLOW_STATUS_COMPLETED",
    "WORKFLOW_STATUS_FAILED",
    "WORKFLOW_STATUS_CANCELLED",
    "VALID_WORKFLOW_STATUSES",
    "ALLOWED_WORKFLOW_TRANSITIONS",
    "STAGE_STATUS_PENDING",
    "STAGE_STATUS_RUNNING",
    "STAGE_STATUS_WAITING_APPROVAL",
    "STAGE_STATUS_COMPLETED",
    "STAGE_STATUS_FAILED",
    "STAGE_STATUS_SKIPPED",
    "AUTOMATION_LEVEL_MANUAL",
    "AUTOMATION_LEVEL_ASSISTED",
    "AUTOMATION_LEVEL_CONTROLLED",
    "AUTOMATION_LEVEL_SCHEDULED",
]
