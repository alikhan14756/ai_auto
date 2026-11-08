"""Video Script Generation, Revision, and Fact-Checking REST API endpoints."""

from typing import List, Optional, Any, Dict
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Body, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, get_current_user
from app.models.channel import Channel
from app.models.project import VideoProject
from app.models.script import Script, ScriptClaim
from app.models.user import User
from app.providers.ai.base import AIBudgetExceededError, AIProviderError
from app.providers.ai.factory import get_ai_provider
from app.schemas.job import JobRead
from app.schemas.script import (
    ScriptGenerateRequest,
    ScriptOutlineRequest,
    ScriptOutlineResponse,
    ScriptResponse,
    ScriptUpdateRequest,
    SectionRegenerateRequest,
    ScriptQualityMetrics,
)
from app.services.fact_checking import FactCheckingService
from app.services.job_queue import JobQueueService
from app.services.script_evaluation import ScriptEvaluationService
from app.services.script_generation import ScriptGenerationService

router = APIRouter()


async def _verify_project_access(project_id: UUID, user: User, db: AsyncSession) -> VideoProject:
    """Verify that project exists and belongs to the authenticated user."""
    stmt = (
        select(VideoProject)
        .options(selectinload(VideoProject.channel))
        .where(VideoProject.id == project_id)
    )
    res = await db.execute(stmt)
    project = res.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="VideoProject not found.")

    if project.channel.user_id != user.id and user.role != "SUPER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this project.",
        )
    return project


def _attach_quality_metrics(script: Script) -> ScriptResponse:
    """Calculate and attach quality metrics to script response."""
    claims = script.claims or []
    verified_count = sum(1 for c in claims if c.is_verified)
    unverified_count = sum(1 for c in claims if not c.is_verified)

    # Derive hook preview
    first_sentence = script.full_text.split(".")[0] if script.full_text else ""
    metrics = ScriptEvaluationService.evaluate_script(
        full_text=script.full_text,
        hook_text=first_sentence,
        total_claims=len(claims),
        verified_claims=verified_count,
        unverified_claims=unverified_count,
    )

    resp = ScriptResponse.model_validate(script)
    resp.quality_metrics = metrics
    return resp


@router.post("/generate", response_model=JobRead, status_code=status.HTTP_202_ACCEPTED)
async def trigger_script_generation_job(
    request: ScriptGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Enqueue an asynchronous scriptwriting and fact-checking job."""
    project = await _verify_project_access(request.project_id, current_user, db)

    queue_service = JobQueueService(db)
    job, _ = await queue_service.enqueue_job(
        channel_id=project.channel_id,
        job_type="GENERATE_SCRIPT",
        payload={
            "project_id": str(request.project_id),
            "target_duration_seconds": request.target_duration_seconds,
            "tone": request.tone,
            "custom_instructions": request.custom_instructions,
        },
        priority=3,
    )
    return job


@router.post("/sync", response_model=ScriptResponse, status_code=status.HTTP_201_CREATED)
async def generate_script_sync(
    request: ScriptGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Synchronously execute script generation and return the verified draft immediately."""
    await _verify_project_access(request.project_id, current_user, db)

    try:
        service = ScriptGenerationService(provider=get_ai_provider())
        script = await service.generate_and_persist_script(
            project_id=request.project_id,
            db=db,
            target_duration_seconds=request.target_duration_seconds,
            tone=request.tone or "authoritative",
            custom_instructions=request.custom_instructions,
        )
        return _attach_quality_metrics(script)
    except AIBudgetExceededError as exc:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=str(exc))
    except AIProviderError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"AI Provider error: {str(exc)}")


