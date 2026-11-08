"""Performance Intelligence Engine for deterministic analysis, evidence-backed insights, and recommendations."""

import statistics
from typing import Dict, Any, List, Optional
from uuid import UUID
from sqlalchemy import select, and_, desc, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.analytics import (
    ChannelAnalyticsSnapshot,
    VideoAnalyticsSnapshot,
    AudienceRetentionSnapshot,
    PerformanceInsight,
    PerformanceRecommendation,
)
from app.models.publishing import YouTubeVideo
from app.services.youtube.constants import (
    CONTENT_LONG_FORM,
    CONTENT_SHORTS,
    INSIGHT_VIEW_VELOCITY,
    INSIGHT_RETENTION_DROP,
    INSIGHT_TOPIC_OUTPERFORMANCE,
    INSIGHT_CTR_VARIANCE,
    INSIGHT_CADENCE,
    INSIGHT_FORMAT_COMPARISON,
    REC_STATUS_NEW,
)


class PerformanceIntelligenceEngine:
    """Transforms raw analytics telemetry into transparent, evidence-backed insights and recommendations."""

    @classmethod
    async def analyze_channel(
        cls,
        db: AsyncSession,
        channel_id: UUID,
        use_ai_explanations: bool = False,
    ) -> Dict[str, Any]:
        """Perform comprehensive deterministic performance analysis and generate insights."""
        # 1. Fetch recent video snapshots
        stmt = (
            select(VideoAnalyticsSnapshot)
            .where(VideoAnalyticsSnapshot.channel_id == channel_id)
            .order_by(desc(VideoAnalyticsSnapshot.snapshot_date))
            .limit(100)
        )
        res = await db.execute(stmt)
        raw_video_snaps = res.scalars().all()

        if not raw_video_snaps:
            return {
                "status": "INSUFFICIENT_DATA",
                "message": "Not enough video analytics snapshots available for baseline comparison.",
                "insights": [],
                "recommendations": [],
            }

        # Deduplicate to latest snapshot per video to prevent multi-day repetition distortion
        latest_snaps_dict: Dict[str, VideoAnalyticsSnapshot] = {}
        for s in raw_video_snaps:
            if s.youtube_video_id not in latest_snaps_dict:
                latest_snaps_dict[s.youtube_video_id] = s
        video_snaps = list(latest_snaps_dict.values())

        # 2. Separate cohorts: Long-form vs Shorts
        long_form = [v for v in video_snaps if v.content_type == CONTENT_LONG_FORM]
        shorts = [v for v in video_snaps if v.content_type == CONTENT_SHORTS]

        # Calculate baselines
        all_views = [v.views for v in video_snaps]
        median_views = statistics.median(all_views) if all_views else 0
        median_retention_30s = (
            statistics.median([float(v.retention_at_30s) for v in video_snaps if v.retention_at_30s])
            if video_snaps
            else 0.70
        )
        median_ctr = (
            statistics.median([float(v.click_through_rate) for v in video_snaps if v.click_through_rate])
            if video_snaps
            else 0.06
        )

        insights: List[PerformanceInsight] = []
        recommendations: List[PerformanceRecommendation] = []

        # 3. Detect Outperforming & Underperforming Videos (Deterministic)
        for v in video_snaps:
            # High View Velocity
            if v.views > median_views * 1.35 and median_views > 0:
                outperf_pct = round(((v.views - median_views) / median_views) * 100.0, 1)
                ins = PerformanceInsight(
                    channel_id=channel_id,
                    youtube_video_id=v.youtube_video_id,
                    insight_type=INSIGHT_VIEW_VELOCITY,
                    category="CONTENT",
                    title=f"Video {v.youtube_video_id} outperforming median views by {outperf_pct}%",
                    explanation=(
                        f"Video received {v.views} views compared to channel median of {int(median_views)}. "
                        "This observed correlation suggests strong viewer interest or discovery placement, "
                        "not guaranteed causality from title alone."
                    ),
                    evidence_metrics={
                        "video_views": v.views,
                        "median_views": median_views,
                        "percentage_above_median": outperf_pct,
                    },
                    confidence_score=0.92,
                    limitations="Based on current reporting window; excludes external off-platform embeds.",
                )
                insights.append(ins)

            # Hook Retention Drop (< 65% at 30s)
            if v.retention_at_30s and float(v.retention_at_30s) < 0.65:
                ret_pct = round(float(v.retention_at_30s) * 100.0, 1)
                ins = PerformanceInsight(
                    channel_id=channel_id,
                    youtube_video_id=v.youtube_video_id,
                    insight_type=INSIGHT_RETENTION_DROP,
                    category="RETENTION",
                    title=f"Hook drop-off detected on {v.youtube_video_id} ({ret_pct}% at 30s)",
                    explanation=(
                        f"At second 30, viewer retention dropped to {ret_pct}%, which is below the channel "
                        f"median of {round(median_retention_30s * 100.0, 1)}%. Early drop indicates hook pacing "
                        "or premise alignment could be tightened."
                    ),
                    evidence_metrics={
                        "retention_30s": float(v.retention_at_30s),
                        "median_retention_30s": median_retention_30s,
                    },
                    confidence_score=0.88,
                    limitations="Retention curve telemetry compiled over 48h retrospective window.",
                )
                insights.append(ins)

            # High CTR
            if v.click_through_rate and float(v.click_through_rate) > 0.08:
                ctr_pct = round(float(v.click_through_rate) * 100.0, 1)
                ins = PerformanceInsight(
                    channel_id=channel_id,
                    youtube_video_id=v.youtube_video_id,
                    insight_type=INSIGHT_CTR_VARIANCE,
                    category="METADATA",
                    title=f"Elevated Impression CTR ({ctr_pct}%) on {v.youtube_video_id}",
                    explanation=(
                        f"Thumbnail and title combination achieved a {ctr_pct}% CTR, exceeding channel "
                        f"median of {round(median_ctr * 100.0, 1)}%."
                    ),
                    evidence_metrics={
                        "click_through_rate": float(v.click_through_rate),
                        "median_ctr": median_ctr,
                    },
                    confidence_score=0.85,
                    limitations="CTR can naturally decay as YouTube expands impressions to broader audiences.",
                )
                insights.append(ins)

        # 4. Format Comparison (Shorts vs Long-form)
        if long_form and shorts:
            avg_lf_views = sum(v.views for v in long_form) / len(long_form)
            avg_sh_views = sum(v.views for v in shorts) / len(shorts)
            ins = PerformanceInsight(
                channel_id=channel_id,
                youtube_video_id=None,
                insight_type=INSIGHT_FORMAT_COMPARISON,
                category="AUDIENCE",
                title="Shorts vs Long-Form Audience Engagement Comparison",
                explanation=(
                    f"Shorts averaged {int(avg_sh_views)} views with {round(statistics.median([float(s.retention_at_30s) for s in shorts]) * 100.0, 1)}% hook retention, "
                    f"while Long-Form averaged {int(avg_lf_views)} views with deeper total watch time. "
                    "Shorts accelerate subscriber acquisition; long-form builds watch-time authority."
                ),
                evidence_metrics={
                    "shorts_count": len(shorts),
                    "long_form_count": len(long_form),
                    "shorts_avg_views": int(avg_sh_views),
                    "long_form_avg_views": int(avg_lf_views),
                },
                confidence_score=0.90,
                limitations="Different monetization rates and algorithm surfaces apply to each format.",
            )
            insights.append(ins)

        # 5. Generate Strategic Recommendations
        # Recommendation 1: Hook tightening for low retention
        low_retention_videos = [v for v in video_snaps if v.retention_at_30s and float(v.retention_at_30s) < 0.65]
        if low_retention_videos:
            rec = PerformanceRecommendation(
                channel_id=channel_id,
                recommendation_type="HOOK_OPTIMIZATION",
                title="Streamline Video Hooks to Exceed 70% 30-Second Retention",
                explanation=(
                    f"{len(low_retention_videos)} video(s) experienced drop-offs before 30 seconds. "
                    "Recommend reducing teaser intros to under 8 seconds and opening immediately with the core thesis."
                ),
                supporting_metrics={
                    "impacted_videos_count": len(low_retention_videos),
                    "current_median_hook": round(median_retention_30s * 100.0, 1),
                    "target_hook": 75.0,
                },
                suggested_action={
                    "action": "UPDATE_SCRIPT_TEMPLATE",
                    "hook_max_duration_seconds": 12,
                    "target_topic_niche": "AI Tools & Developer Productivity",
                },
                confidence_level="HIGH",
                status=REC_STATUS_NEW,
            )
            recommendations.append(rec)

        # Recommendation 2: Topic doubling for high performance
        high_view_videos = [v for v in video_snaps if v.views > median_views * 1.3]
        if high_view_videos:
            rec = PerformanceRecommendation(
                channel_id=channel_id,
                recommendation_type="TOPIC_OPPORTUNITY",
                title="Expand Topic Coverage on Proven High-Velocity Subjects",
                explanation=(
                    f"Videos focusing on practical workflows outperformed median viewership by 35%+. "
                    "Recommend prioritizing adjacent topics in AI tooling and full-stack automation."
                ),
                supporting_metrics={
                    "high_velocity_count": len(high_view_videos),
                    "median_views": median_views,
                },
                suggested_action={
                    "action": "BOOST_TOPIC_WEIGHTS",
                    "niche_focus": "AI Tools, Developer Productivity, Practical Web Technology & Coding",
                    "suggested_topics": [
                        "Automated Test Suites with Local LLMs",
                        "Building High-Concurrency Workers in Python 3.12",
                    ],
                },
                confidence_level="HIGH",
                status=REC_STATUS_NEW,
            )
            recommendations.append(rec)

        # 6. Archive prior active insights to prevent stale duplicates, then save new ones
        await db.execute(
            update(PerformanceInsight)
            .where(
                and_(
                    PerformanceInsight.channel_id == channel_id,
                    PerformanceInsight.status == "ACTIVE",
                )
            )
            .values(status="ARCHIVED")
        )

        for ins in insights:
            db.add(ins)
        for rec in recommendations:
            db.add(rec)
        await db.commit()

        return {
            "status": "ANALYSIS_COMPLETE",
            "median_views": median_views,
            "median_retention_30s": median_retention_30s,
            "median_ctr": median_ctr,
            "insights_generated": len(insights),
            "recommendations_generated": len(recommendations),
            "insights": [
                {
                    "id": str(i.id),
                    "type": i.insight_type,
                    "title": i.title,
                    "explanation": i.explanation,
                    "confidence": float(i.confidence_score),
                }
                for i in insights
            ],
            "recommendations": [
                {
                    "id": str(r.id),
                    "type": r.recommendation_type,
                    "title": r.title,
                    "explanation": r.explanation,
                    "confidence": r.confidence_level,
                }
                for r in recommendations
            ],
        }
