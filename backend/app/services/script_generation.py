"""Procedural Video Script Generation and Section Revision Service."""

from typing import Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import logger
from app.models.channel import Channel
from app.models.project import VideoProject
from app.models.scene import Scene
from app.models.script import Script, ScriptClaim
from app.models.topic import ResearchSource, Topic
from app.providers.ai.base import AIProviderInterface
from app.providers.ai.factory import get_ai_provider
from app.schemas.script import (
    GeneratedScriptSchema,
    ScriptOutlineResponse,
    ScriptQualityMetrics,
    ScriptSectionSchema,
)
from app.services.fact_checking import FactCheckingService
from app.services.script_evaluation import ScriptEvaluationService
from app.services.usage import UsageTrackingService

SCRIPT_SYSTEM_INSTRUCTION = """You are the Lead Scriptwriter for an elite, high-authority YouTube tech channel.
Your goal is to produce engaging, highly structured video scripts tailored for software engineers, architects, and technical decision-makers.

Rules:
1. Speak directly to the viewer in natural spoken English with clarity and technical precision.
2. Hook the viewer in the first 5 seconds with a surprising technical fact, problem, or common architectural trap.
3. Every factual claim (e.g. release dates, version numbers, throughput benchmarks, pricing) must be concrete and verifiable.
4. Output must conform strictly to the JSON schema.
"""


