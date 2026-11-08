"""Algorithmic feedback loop connecting YouTube analytics retention to future topic opportunity scoring."""

import datetime
from typing import Dict, Any, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.channel import Channel, ChannelSettings
from app.models.analytics import VideoAnalyticsSnapshot, PerformanceRecommendation
from app.models.publishing import YouTubeVideo, PublishingJob
from app.models.project import VideoProject
from app.services.youtube.constants import (
    REC_STATUS_ACCEPTED,
    REC_STATUS_REJECTED,
    REC_STATUS_COMPLETED,
)


class TopicRetentionFeedbackLoop:
    """Computes retention ratios per topic category and updates ChannelSettings.topic_retention_weights."""

    MIN_MULTIPLIER = 0.70
    MAX_MULTIPLIER = 1.30

    @classmethod
    async def rebalance_topic_weights(
        cls,
        db: AsyncSession,
        channel_id: UUID,
    ) -> Dict[str, float]:
        """Analyze video retention by topic category and compute updated weights."""
        # 1. Fetch channel settings
        stmt = select(ChannelSettings).where(ChannelSettings.channel_id == channel_id)
        res = await db.execute(stmt)
        settings = res.scalar_one_or_none()

        if not settings:
            logger.warning(f"[FeedbackLoop] ChannelSettings not found for channel {channel_id}")
            return {}

        current_weights = dict(settings.topic_retention_weights or {})

        # 2. Fetch video snapshots for channel
        v_stmt = select(VideoAnalyticsSnapshot).where(VideoAnalyticsSnapshot.channel_id == channel_id)
        v_res = await db.execute(v_stmt)
        snaps = v_res.scalars().all()

        if not snaps:
            # Return baseline niche weights
            default_weights = {
                "AI Tools": 1.15,
                "Developer Productivity": 1.10,
                "Practical Web Technology & Coding": 1.05,
            }
            settings.topic_retention_weights = default_weights
            await db.commit()
            return default_weights

        # 3. Compute overall median retention
        retentions = [float(s.retention_at_30s) for s in snaps if s.retention_at_30s]
        overall_median = (sum(retentions) / len(retentions)) if retentions else 0.70

        # 4. Build title lookup from PublishingJob & VideoProject for authoritative category matching
        v_title_map: Dict[str, str] = {}
        try:
            pub_stmt = (
                select(YouTubeVideo.youtube_video_id, PublishingJob.title, VideoProject.title)
                .join(PublishingJob, YouTubeVideo.publishing_job_id == PublishingJob.id)
                .outerjoin(VideoProject, PublishingJob.project_id == VideoProject.id)
                .where(PublishingJob.channel_id == channel_id)
            )
            p_res = await db.execute(pub_stmt)
            for row in p_res.all():
                y_id, p_title, proj_title = row
                v_title_map[str(y_id)] = f"{p_title or ''} {proj_title or ''}".lower()
        except Exception as e:
            logger.debug(f"[FeedbackLoop] Could not build title map from DB projects: {e}")

        # Default target niches for Creator Studio AI
        niche_categories = [
            "AI Tools",
            "Developer Productivity",
            "Practical Web Technology & Coding",
        ]

        updated_weights = {}
        for cat in niche_categories:
            # Match keywords against YouTube ID, Publishing title, Project title, or raw snippet
            cat_keywords = [w.lower() for w in cat.split() if len(w) > 2 and w.lower() not in ("and", "&")]
            cat_snaps = [
                s for s in snaps
                if any(
                    kw in s.youtube_video_id.lower()
                    or kw in v_title_map.get(s.youtube_video_id, "")
                    or (isinstance(s.raw_metrics, dict) and kw in str(s.raw_metrics.get("title", "")).lower())
                    for kw in cat_keywords
                )
            ]

            if cat_snaps:
                cat_ret = [float(s.retention_at_30s) for s in cat_snaps if s.retention_at_30s]
                avg_ret = (sum(cat_ret) / len(cat_ret)) if cat_ret else overall_median
                raw_ratio = avg_ret / max(0.01, overall_median)
            else:
                raw_ratio = 1.05  # Default encouraging multiplier for planned core niche

            clamped_weight = round(max(cls.MIN_MULTIPLIER, min(cls.MAX_MULTIPLIER, raw_ratio)), 3)
            updated_weights[cat] = clamped_weight

        # 5. Persist updated weights
        settings.topic_retention_weights = updated_weights
        await db.commit()
        logger.info(f"[FeedbackLoop] Updated topic retention weights for channel {channel_id}: {updated_weights}")
        return updated_weights

    @classmethod
    async def accept_recommendation(
        cls,
        db: AsyncSession,
        recommendation_id: UUID,
    ) -> PerformanceRecommendation:
        """Mark recommendation as accepted and trigger weight rebalancing if applicable."""
        stmt = select(PerformanceRecommendation).where(PerformanceRecommendation.id == recommendation_id)
        res = await db.execute(stmt)
        rec = res.scalar_one_or_none()

        if not rec:
            raise ValueError(f"Recommendation {recommendation_id} not found")

        rec.status = REC_STATUS_ACCEPTED
        rec.applied_at = datetime.datetime.now(datetime.timezone.utc)

        # If it's a topic opportunity, boost topic weights
        if rec.recommendation_type == "TOPIC_OPPORTUNITY":
            await cls.rebalance_topic_weights(db, rec.channel_id)

        await db.commit()
        return rec

    @classmethod
    async def reject_recommendation(
        cls,
        db: AsyncSession,
        recommendation_id: UUID,
    ) -> PerformanceRecommendation:
        """Mark recommendation as rejected."""
        stmt = select(PerformanceRecommendation).where(PerformanceRecommendation.id == recommendation_id)
        res = await db.execute(stmt)
        rec = res.scalar_one_or_none()

        if not rec:
            raise ValueError(f"Recommendation {recommendation_id} not found")

        rec.status = REC_STATUS_REJECTED
        await db.commit()
        return rec

    @classmethod
    async def complete_recommendation(
        cls,
        db: AsyncSession,
        recommendation_id: UUID,
    ) -> PerformanceRecommendation:
        """Mark recommendation as completed."""
        stmt = select(PerformanceRecommendation).where(PerformanceRecommendation.id == recommendation_id)
        res = await db.execute(stmt)
        rec = res.scalar_one_or_none()

        if not rec:
            raise ValueError(f"Recommendation {recommendation_id} not found")

        rec.status = REC_STATUS_COMPLETED
        await db.commit()
        return rec
