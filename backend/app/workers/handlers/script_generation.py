"""Background worker handler for GENERATE_SCRIPT jobs."""

from typing import Any, Dict
from uuid import UUID

from app.core.logging import logger
from app.db.session import AsyncSessionLocal
from app.models.job import AutomationJob
from app.providers.ai.factory import get_ai_provider
from app.services.script_generation import ScriptGenerationService
from app.workers.handlers.base import (
    BaseJobHandler,
    CancellationChecker,
    HardFailureException,
    JobCancelledException,
    ProgressCallback,
)


class ScriptGenerationJobHandler(BaseJobHandler):
    """Processes asynchronous video scriptwriting and fact-checking jobs in the worker queue."""

    def __init__(self, session_factory=None):
        self._session_factory = session_factory or AsyncSessionLocal

    async def validate(self, payload: Dict[str, Any]) -> None:
        """Validate input payload before job execution."""
        if not payload or not isinstance(payload, dict):
            raise HardFailureException("Payload must be a non-empty JSON object.")

        project_id_raw = payload.get("project_id")
        if not project_id_raw:
            raise HardFailureException("Missing required parameter: 'project_id'.")

        try:
            UUID(str(project_id_raw))
        except (ValueError, TypeError):
            raise HardFailureException(f"Invalid UUID format for 'project_id': {project_id_raw}")

    async def execute(
        self,
        job: AutomationJob,
        update_progress: ProgressCallback,
        is_cancelled: CancellationChecker,
    ) -> Dict[str, Any]:
        """Execute complete script generation pipeline with stage progress reporting."""
        payload = job.payload or {}
        project_id = UUID(str(payload["project_id"]))
        duration = payload.get("target_duration_seconds")
        tone = payload.get("tone", "authoritative")
        custom_instructions = payload.get("custom_instructions")

        logger.info(f"Executing GENERATE_SCRIPT for job {job.id}, project {project_id}")

        # Stage 1: Initializing
        await update_progress(10, "INITIALIZING_GENERATION")
        if await is_cancelled():
            raise JobCancelledException("Script generation cancelled by user.")

        # Stage 2: Loading Context & Evidence
        await update_progress(30, "LOADING_TOPIC_EVIDENCE")
        if await is_cancelled():
            raise JobCancelledException("Script generation cancelled by user.")

        # Stage 3: Synthesizing Script
        await update_progress(60, "SYNTHESIZING_SCRIPT")
        if await is_cancelled():
            raise JobCancelledException("Script generation cancelled by user.")

        service = ScriptGenerationService(provider=get_ai_provider())
        async with (self._session_factory)() as session:
            script = await service.generate_and_persist_script(
                project_id=project_id,
                db=session,
                target_duration_seconds=duration,
                tone=tone,
                custom_instructions=custom_instructions,
            )

        # Stage 4: Fact-Checking Claims
        await update_progress(80, "EXTRACTING_AND_CHECKING_CLAIMS")
        if await is_cancelled():
            raise JobCancelledException("Script generation cancelled by user.")

        # Stage 5: Evaluating Originality & Quality
        await update_progress(95, "EVALUATING_ORIGINALITY_AND_QUALITY")
        if await is_cancelled():
            raise JobCancelledException("Script generation cancelled by user.")

        # Stage 6: Finalizing
        await update_progress(100, "COMPLETED")

        return {
            "script_id": str(script.id),
            "project_id": str(project_id),
            "version": script.version,
            "word_count": script.word_count,
            "estimated_duration_seconds": script.estimated_duration_seconds,
            "claims_count": len(script.claims),
        }


class ScriptOutlineJobHandler(BaseJobHandler):
    """Processes asynchronous script outline generation."""

    def __init__(self, session_factory=None):
        self._session_factory = session_factory or AsyncSessionLocal

    async def validate(self, payload: Dict[str, Any]) -> None:
        if not payload or not isinstance(payload, dict):
            raise HardFailureException("Payload must be a non-empty JSON object.")
        project_id_raw = payload.get("project_id")
        if not project_id_raw:
            raise HardFailureException("Missing required parameter: 'project_id'.")
        try:
            UUID(str(project_id_raw))
        except (ValueError, TypeError):
            raise HardFailureException(f"Invalid UUID format for 'project_id': {project_id_raw}")

    async def execute(
        self,
        job: AutomationJob,
        update_progress: ProgressCallback,
        is_cancelled: CancellationChecker,
    ) -> Dict[str, Any]:
        payload = job.payload or {}
        project_id = UUID(str(payload["project_id"]))
        duration = payload.get("target_duration_seconds")
        tone = payload.get("tone", "authoritative")
        custom_instructions = payload.get("custom_instructions")

        await update_progress(20, "INITIALIZING_OUTLINE")
        if await is_cancelled():
            raise JobCancelledException("Job cancelled by user.")

        await update_progress(60, "GENERATING_OUTLINE_BLUEPRINT")
        if await is_cancelled():
            raise JobCancelledException("Job cancelled by user.")

        service = ScriptGenerationService(provider=get_ai_provider())
        async with (self._session_factory)() as session:
            outline = await service.generate_outline(
                project_id=project_id,
                db=session,
                target_duration_seconds=duration,
                tone=tone,
                custom_instructions=custom_instructions,
            )

        await update_progress(100, "COMPLETED")
        return outline.model_dump(mode="json")


