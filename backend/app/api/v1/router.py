"""API Router v1 aggregator."""

from fastapi import APIRouter
from app.api.v1.endpoints import (
    health,
    auth,
    users,
    channels,
    projects,
    jobs,
    topics,
    providers,
    scripts,
    voice,
    visual,
    video,
    thumbnails,
    metadata,
    publication,
    qa,
    youtube,
    analytics,
    workflows,
    workflow_templates,
    automation,
    planning,
    system,
)

api_router = APIRouter()

# Register endpoint sub-routers
api_router.include_router(health.router, tags=["System"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(channels.router, prefix="/channels", tags=["Channels"])
api_router.include_router(projects.router, prefix="/projects", tags=["Projects"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["Jobs"])
api_router.include_router(topics.router, prefix="/topics", tags=["Topics"])
api_router.include_router(providers.router, prefix="/providers", tags=["Providers"])
api_router.include_router(scripts.router, prefix="/scripts", tags=["Scripts"])
api_router.include_router(voice.router, prefix="/voice", tags=["Voice & Narration"])
api_router.include_router(visual.router, tags=["Visual Studio & Media Library"])
api_router.include_router(video.router, tags=["Video Studio & Automated Editing"])
api_router.include_router(thumbnails.router, tags=["Thumbnail Studio & Composition"])
api_router.include_router(metadata.router, tags=["YouTube SEO Metadata Studio"])
api_router.include_router(publication.router, tags=["Publication Packages"])
api_router.include_router(qa.router, tags=["Quality Assurance & Veto Gate"])
api_router.include_router(youtube.router, tags=["YouTube Publishing"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["YouTube Analytics & Performance Intelligence"])
api_router.include_router(workflows.router, prefix="/workflows", tags=["Workflow Orchestration"])
api_router.include_router(workflow_templates.router, prefix="/workflow-templates", tags=["Workflow Templates"])
api_router.include_router(automation.router, prefix="/automation", tags=["Automation Policies & Governance"])
api_router.include_router(planning.router, prefix="/planning", tags=["Production Planning & Calendar"])
api_router.include_router(system.router, prefix="/system", tags=["System Health & Resource Governance"])
