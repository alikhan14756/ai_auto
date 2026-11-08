"""Registry mapping job_type strings to their handler instances."""

from typing import Dict, Type
from app.workers.handlers.base import BaseJobHandler, HardFailureException
from app.workers.handlers.demo import DemoJobHandler
from app.workers.handlers.topic_research import TopicResearchJobHandler
from app.workers.handlers.script_generation import (
    ScriptGenerationJobHandler,
    ScriptOutlineJobHandler,
    ScriptFactCheckJobHandler,
    ScriptQualityEvaluationJobHandler,
)
from app.workers.handlers.narration import (
    NarrationGenerationJobHandler,
    VoicePreviewJobHandler,
    NarrationSectionRegenerateJobHandler,
)
from app.workers.handlers.visual import (
    StoryboardGenerationJobHandler,
    VisualAssetSearchJobHandler,
    ImageGenerationJobHandler,
)
from app.workers.handlers.video import (
    TimelineGenerationJobHandler,
    VideoRenderJobHandler,
    VideoValidationJobHandler,
)
from app.workers.handlers.thumbnail_seo import (
    ThumbnailConceptGenerationJobHandler,
    ThumbnailCompositionRenderJobHandler,
    SEOMetadataGenerationJobHandler,
    PublicationPackagePreparationJobHandler,
)
from app.workers.handlers.qa import QAPackageInspectionJobHandler
from app.workers.handlers.youtube_publishing import (
    YouTubeVideoUploadJobHandler,
    YouTubeChannelSyncJobHandler,
)
from app.workers.handlers.analytics import (
    YouTubeChannelAnalyticsSyncJobHandler,
    YouTubeVideoAnalyticsSyncJobHandler,
    YouTubeRetentionAnalyticsSyncJobHandler,
    YouTubeTrafficAnalyticsSyncJobHandler,
    YouTubeAnalyticsReconciliationJobHandler,
)
from app.workers.handlers.orchestration import (
    WorkflowExecutionJobHandler,
    WorkflowStageDispatchJobHandler,
    ScheduledWorkflowTriggerJobHandler,
    WorkflowRecoveryJobHandler,
)
from app.core.logging import logger


class JobHandlerRegistry:
    """Manages mapping between job types and their execution handlers."""

    def __init__(self):
        self._handlers: Dict[str, BaseJobHandler] = {}

    def register(self, job_type: str, handler: BaseJobHandler) -> None:
        """Register a handler instance for a given job_type."""
        self._handlers[job_type] = handler
        logger.debug(f"Registered handler for job type: {job_type}")

    def get_handler(self, job_type: str) -> BaseJobHandler:
        """Retrieve the handler for a job_type, or raise HardFailureException if unsupported."""
        handler = self._handlers.get(job_type)
        if not handler:
            raise HardFailureException(
                f"Unsupported job type: '{job_type}'. Registered types: {list(self._handlers.keys())}"
            )
        return handler


# Global registry with standard default handlers
registry = JobHandlerRegistry()

# Register M04 demo and verification handlers
registry.register("TEST_DEMO", DemoJobHandler())
registry.register("DEMO_JOB", DemoJobHandler())
registry.register("DISCOVER_TOPICS", TopicResearchJobHandler())
registry.register("GENERATE_SCRIPT", ScriptGenerationJobHandler())
registry.register("SCRIPT_OUTLINE_GENERATION", ScriptOutlineJobHandler())
registry.register("SCRIPT_FACT_CHECK", ScriptFactCheckJobHandler())
registry.register("SCRIPT_QUALITY_EVALUATION", ScriptQualityEvaluationJobHandler())
registry.register("NARRATION_GENERATION", NarrationGenerationJobHandler())
registry.register("VOICE_PREVIEW_GENERATION", VoicePreviewJobHandler())
registry.register("NARRATION_SECTION_REGENERATE", NarrationSectionRegenerateJobHandler())
registry.register("STORYBOARD_GENERATION", StoryboardGenerationJobHandler())
registry.register("VISUAL_ASSET_SEARCH", VisualAssetSearchJobHandler())
registry.register("IMAGE_GENERATION", ImageGenerationJobHandler())
registry.register("TIMELINE_GENERATION", TimelineGenerationJobHandler())
registry.register("VIDEO_RENDER", VideoRenderJobHandler())
registry.register("VIDEO_VALIDATION", VideoValidationJobHandler())
registry.register("THUMBNAIL_CONCEPT_GENERATION", ThumbnailConceptGenerationJobHandler())
registry.register("THUMBNAIL_COMPOSITION_RENDER", ThumbnailCompositionRenderJobHandler())
registry.register("SEO_METADATA_GENERATION", SEOMetadataGenerationJobHandler())
registry.register("PUBLICATION_PACKAGE_PREPARATION", PublicationPackagePreparationJobHandler())
registry.register("QA_PACKAGE_INSPECTION", QAPackageInspectionJobHandler())
registry.register("YOUTUBE_VIDEO_UPLOAD", YouTubeVideoUploadJobHandler())
registry.register("YOUTUBE_CHANNEL_SYNC", YouTubeChannelSyncJobHandler())
registry.register("YOUTUBE_CHANNEL_ANALYTICS_SYNC", YouTubeChannelAnalyticsSyncJobHandler())
registry.register("YOUTUBE_VIDEO_ANALYTICS_SYNC", YouTubeVideoAnalyticsSyncJobHandler())
registry.register("YOUTUBE_RETENTION_ANALYTICS_SYNC", YouTubeRetentionAnalyticsSyncJobHandler())
registry.register("YOUTUBE_TRAFFIC_ANALYTICS_SYNC", YouTubeTrafficAnalyticsSyncJobHandler())
registry.register("YOUTUBE_ANALYTICS_RECONCILIATION", YouTubeAnalyticsReconciliationJobHandler())
registry.register("WORKFLOW_EXECUTION", WorkflowExecutionJobHandler())
registry.register("WORKFLOW_STAGE_DISPATCH", WorkflowStageDispatchJobHandler())
registry.register("SCHEDULED_WORKFLOW_TRIGGER", ScheduledWorkflowTriggerJobHandler())
registry.register("WORKFLOW_RECOVERY", WorkflowRecoveryJobHandler())

# Aliases for Workflow Orchestration Template stage job types
registry.register("GENERATE_NARRATION", NarrationGenerationJobHandler())
registry.register("PLAN_VISUALS", StoryboardGenerationJobHandler())
registry.register("RENDER_VIDEO", VideoRenderJobHandler())
registry.register("GENERATE_THUMBNAIL_AND_METADATA", ThumbnailCompositionRenderJobHandler())
registry.register("EVALUATE_PUBLICATION_READINESS", QAPackageInspectionJobHandler())
registry.register("YOUTUBE_PUBLICATION_DISPATCH", YouTubeVideoUploadJobHandler())