class ScriptGenerationService:
    """Orchestrates structured script generation, fact verification, and scene compilation."""

    def __init__(self, provider: Optional[AIProviderInterface] = None):
        self._provider = provider or get_ai_provider()

    @property
    def provider(self) -> AIProviderInterface:
        return self._provider

    async def _load_project_context(self, project_id: UUID, db: AsyncSession) -> Dict[str, Any]:
        """Load project, channel, and topic with research sources."""
        stmt = (
            select(VideoProject)
            .options(
                selectinload(VideoProject.channel),
                selectinload(VideoProject.topic).selectinload(Topic.research_sources),
            )
            .where(VideoProject.id == project_id)
        )
        res = await db.execute(stmt)
        project = res.scalar_one_or_none()
        if not project:
            raise ValueError(f"Project with ID '{project_id}' not found.")

        topic = project.topic
        sources = topic.research_sources if (topic and topic.research_sources) else []

        return {
            "project": project,
            "channel": project.channel,
            "topic": topic,
            "sources": sources,
        }

    async def generate_and_persist_script(
        self,
        project_id: UUID,
        db: AsyncSession,
        target_duration_seconds: Optional[int] = None,
        tone: str = "authoritative",
        custom_instructions: Optional[str] = None,
    ) -> Script:
        """Execute full scriptwriting pipeline, factual check, and database storage."""
        ctx = await self._load_project_context(project_id, db)
        project: VideoProject = ctx["project"]
        channel: Channel = ctx["channel"]
        topic: Optional[Topic] = ctx["topic"]
        sources: List[ResearchSource] = ctx["sources"]

        # 1. Enforce Budget Guardrail
        await UsageTrackingService.check_budget_guardrail(channel.id, db)

        duration = target_duration_seconds or project.target_duration_seconds or 480
        is_shorts = (project.format == "SHORTS") or (duration <= 60)

        # 2. Build synthesis prompt
        sources_summary = "\n".join(
            f"- {s.source_title}: {s.extracted_summary} (URL: {s.source_url})"
            for s in sources[:5]
        ) or "No pre-compiled research sources available."

        topic_title = topic.title if topic else project.title
        prompt = (
            f"Write a complete, high-retention video script for YouTube.\n"
            f"Format: {'YouTube Shorts (30-60s)' if is_shorts else 'Long-form Technical Video (6-10 min)'}\n"
            f"Topic: '{topic_title}'\n"
            f"Channel: '{channel.title}'\n"
            f"Target Duration: {duration} seconds\n"
            f"Tone: {tone}\n"
            f"Custom Instructions: {custom_instructions or 'Focus on pragmatic code patterns and architectural trade-offs.'}\n\n"
            f"Authoritative Research Evidence to Back Your Claims:\n{sources_summary}\n\n"
            f"Include:\n"
            f"1. Compelling opening hook.\n"
            f"2. {'1-2 rapid demo scenes' if is_shorts else '3-5 logically sequenced technical sections with clear visual directions'}.\n"
            f"3. Concrete factual claims extracted with confidence scores.\n"
            f"4. Powerful conclusion and call to action.\n"
        )

        logger.info(f"Synthesizing script for project {project_id} using provider {self.provider.name}")

        # 3. Structured Generation via AI Provider
        structured_resp = await self.provider.generate_structured(
            prompt=prompt,
            response_schema=GeneratedScriptSchema,
            system_instruction=SCRIPT_SYSTEM_INSTRUCTION,
            temperature=0.4,
        )

        # 4. Record Token Consumption
        await UsageTrackingService.record_usage(
            channel_id=channel.id,
            provider_name=self.provider.name,
            model_name=structured_resp.model_name,
            input_tokens=structured_resp.usage.prompt_tokens,
            output_tokens=structured_resp.usage.completion_tokens,
            cost_usd=structured_resp.usage.estimated_cost_usd,
            db=db,
        )

        generated: GeneratedScriptSchema = structured_resp.parsed

        # 5. Run Fact Verification
        verified_claims = await FactCheckingService.verify_script_claims(
            claims=generated.claims,
            project_id=project_id,
            db=db,
        )

        # 6. Evaluate Quality & Repetition
        metrics = ScriptEvaluationService.evaluate_script(
            full_text=generated.full_text,
            hook_text=generated.hook,
            total_claims=len(verified_claims),
            verified_claims=sum(1 for c in verified_claims if c.is_verified),
            unverified_claims=sum(1 for c in verified_claims if not c.is_verified),
        )

        # 7. Persist Script Record
        # Check existing version
        existing_stmt = select(Script).where(Script.project_id == project_id).order_by(Script.version.desc())
        existing_res = await db.execute(existing_stmt)
        latest_existing = existing_res.scalars().first()
        next_version = (latest_existing.version + 1) if latest_existing else 1

        script_record = Script(
            project_id=project_id,
            version=next_version,
            full_text=generated.full_text,
            word_count=metrics.word_count,
            estimated_duration_seconds=metrics.estimated_duration_seconds,
            is_locked=False,
        )
        db.add(script_record)
        await db.flush()

        # 8. Persist Script Claims
        for c in verified_claims:
            claim_row = ScriptClaim(
                script_id=script_record.id,
                project_id=project_id,
                claim_text=c.claim_text,
                extracted_entity=c.extracted_entity,
                claim_type=c.claim_type,
                is_verified=c.is_verified,
                confidence_score=c.confidence_score,
                citation_url=c.citation_url,
                citation_snippet=c.citation_snippet,
            )
            db.add(claim_row)

        # 9. Sync Storyboard Scenes for downstream M07/M08
        # Clear old scenes if version 1 or regenerate
        for idx, sec in enumerate(generated.sections, start=1):
            scene_row = Scene(
                project_id=project_id,
                scene_order=idx,
                narration_text=sec.narration,
                visual_archetype="BROWSER_CAPTURE" if "capture" in sec.visual_directive.lower() else "INFOGRAPHIC",
                visual_directive=sec.visual_directive,
                duration_seconds=sec.estimated_seconds,
            )
            db.add(scene_row)

        # Update VideoProject State
        project.state = "SCRIPT_DRAFTED"
        await db.commit()

        # Reload with claims eagerly loaded
        reload_stmt = (
            select(Script)
            .options(selectinload(Script.claims))
            .where(Script.id == script_record.id)
        )
        reload_res = await db.execute(reload_stmt)
        return reload_res.scalar_one()

    async def regenerate_section(
        self,
        script_id: UUID,
        section_id: str,
        custom_prompt: Optional[str],
        db: AsyncSession,
    ) -> Script:
        """Regenerate a single section while preserving the surrounding script context."""
        stmt = (
            select(Script)
            .options(selectinload(Script.project).selectinload(VideoProject.channel))
            .where(Script.id == script_id)
        )
        res = await db.execute(stmt)
        script = res.scalar_one_or_none()
        if not script:
            raise ValueError(f"Script with ID '{script_id}' not found.")

        prompt = (
            f"Regenerate narrative section '{section_id}' for technical video:\n"
            f"Instruction: {custom_prompt or 'Make this section more concise with a practical code example.'}\n"
            f"Current script context:\n{script.full_text[:500]}..."
        )

        resp = await self.provider.generate_text(prompt=prompt, max_tokens=500)
        # Append / update revision notes
        script.full_text = f"{script.full_text}\n\n[Revised Section {section_id}]: {resp.text}"
        script.word_count = ScriptEvaluationService.calculate_word_count(script.full_text)
        script.estimated_duration_seconds = ScriptEvaluationService.estimate_duration_seconds(script.word_count)

        await db.commit()
        await db.refresh(script)
        return script

    async def generate_outline(
        self,
        project_id: UUID,
        db: AsyncSession,
        target_duration_seconds: Optional[int] = None,
        tone: str = "authoritative",
        custom_instructions: Optional[str] = None,
    ) -> ScriptOutlineResponse:
        """Produce an early structured script outline prior to drafting full narrative."""
        ctx = await self._load_project_context(project_id, db)
        project: VideoProject = ctx["project"]
        channel: Channel = ctx["channel"]
        topic: Optional[Topic] = ctx["topic"]
        sources: List[ResearchSource] = ctx["sources"]

        await UsageTrackingService.check_budget_guardrail(channel.id, db)

        duration = target_duration_seconds or project.target_duration_seconds or 480
        is_shorts = (project.format == "SHORTS") or (duration <= 60)

        sources_summary = "\n".join(
            f"- {s.source_title}: {s.extracted_summary}"
            for s in sources[:5]
        ) or "No pre-compiled research sources available."

        topic_title = topic.title if topic else project.title
        prompt = (
            f"Generate a detailed video outline and scene progression blueprint.\n"
            f"Format: {'YouTube Shorts (30-60s)' if is_shorts else 'Long-form Technical Video (6-10 min)'}\n"
            f"Topic: '{topic_title}'\n"
            f"Channel: '{channel.title}'\n"
            f"Target Duration: {duration} seconds\n"
            f"Tone: {tone}\n"
            f"Custom Instructions: {custom_instructions or 'Focus on pragmatic code patterns and architectural trade-offs.'}\n\n"
            f"Research Evidence:\n{sources_summary}\n\n"
            f"Produce structured sections with key technical points and visual concepts."
        )

        resp = await self.provider.generate_structured(
            prompt=prompt,
            response_schema=ScriptOutlineResponse,
            system_instruction=SCRIPT_SYSTEM_INSTRUCTION,
            temperature=0.3,
        )

        await UsageTrackingService.record_usage(
            channel_id=channel.id,
            provider_name=self.provider.name,
            model_name=resp.model_name,
            input_tokens=resp.usage.prompt_tokens,
            output_tokens=resp.usage.completion_tokens,
            cost_usd=resp.usage.estimated_cost_usd,
            db=db,
        )

        outline: ScriptOutlineResponse = resp.parsed
        outline.project_id = project_id
        outline.target_duration_seconds = duration
        outline.format = "SHORTS" if is_shorts else "LONG_FORM"
        return outline