class ScriptFactCheckJobHandler(BaseJobHandler):
    """Processes asynchronous fact-checking for existing script claims."""

    def __init__(self, session_factory=None):
        self._session_factory = session_factory or AsyncSessionLocal

    async def validate(self, payload: Dict[str, Any]) -> None:
        if not payload or not isinstance(payload, dict):
            raise HardFailureException("Payload must be a non-empty JSON object.")
        script_id_raw = payload.get("script_id")
        if not script_id_raw:
            raise HardFailureException("Missing required parameter: 'script_id'.")
        try:
            UUID(str(script_id_raw))
        except (ValueError, TypeError):
            raise HardFailureException(f"Invalid UUID format for 'script_id': {script_id_raw}")

    async def execute(
        self,
        job: AutomationJob,
        update_progress: ProgressCallback,
        is_cancelled: CancellationChecker,
    ) -> Dict[str, Any]:
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from app.models.script import Script
        from app.schemas.script import ScriptClaimSchema
        from app.services.fact_checking import FactCheckingService

        payload = job.payload or {}
        script_id = UUID(str(payload["script_id"]))

        await update_progress(20, "LOADING_SCRIPT_EVIDENCE")
        if await is_cancelled():
            raise JobCancelledException("Job cancelled by user.")

        async with (self._session_factory)() as session:
            stmt = select(Script).options(selectinload(Script.claims)).where(Script.id == script_id)
            res = await session.execute(stmt)
            script = res.scalar_one_or_none()
            if not script:
                raise HardFailureException(f"Script with ID '{script_id}' not found.")

            raw_claims = [
                ScriptClaimSchema(
                    claim_text=c.claim_text,
                    extracted_entity=c.extracted_entity,
                    claim_type=c.claim_type,
                )
                for c in script.claims
            ]

            await update_progress(60, "VERIFYING_CLAIMS_AGAINST_SOURCES")
            if await is_cancelled():
                raise JobCancelledException("Job cancelled by user.")

            verified = await FactCheckingService.verify_script_claims(
                claims=raw_claims,
                project_id=script.project_id,
                db=session,
            )

            # Update existing claims
            for claim_row, ver in zip(script.claims, verified):
                claim_row.is_verified = ver.is_verified
                claim_row.confidence_score = ver.confidence_score
                claim_row.citation_url = ver.citation_url
                claim_row.citation_snippet = ver.citation_snippet

            await session.commit()

        await update_progress(100, "COMPLETED")
        return {
            "script_id": str(script_id),
            "total_claims": len(verified),
            "verified_count": sum(1 for c in verified if c.is_verified),
            "unverified_count": sum(1 for c in verified if not c.is_verified),
        }


class ScriptQualityEvaluationJobHandler(BaseJobHandler):
    """Processes asynchronous script quality, retention, and originality evaluation."""

    def __init__(self, session_factory=None):
        self._session_factory = session_factory or AsyncSessionLocal

    async def validate(self, payload: Dict[str, Any]) -> None:
        if not payload or not isinstance(payload, dict):
            raise HardFailureException("Payload must be a non-empty JSON object.")
        script_id_raw = payload.get("script_id")
        if not script_id_raw:
            raise HardFailureException("Missing required parameter: 'script_id'.")
        try:
            UUID(str(script_id_raw))
        except (ValueError, TypeError):
            raise HardFailureException(f"Invalid UUID format for 'script_id': {script_id_raw}")

    async def execute(
        self,
        job: AutomationJob,
        update_progress: ProgressCallback,
        is_cancelled: CancellationChecker,
    ) -> Dict[str, Any]:
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from app.models.script import Script
        from app.services.script_evaluation import ScriptEvaluationService

        payload = job.payload or {}
        script_id = UUID(str(payload["script_id"]))

        await update_progress(30, "LOADING_SCRIPT_CONTENT")
        if await is_cancelled():
            raise JobCancelledException("Job cancelled by user.")

        async with (self._session_factory)() as session:
            stmt = select(Script).options(selectinload(Script.claims)).where(Script.id == script_id)
            res = await session.execute(stmt)
            script = res.scalar_one_or_none()
            if not script:
                raise HardFailureException(f"Script with ID '{script_id}' not found.")

            first_sentence = script.full_text.split(".")[0] if script.full_text else ""
            claims = script.claims or []
            metrics = ScriptEvaluationService.evaluate_script(
                full_text=script.full_text,
                hook_text=first_sentence,
                total_claims=len(claims),
                verified_claims=sum(1 for c in claims if c.is_verified),
                unverified_claims=sum(1 for c in claims if not c.is_verified),
            )

        await update_progress(100, "COMPLETED")
        return {
            "script_id": str(script_id),
            "quality_metrics": metrics.model_dump(mode="json"),
        }
