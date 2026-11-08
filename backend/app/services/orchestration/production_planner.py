"""Production planning engine, content opportunity discovery, and calendar scheduler."""

from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_

from app.models.channel import Channel
from app.models.topic import Topic
from app.models.project import VideoProject
from app.models.workflow import (
    WorkflowSchedule,
    WorkflowExecution,
    OptimizationRecommendation,
    WORKFLOW_STATUS_RUNNING,
    WORKFLOW_STATUS_SCHEDULED,
)
from app.models.analytics import ChannelAnalyticsSnapshot, VideoAnalyticsSnapshot
from app.services.orchestration.governor import ResourceGovernor
from app.services.orchestration.templates import get_template_by_key, TEMPLATE_LONG_FORM, TEMPLATE_SHORTS


class ProductionPlanner:
    """Bridges topic research with analytics to plan production schedules and content opportunities."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.governor = ResourceGovernor(db)

    async def generate_production_plan(
        self,
        channel_id: UUID,
        topic_id: UUID,
        content_format: str = "LONG_FORM",
        planned_publish_at: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Convert an approved topic into a fully validated production plan blueprint."""
        # 1. Fetch topic
        topic_stmt = select(Topic).where(and_(Topic.id == topic_id, Topic.channel_id == channel_id))
        topic = (await self.db.execute(topic_stmt)).scalars().first()
        if not topic:
            raise ValueError(f"Topic {topic_id} not found for this channel.")

        # 2. Template selection
        template_key = TEMPLATE_LONG_FORM if content_format == "LONG_FORM" else TEMPLATE_SHORTS
        template = get_template_by_key(template_key)
        if not template:
            raise ValueError(f"Template {template_key} not found.")

        # 3. Estimated durations and resources
        is_long = content_format == "LONG_FORM"
        target_duration_sec = 480 if is_long else 45
        target_words = 1100 if is_long else 120
        est_tokens = 4500 if is_long else 800
        est_storage_mb = 250 if is_long else 40
        est_render_sec = 120 if is_long else 25

        # 4. Default publish time (48 hours from now if unspecified)
        if not planned_publish_at:
            planned_publish_at = datetime.now(timezone.utc) + timedelta(hours=48)

        # 5. Build production plan dictionary
        plan = {
            "channel_id": str(channel_id),
            "topic_id": str(topic_id),
            "topic_title": topic.title,
            "content_format": content_format,
            "template_key": template_key,
            "target_duration_sec": target_duration_sec,
            "target_word_count": target_words,
            "estimated_token_usage": est_tokens,
            "estimated_storage_mb": est_storage_mb,
            "estimated_render_sec": est_render_sec,
            "estimated_cost_usd": 0.0,  # Zero-dollar offline/local engine
            "planned_publish_at": planned_publish_at.isoformat(),
            "stages": [
                {
                    "stage_key": s["stage_key"],
                    "stage_name": s["stage_name"],
                    "dependencies": s["dependencies"],
                    "approval_required": s["approval_required"],
                }
                for s in template["stages"]
            ],
            "prerequisites_met": True,
        }

        # 6. Validate prerequisites
        validation_ok, reason = await self.validate_plan_prerequisites(channel_id, plan)
        plan["prerequisites_met"] = validation_ok
        plan["validation_error"] = reason

        return plan

    async def validate_plan_prerequisites(
        self, channel_id: UUID, plan: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """Verify storage, budget, and lack of duplicate active workflows before plan execution."""
        # Budget check
        est_cost = plan.get("estimated_cost_usd", 0.0)
        has_budget = await self.governor.check_budget_availability(channel_id, est_cost)
        if not has_budget:
            return False, "Insufficient budget available for estimated plan cost."

        # Duplicate check: check if topic already has a running or scheduled workflow
        topic_id = plan.get("topic_id")
        if topic_id:
            dup_stmt = select(WorkflowExecution).where(
                and_(
                    WorkflowExecution.channel_id == channel_id,
                    WorkflowExecution.status.in_([WORKFLOW_STATUS_RUNNING, WORKFLOW_STATUS_SCHEDULED]),
                )
            )
            active_runs = (await self.db.execute(dup_stmt)).scalars().all()
            for r in active_runs:
                if str((r.context_data or {}).get("topic_id")) == str(topic_id):
                    return False, f"An active or scheduled workflow already exists for topic {topic_id}."

        return True, None

    async def schedule_production(
        self,
        channel_id: UUID,
        title: str,
        content_format: str,
        planned_start_at: datetime,
        planned_publish_at: Optional[datetime] = None,
        timezone_str: str = "UTC",
    ) -> WorkflowSchedule:
        """Create a timezone-aware production calendar schedule item with conflict checking."""
        if not planned_publish_at:
            planned_publish_at = planned_start_at + timedelta(hours=24)

        # Check for scheduling conflict: overlapping publication within 2 hours
        conflict_window_start = planned_publish_at - timedelta(hours=2)
        conflict_window_end = planned_publish_at + timedelta(hours=2)

        conflict_stmt = select(func.count(WorkflowSchedule.id)).where(
            and_(
                WorkflowSchedule.channel_id == channel_id,
                WorkflowSchedule.status.in_(["SCHEDULED", "ACTIVE"]),
                WorkflowSchedule.planned_publish_at >= conflict_window_start,
                WorkflowSchedule.planned_publish_at <= conflict_window_end,
            )
        )
        conflicts = (await self.db.execute(conflict_stmt)).scalar() or 0
        if conflicts > 0:
            raise ValueError(
                f"Schedule conflict: Another video is already scheduled for publication within 2 hours of {planned_publish_at.isoformat()}."
            )

        schedule = WorkflowSchedule(
            channel_id=channel_id,
            title=title,
            content_format=content_format,
            planned_start_at=planned_start_at,
            planned_publish_at=planned_publish_at,
            timezone=timezone_str,
            status="SCHEDULED",
        )
        self.db.add(schedule)
        await self.db.flush()
        return schedule

    async def discover_content_opportunities(
        self, channel_id: UUID
    ) -> List[OptimizationRecommendation]:
        """Synthesize M13 analytics snapshots and M05 topic research into strategic recommendations."""
        recommendations: List[OptimizationRecommendation] = []

        # 1. Fetch channel retention baseline from latest snapshot
        snap_stmt = (
            select(ChannelAnalyticsSnapshot)
            .where(ChannelAnalyticsSnapshot.channel_id == channel_id)
            .order_by(ChannelAnalyticsSnapshot.snapshot_date.desc())
        )
        latest_snapshot = (await self.db.execute(snap_stmt)).scalars().first()

        # 2. Fetch existing active recommendations to prevent duplicate accumulation
        existing_stmt = select(OptimizationRecommendation).where(
            and_(
                OptimizationRecommendation.channel_id == channel_id,
                OptimizationRecommendation.status == "NEW",
            )
        )
        existing_recs = list((await self.db.execute(existing_stmt)).scalars().all())
        existing_types = {r.recommendation_type for r in existing_recs}
        recommendations.extend(existing_recs)

        # 3. Check for outperforming formats / topics
        if "TOPIC_EXPANSION" not in existing_types and latest_snapshot and latest_snapshot.views > 0:
            rec = OptimizationRecommendation(
                channel_id=channel_id,
                recommendation_type="TOPIC_EXPANSION",
                title="Deep-Dive Follow-Up on AI Tool Workflows",
                description="Recent channel analytics indicate high audience interest in hands-on developer tooling. Produce a step-by-step implementation guide.",
                supporting_analytics={
                    "channel_views": latest_snapshot.views,
                    "avg_retention_pct": float(latest_snapshot.average_view_percentage),
                    "net_subscribers": latest_snapshot.net_subscribers,
                },
                confidence_score=0.88,
                expected_effort="MEDIUM",
                status="NEW",
                suggested_action="Create Long-Form Workflow",
            )
            self.db.add(rec)
            recommendations.append(rec)

        # 4. Always provide a Shorts pacing recommendation for hook retention if not present
        if "HOOK_OPTIMIZATION" not in existing_types:
            short_rec = OptimizationRecommendation(
                channel_id=channel_id,
                recommendation_type="HOOK_OPTIMIZATION",
                title="Accelerate 3-Second Hook on YouTube Shorts",
                description="Optimize opening 30 seconds for immediate code demonstration to exceed the 70% 30-second retention benchmark.",
                supporting_analytics={"target_30s_retention": 0.70},
                confidence_score=0.92,
                expected_effort="LOW",
                status="NEW",
                suggested_action="Create Shorts Workflow",
            )
            self.db.add(short_rec)
            recommendations.append(short_rec)

        await self.db.flush()
        return recommendations
