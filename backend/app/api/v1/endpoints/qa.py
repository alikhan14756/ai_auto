"""FastAPI REST API router for Autonomous QA and Veto Gate."""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.schemas.qa import (
    QARunResponse,
    QAFindingResponse,
    QARunTriggerRequest,
    QAFindingResolveRequest,
    QAExceptionCreateRequest,
    QAExceptionResponse,
    QAReadinessResponse,
)
from app.services.qa_service import QAService
from app.services.qa.corrections import QACorrectionEngine
from app.services.job_queue import JobQueueService

router = APIRouter(prefix="/qa", tags=["Quality Assurance"])


@router.post("/runs", response_model=QARunResponse, status_code=status.HTTP_201_CREATED)
async def trigger_qa_run(
    req: QARunTriggerRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Trigger an autonomous QA evaluation run for a video project and publication package."""
    try:
        qa_run = await QAService.create_qa_run(
            db=db,
            project_id=req.project_id,
            package_id=req.publication_package_id,
            user=current_user,
        )

        if req.run_async:
            # Enqueue to durable worker queue
            project = await QAService.verify_project_access(db, req.project_id, current_user)
            queue_service = JobQueueService(db)
            await queue_service.enqueue_job(
                channel_id=project.channel_id,
                job_type="QA_PACKAGE_INSPECTION",
                payload={
                    "run_id": str(qa_run.id),
                    "project_id": str(req.project_id),
                    "package_id": str(req.publication_package_id) if req.publication_package_id else None,
                    "target_categories": req.target_categories,
                },
                priority=1,
            )
            return qa_run
        else:
            # Execute synchronously
            target_set = set(req.target_categories) if req.target_categories else None
            completed_run = await QAService.execute_qa_run(
                db=db,
                run_id=qa_run.id,
                target_categories=target_set,
            )
            return completed_run

    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/runs/{run_id}", response_model=QARunResponse)
async def get_qa_run(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve full QA run report with all category checks, findings, and score breakdown."""
    try:
        return await QAService.get_qa_run(db=db, run_id=run_id, user=current_user)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/runs/project/{project_id}", response_model=List[QARunResponse])
async def list_project_qa_runs(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List historical QA runs for a project."""
    try:
        return await QAService.list_qa_runs_for_project(db=db, project_id=project_id, user=current_user)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/runs/{run_id}/readiness", response_model=QAReadinessResponse)
async def check_publication_readiness(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fast check returning whether the video publication package is released by the veto gate."""
    try:
        qa_run = await QAService.get_qa_run(db=db, run_id=run_id, user=current_user)
        return QAReadinessResponse(
            project_id=qa_run.project_id,
            can_publish=qa_run.can_publish,
            veto_decision=qa_run.veto_decision,
            overall_score=float(qa_run.overall_score or 0.0),
            summary=qa_run.summary,
        )
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/findings/{finding_id}/resolve", response_model=QAFindingResponse)
async def resolve_finding(
    finding_id: UUID,
    req: QAFindingResolveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark a QA finding as resolved with detailed notes and re-evaluate the veto gate."""
    try:
        return await QAService.resolve_finding(
            db=db,
            finding_id=finding_id,
            user=current_user,
            resolution_notes=req.resolution_notes,
        )
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/findings/{finding_id}/exception", response_model=QAExceptionResponse)
async def authorize_exception(
    finding_id: UUID,
    req: QAExceptionCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Authorize an administrative override exception for a HIGH severity finding (Admins only)."""
    try:
        return await QAService.authorize_exception(
            db=db,
            finding_id=finding_id,
            user=current_user,
            reason=req.reason,
            expires_at=req.expires_at,
        )
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/findings/{finding_id}/guide")
async def get_finding_correction_guide(
    finding_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve actionable, step-by-step remediation guide for a specific finding."""
    from app.models.qa import QAFinding
    from sqlalchemy.orm import selectinload
    stmt = select(QAFinding).where(QAFinding.id == finding_id).options(selectinload(QAFinding.qa_run))
    res = await db.execute(stmt)
    finding = res.scalars().first()
    if not finding:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Finding {finding_id} not found.")

    await QAService.verify_project_access(db, finding.qa_run.project_id, current_user)

    guide = QACorrectionEngine.generate_correction_guide({
        "category": finding.category,
        "severity": finding.severity,
        "title": finding.title,
        "affected_artifact": finding.affected_artifact,
        "evidence": finding.evidence,
    })
    return guide
