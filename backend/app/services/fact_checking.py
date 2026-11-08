"""Factual verification and claim-to-evidence cross-referencing engine."""

import re
from typing import List, Optional, Tuple
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.script import ScriptClaim
from app.models.topic import ResearchSource, Topic
from app.models.project import VideoProject
from app.schemas.script import ScriptClaimSchema


class FactCheckingService:
    """Verifies extracted script claims against authoritative research sources."""

    @staticmethod
    def _extract_keywords(text: str) -> set:
        """Tokenize text into significant lowercase words."""
        stop_words = {"the", "a", "an", "is", "in", "at", "to", "for", "with", "and", "or", "of", "on"}
        tokens = re.findall(r"\b[a-z0-9_]{3,}\b", text.lower())
        return {t for t in tokens if t not in stop_words}

    @classmethod
    def verify_claim_against_sources(
        cls,
        claim: ScriptClaimSchema,
        sources: List[ResearchSource],
    ) -> ScriptClaimSchema:
        """Match a claim against known research sources and calculate confidence."""
        claim_keywords = cls._extract_keywords(claim.claim_text)
        if not claim_keywords:
            claim.is_verified = False
            claim.confidence_score = 0.0
            claim.verification_explanation = "Claim contains insufficient distinct keywords to verify."
            return claim

        best_score = 0.0
        best_source: Optional[ResearchSource] = None

        for src in sources:
            source_text = f"{src.source_title or ''} {src.extracted_summary}".lower()
            source_keywords = cls._extract_keywords(source_text)

            intersection = claim_keywords.intersection(source_keywords)
            overlap_ratio = len(intersection) / float(len(claim_keywords))

            # Factor in the source's own relevance score
            relevance = float(src.relevance_score) if src.relevance_score is not None else 1.0
            composite_confidence = overlap_ratio * relevance

            if composite_confidence > best_score:
                best_score = composite_confidence
                best_source = src

        # Thresholds: >= 0.40 overlap with authoritative source counts as supported
        if best_score >= 0.40 and best_source is not None:
            claim.is_verified = True
            claim.confidence_score = round(min(0.99, 0.70 + (best_score * 0.30)), 3)
            claim.citation_url = best_source.source_url
            claim.citation_snippet = best_source.extracted_summary[:300]
            claim.verification_explanation = (
                f"Factual statement cross-referenced against authoritative source '{best_source.source_title}' "
                f"with {int(best_score * 100)}% keyword alignment."
            )
        else:
            claim.is_verified = False
            claim.confidence_score = round(max(0.10, best_score), 3)
            claim.citation_url = None
            claim.citation_snippet = None
            claim.verification_explanation = (
                "Unverified: No supporting documentation or benchmark was found in the research evidence."
            )

        return claim

    @classmethod
    async def verify_script_claims(
        cls,
        claims: List[ScriptClaimSchema],
        project_id: UUID,
        db: AsyncSession,
    ) -> List[ScriptClaimSchema]:
        """Fetch all research sources for the project's topic and verify claims."""
        # Find project and linked topic
        proj_stmt = select(VideoProject).where(VideoProject.id == project_id)
        proj_res = await db.execute(proj_stmt)
        project = proj_res.scalar_one_or_none()

        sources: List[ResearchSource] = []
        if project and project.topic_id:
            src_stmt = select(ResearchSource).where(ResearchSource.topic_id == project.topic_id)
            src_res = await db.execute(src_stmt)
            sources = list(src_res.scalars().all())

        verified_claims: List[ScriptClaimSchema] = []
        for claim in claims:
            verified = cls.verify_claim_against_sources(claim, sources)
            verified_claims.append(verified)

        logger.info(
            f"Fact check completed for project {project_id}: "
            f"{sum(1 for c in verified_claims if c.is_verified)}/{len(verified_claims)} verified."
        )
        return verified_claims
