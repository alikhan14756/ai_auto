"""Intelligent Topic Research and Synthesis Engine."""

import json
from typing import Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import logger
from app.models.channel import Channel, ChannelSettings
from app.models.topic import Topic, ResearchSource
from app.providers.ai.base import AIProviderInterface
from app.providers.ai.factory import get_ai_provider
from app.schemas.topic import TopicDiscoveryBatch, TopicCandidate
from app.services.topic_scoring import TopicScoringService
from app.services.usage import UsageTrackingService

TOPIC_DISCOVERY_SYSTEM_INSTRUCTION = """You are the Senior YouTube Technical Producer and Lead Researcher for an elite software engineering YouTube channel.
Your mission is to discover high-performing, authoritative video topics with strong technical depth, practical utility, and search curiosity.

Rules for generated topics:
1. Grounded in real modern engineering topics (e.g. AI systems, database engines, distributed queues, performance optimization, architectural failure modes).
2. Avoid vague clickbait like "Top 10 AI Tools". Use concrete problem-solution angles (e.g. "Why Postgres SKIP LOCKED Replaces Redis in 90% of Worker Architectures").
3. Include real, factual technical documentation or research references (e.g. official docs, research papers, high-profile engineering blogs).
4. Strictly return your response conforming to the JSON schema.
"""