@router.post("/outline", response_model=ScriptOutlineResponse, status_code=status.HTTP_200_OK)
async def generate_script_outline(
    request: ScriptOutlineRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a structured script outline and visual concept progression before writing full prose."""
    await _verify_project_access(request.project_id, current_user, db)
    try:
        service = ScriptGenerationService(provider=get_ai_provider())
        return await service.generate_outline(
            project_id=request.project_id,
            db=db,
            target_duration_seconds=request.target_duration_seconds,
            tone=request.tone or "authoritative",
            custom_instructions=request.custom_instructions,
        )
    except AIBudgetExceededError as exc:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=str(exc))
    except AIProviderError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"AI Provider error: {str(exc)}")


@router.get("", response_model=List[ScriptResponse])
async def list_scripts_for_project(
    project_id: Optional[UUID] = Query(None, description="Target VideoProject ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve version history of scripts for a project."""
    if project_id:
        await _verify_project_access(project_id, current_user, db)
        stmt = (
            select(Script)
            .options(selectinload(Script.claims))
            .where(Script.project_id == project_id)
            .order_by(Script.version.desc())
        )
    else:
        stmt = (
            select(Script)
            .join(VideoProject, Script.project_id == VideoProject.id)
            .join(Channel, VideoProject.channel_id == Channel.id)
        )
        if current_user.role != "SUPER_ADMIN":
            stmt = stmt.where(Channel.user_id == current_user.id)
        stmt = (
            stmt.options(selectinload(Script.claims))
            .order_by(Script.created_at.desc())
        )
    res = await db.execute(stmt)
    scripts = list(res.scalars().all())
    return [_attach_quality_metrics(s) for s in scripts]


@router.get("/{script_id}", response_model=ScriptResponse)
async def get_script(
    script_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve specific script version, fact-checked claims, and quality evaluation."""
    stmt = (
        select(Script)
        .options(selectinload(Script.claims))
        .where(Script.id == script_id)
    )
    res = await db.execute(stmt)
    script = res.scalar_one_or_none()
    if not script:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Script not found.")

    await _verify_project_access(script.project_id, current_user, db)
    return _attach_quality_metrics(script)


@router.patch("/{script_id}", response_model=ScriptResponse)
async def update_script(
    script_id: UUID,
    payload: ScriptUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update script text or toggle lock state."""
    stmt = (
        select(Script)
        .options(selectinload(Script.claims))
        .where(Script.id == script_id)
    )
    res = await db.execute(stmt)
    script = res.scalar_one_or_none()
    if not script:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Script not found.")

    await _verify_project_access(script.project_id, current_user, db)

    if script.is_locked and payload.full_text is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Script is approved and locked. Unlock before modifying content.",
        )

    if payload.full_text is not None:
        script.full_text = payload.full_text
        script.word_count = ScriptEvaluationService.calculate_word_count(payload.full_text)
        script.estimated_duration_seconds = ScriptEvaluationService.estimate_duration_seconds(script.word_count)

    if payload.is_locked is not None:
        script.is_locked = payload.is_locked

    await db.commit()
    await db.refresh(script)
    return _attach_quality_metrics(script)


@router.post("/{script_id}/regenerate-section", response_model=ScriptResponse)
async def regenerate_section(
    script_id: UUID,
    payload: SectionRegenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Regenerate a single narrative section while preserving the rest of the script."""
    stmt = select(Script).options(selectinload(Script.claims)).where(Script.id == script_id)
    res = await db.execute(stmt)
    script = res.scalar_one_or_none()
    if not script:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Script not found.")

    await _verify_project_access(script.project_id, current_user, db)

    service = ScriptGenerationService(provider=get_ai_provider())
    updated_script = await service.regenerate_section(
        script_id=script_id,
        section_id=payload.section_id,
        custom_prompt=payload.custom_prompt,
        db=db,
    )
    return _attach_quality_metrics(updated_script)


@router.post("/sections/{section_id}/regenerate", response_model=ScriptResponse)
async def regenerate_section_by_section_id(
    section_id: str,
    payload: Dict[str, Any] = Body(default={}),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Regenerate a single narrative section by section ID, resolving project script automatically."""
    refinement = payload.get("refinement_prompt") or payload.get("custom_prompt") or "Enhance clarity and technical accuracy"
    stmt = (
        select(Script)
        .join(VideoProject, Script.project_id == VideoProject.id)
        .join(Channel, VideoProject.channel_id == Channel.id)
    )
    if current_user.role != "SUPER_ADMIN":
        stmt = stmt.where(Channel.user_id == current_user.id)
    stmt = stmt.options(selectinload(Script.claims)).order_by(Script.created_at.desc())
    res = await db.execute(stmt)
    script = res.scalars().first()
    if not script:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active script found.")

    service = ScriptGenerationService(provider=get_ai_provider())
    updated_script = await service.regenerate_section(
        script_id=script.id,
        section_id=section_id,
        custom_prompt=refinement,
        db=db,
    )
    return _attach_quality_metrics(updated_script)


@router.post("/{script_id}/approve", response_model=ScriptResponse)
async def approve_script(
    script_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Approve and lock script for voice recording, advancing project state."""
    stmt = select(Script).options(selectinload(Script.claims)).where(Script.id == script_id)
    res = await db.execute(stmt)
    script = res.scalar_one_or_none()
    if not script:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Script not found.")

    project = await _verify_project_access(script.project_id, current_user, db)

    script.is_locked = True
    project.state = "SCRIPT_APPROVED"
    await db.commit()
    await db.refresh(script)
    return _attach_quality_metrics(script)