class TopicResearchService:
    """Orchestrates topic ideation, AI inference, factual sourcing, and database persistence."""

    def __init__(self, provider: Optional[AIProviderInterface] = None):
        self._provider = provider or get_ai_provider()

    @property
    def provider(self) -> AIProviderInterface:
        return self._provider

    async def _load_channel_context(self, channel_id: UUID, db: AsyncSession) -> Dict[str, Any]:
        """Fetch channel metadata, niche keywords, and custom retention weights."""
        stmt = (
            select(Channel)
            .options(selectinload(Channel.settings))
            .where(Channel.id == channel_id)
        )
        res = await db.execute(stmt)
        channel = res.scalar_one_or_none()
        if not channel:
            raise ValueError(f"Channel with ID '{channel_id}' does not exist.")

        settings = channel.settings
        niche_keywords = settings.niche_keywords if (settings and settings.niche_keywords) else [
            "AI Engineering", "Distributed Systems", "PostgreSQL", "FastAPI", "Full-Stack Architecture"
        ]
        retention_weights = settings.topic_retention_weights if (settings and settings.topic_retention_weights) else None

        return {
            "channel_title": channel.title,
            "niche_keywords": niche_keywords,
            "weights": retention_weights,
        }

    async def _get_historical_titles(self, channel_id: UUID, db: AsyncSession) -> List[str]:
        """Fetch all existing topic titles for this channel to prevent duplicates."""
        stmt = select(Topic.title).where(Topic.channel_id == channel_id)
        res = await db.execute(stmt)
        return [row[0] for row in res.fetchall()]

    async def discover_and_persist_topics(
        self,
        channel_id: UUID,
        db: AsyncSession,
        niche_override: Optional[str] = None,
        count: int = 5,
    ) -> List[Topic]:
        """Execute the end-to-end topic research pipeline and store scored topics."""
        # 1. Budget Circuit Breaker Check
        await UsageTrackingService.check_budget_guardrail(channel_id, db)

        # 2. Load context and historical topics
        context = await self._load_channel_context(channel_id, db)
        historical_titles = await self._get_historical_titles(channel_id, db)

        niches = [niche_override] if niche_override else context["niche_keywords"]
        niche_str = ", ".join(niches) if isinstance(niches, list) else str(niches)

        prompt = (
            f"Generate {count} unique, high-opportunity YouTube video topic proposals for channel '{context['channel_title']}'.\n"
            f"Core technical domain and niche keywords: {niche_str}.\n\n"
            f"Existing historical video titles (DO NOT duplicate or closely rephrase any of these):\n"
            + "\n".join(f"- {t}" for t in historical_titles[:15])
            + f"\n\nEach proposal must contain:\n"
            f"- A high-CTR, curiosity-driven technical title\n"
            f"- Specific niche category\n"
            f"- Unique narrative angle and problem-solution hook\n"
            f"- Precise target developer audience\n"
            f"- Estimated audience relevance, practical value, originality, search volume score, and competition score (0-100)\n"
            f"- Compelling technical rationale\n"
            f"- 1 to 3 authoritative reference sources with URLs, titles, and extracted summaries.\n"
        )

        logger.info(f"Triggering AI topic discovery for channel {channel_id} with provider {self.provider.name}")

        # 3. Invoke structured AI generation
        structured_resp = await self.provider.generate_structured(
            prompt=prompt,
            response_schema=TopicDiscoveryBatch,
            system_instruction=TOPIC_DISCOVERY_SYSTEM_INSTRUCTION,
            temperature=0.3,
        )

        # 4. Record token usage ledger
        await UsageTrackingService.record_usage(
            channel_id=channel_id,
            provider_name=self.provider.name,
            model_name=structured_resp.model_name,
            input_tokens=structured_resp.usage.prompt_tokens,
            output_tokens=structured_resp.usage.completion_tokens,
            cost_usd=structured_resp.usage.estimated_cost_usd,
            db=db,
        )

        batch: TopicDiscoveryBatch = structured_resp.parsed
        saved_topics: List[Topic] = []

        # 5. Process, score, deduplicate, and persist topics
        for candidate in batch.topics[:count]:
            sim_ratio, similar_title = TopicScoringService.find_max_historical_similarity(
                candidate.title, historical_titles
            )

            # Skip candidate if too similar to an existing title (>0.80)
            if sim_ratio >= 0.80:
                logger.warning(
                    f"Discarding duplicate topic '{candidate.title}' (similarity {sim_ratio} with '{similar_title}')"
                )
                continue

            # Deterministic weighted score
            opp_score = TopicScoringService.calculate_opportunity_score(
                audience_relevance=candidate.audience_relevance,
                practical_value=candidate.practical_value,
                originality=candidate.originality,
                search_volume_score=candidate.search_volume_score,
                competition_score=candidate.competition_score,
                custom_weights=context["weights"],
            )

            # Deduct penalty if moderately similar (0.50 - 0.79)
            if sim_ratio >= 0.50:
                opp_score = round(max(10.0, opp_score - 15.0), 2)

            raw_payload = {
                "angle": candidate.angle,
                "target_audience": candidate.target_audience,
                "rationale": candidate.rationale,
                "similarity_to_history": sim_ratio,
                "most_similar_existing_title": similar_title if sim_ratio > 0.3 else None,
                "component_scores": {
                    "audience_relevance": candidate.audience_relevance,
                    "practical_value": candidate.practical_value,
                    "originality": candidate.originality,
                    "search_volume_score": candidate.search_volume_score,
                    "competition_score": candidate.competition_score,
                },
            }

            topic_model = Topic(
                channel_id=channel_id,
                title=candidate.title,
                niche_category=candidate.niche_category,
                opportunity_score=opp_score,
                search_volume_score=candidate.search_volume_score,
                competition_score=candidate.competition_score,
                status="DISCOVERED",
                raw_discovery_payload=raw_payload,
            )
            db.add(topic_model)
            await db.flush()  # populate topic_model.id

            # Save research sources
            for src in candidate.sources:
                source_record = ResearchSource(
                    topic_id=topic_model.id,
                    source_url=src.source_url,
                    source_title=src.source_title,
                    extracted_summary=src.extracted_summary,
                    relevance_score=src.relevance_score,
                )
                db.add(source_record)

            saved_topics.append(topic_model)
            historical_titles.append(candidate.title)

        await db.commit()

        # Reload with sources eager loaded
        topic_ids = [t.id for t in saved_topics]
        if topic_ids:
            stmt = (
                select(Topic)
                .options(selectinload(Topic.research_sources))
                .where(Topic.id.in_(topic_ids))
                .order_by(Topic.opportunity_score.desc())
            )
            res = await db.execute(stmt)
            return list(res.scalars().all())

        return []
