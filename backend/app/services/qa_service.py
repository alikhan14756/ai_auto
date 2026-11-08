"""High-level QA Application Service managing QA runs, audits, and exceptions."""

import datetime
import uuid
from typing import Any, Dict, List, Optional, Set
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.channel import Channel
from app.models.project import VideoProject
from app.models.publication import PublicationPackage
from app.models.script import Script, ScriptClaim
from app.models.scene import Scene
from app.models.voice import NarrationTrack, Voiceover
from app.models.timeline import VideoTimeline, CaptionAsset
from app.models.render import RenderJob
from app.models.thumbnail import Thumbnail
from app.models.metadata import VideoMetadataDraft
from app.models.media import MediaAsset
from app.models.user import User
from app.models.qa import (
    QARun,
    QACheck,
    QAFinding,
    QACategoryScore,
    QAException,
)
from app.services.qa.constants import (
    QASeverity,
    QAFindingStatus,
    QAVetoDecision,
)
from app.services.qa.models import QAExecutionContext
from app.services.qa.orchestrator import QAOrchestrator
from app.services.qa.veto import QAVetoGate
from app.services.qa.invalidation import QAInvalidationTracker


class QAService:
    """Manages QA evaluation lifecycle, database synchronization, and policy gates."""

    @classmethod
    async def verify_project_access(cls, db: AsyncSession, project_id: UUID, user: User) -> VideoProject:
        """Verify user ownership or admin access to project."""
        stmt = (
            select(VideoProject)
            .join(Channel, VideoProject.channel_id == Channel.id)
            .where(VideoProject.id == project_id)
        )
        if user.role not in ["SUPER_ADMIN", "ADMIN"]:
            stmt = stmt.where(Channel.user_id == user.id)

        res = await db.execute(stmt)
        project = res.scalars().first()
        if not project:
            raise PermissionError("Access denied or project not found.")
        return project

    @classmethod
    async def assemble_context(
        cls,
        db: AsyncSession,
        project_id: UUID,
        package_id: Optional[UUID] = None,
    ) -> QAExecutionContext:
        """Fetch all production artifacts from database to build complete QA context."""
        # 1. Project
        proj_res = await db.execute(select(VideoProject).where(VideoProject.id == project_id))
        project = proj_res.scalars().first()
        if not project:
            raise ValueError(f"Project {project_id} not found.")

        # 2. Package (if provided, or latest)
        package = None
        if package_id:
            pkg_res = await db.execute(
                select(PublicationPackage).where(
                    PublicationPackage.id == package_id,
                    PublicationPackage.project_id == project_id,
                )
            )
            package = pkg_res.scalars().first()
            if not package:
                raise ValueError(f"PublicationPackage {package_id} does not belong to project {project_id}.")
        else:
            pkg_res = await db.execute(
                select(PublicationPackage)
                .where(PublicationPackage.project_id == project_id)
                .order_by(PublicationPackage.created_at.desc())
            )
            package = pkg_res.scalars().first()

        # 3. Script & Claims
        script_res = await db.execute(
            select(Script)
            .where(Script.project_id == project_id)
            .order_by(Script.version.desc())
        )
        script = script_res.scalars().first()

        claims_res = await db.execute(
            select(ScriptClaim).where(ScriptClaim.project_id == project_id)
        )
        claims = list(claims_res.scalars().all())

        # 4. Scenes & Media Assets
        scenes_res = await db.execute(
            select(Scene).where(Scene.project_id == project_id).order_by(Scene.scene_order)
        )
        scenes = list(scenes_res.scalars().all())

        media_res = await db.execute(
            select(MediaAsset).where(MediaAsset.project_id == project_id)
        )
        media_assets = list(media_res.scalars().all())

        # 5. Narration
        narr_res = await db.execute(
            select(NarrationTrack)
            .where(NarrationTrack.project_id == project_id)
            .order_by(NarrationTrack.created_at.desc())
        )
        narration_track = narr_res.scalars().first()

        # 6. Timeline & Captions
        tl_res = await db.execute(
            select(VideoTimeline)
            .where(VideoTimeline.project_id == project_id)
            .order_by(VideoTimeline.created_at.desc())
        )
        timeline = tl_res.scalars().first()

        caption_asset = None
        if timeline:
            cap_res = await db.execute(
                select(CaptionAsset).where(CaptionAsset.timeline_id == timeline.id)
            )
            caption_asset = cap_res.scalars().first()

        # 7. Render Job (from package or latest completed)
        render_job = None
        if package and package.render_job_id:
            r_res = await db.execute(
                select(RenderJob)
                .where(RenderJob.id == package.render_job_id)
                .options(selectinload(RenderJob.quality_reports))
            )
            render_job = r_res.scalars().first()
        if not render_job:
            r_res = await db.execute(
                select(RenderJob)
                .where(RenderJob.project_id == project_id, RenderJob.status == "COMPLETED")
                .options(selectinload(RenderJob.quality_reports))
                .order_by(RenderJob.created_at.desc())
            )
            render_job = r_res.scalars().first()

        quality_report = render_job.quality_reports[0] if (render_job and render_job.quality_reports) else None

        # 8. Thumbnail (from package or selected)
        thumbnail = None
        if package and package.thumbnail_id:
            th_res = await db.execute(select(Thumbnail).where(Thumbnail.id == package.thumbnail_id))
            thumbnail = th_res.scalars().first()
        if not thumbnail:
            th_res = await db.execute(
                select(Thumbnail)
                .where(Thumbnail.project_id == project_id, Thumbnail.is_selected == True)
            )
            thumbnail = th_res.scalars().first()

        # 9. Metadata Draft
        metadata_draft = None
        if package and package.metadata_id:
            m_res = await db.execute(select(VideoMetadataDraft).where(VideoMetadataDraft.id == package.metadata_id))
            metadata_draft = m_res.scalars().first()
        if not metadata_draft:
            m_res = await db.execute(
                select(VideoMetadataDraft)
                .where(VideoMetadataDraft.project_id == project_id)
                .order_by(VideoMetadataDraft.is_approved.desc(), VideoMetadataDraft.created_at.desc())
            )
            metadata_draft = m_res.scalars().first()

        return QAExecutionContext(
            project_id=project.id,
            project_title=project.title,
            project_format=project.format,
            channel_id=project.channel_id,
            package_id=package.id if package else None,
            script=script,
            script_claims=claims,
            scenes=scenes,
            narration_track=narration_track,
            timeline=timeline,
            caption_asset=caption_asset,
            render_job=render_job,
            thumbnail=thumbnail,
            metadata_draft=metadata_draft,
            media_assets=media_assets,
            quality_report=quality_report,
            video_path=render_job.output_video_path if render_job else None,
            audio_path=narration_track.audio_file_path if narration_track else None,
            thumbnail_path=thumbnail.storage_path if thumbnail else None,
            subtitles_path=caption_asset.file_path if caption_asset else None,
        )

    @classmethod
    async def create_qa_run(
        cls,
        db: AsyncSession,
        project_id: UUID,
        package_id: Optional[UUID],
        user: User,
    ) -> QARun:
        """Initialize a new QA evaluation run in QUEUED status."""
        await cls.verify_project_access(db, project_id, user)

        # Determine run number
        count_stmt = select(func.count(QARun.id)).where(QARun.project_id == project_id)
        count_res = await db.execute(count_stmt)
        run_number = (count_res.scalar() or 0) + 1

        qa_run = QARun(
            id=uuid.uuid4(),
            project_id=project_id,
            publication_package_id=package_id,
            run_number=run_number,
            status="QUEUED",
            veto_decision=QAVetoDecision.BLOCKED.value,
            can_publish=False,
            input_versions_snapshot={},
            summary={},
        )
        db.add(qa_run)
        await db.commit()
        return await cls.get_qa_run(db, qa_run.id)

    @classmethod
    async def execute_qa_run(
        cls,
        db: AsyncSession,
        run_id: UUID,
        target_categories: Optional[Set[str]] = None,
    ) -> QARun:
        """Execute the full 12-category QA evaluation and persist checks, findings, and scores."""
        run_stmt = select(QARun).where(QARun.id == run_id)
        run_res = await db.execute(run_stmt)
        qa_run = run_res.scalars().first()
        if not qa_run:
            raise ValueError(f"QA Run {run_id} not found.")

        qa_run.status = "RUNNING"
        await db.commit()

        try:
            # 1. Assemble complete context
            context = await cls.assemble_context(db, qa_run.project_id, qa_run.publication_package_id)

            # 2. Gather active exceptions
            exc_stmt = (
                select(QAException.finding_id)
                .join(QAFinding, QAException.finding_id == QAFinding.id)
                .where(QAFinding.qa_run_id == qa_run.id)
            )
            exc_res = await db.execute(exc_stmt)
            excepted_ids = {str(r) for r in exc_res.scalars().all()}

            # 3. Run Orchestrator
            orchestrator = QAOrchestrator()
            report = await orchestrator.evaluate_context(
                context=context,
                target_categories=target_categories,
                excepted_finding_ids=excepted_ids,
            )

            # 4. Clear any old checks, findings, scores for this run if re-running
            check_ids_stmt = select(QACheck.id).where(QACheck.qa_run_id == run_id)
            c_res = await db.execute(check_ids_stmt)
            # SQLAlchemy cascade will delete associated findings and exceptions if configured,
            # but let's persist fresh records.

            # 5. Persist Checks & Findings
            qa_run.checks = []
            qa_run.findings = []
            qa_run.category_scores = []

            for cr in report["check_results"]:
                db_check = QACheck(
                    id=uuid.uuid4(),
                    qa_run_id=qa_run.id,
                    category=cr.category,
                    check_name=cr.check_name,
                    status=cr.status,
                    score=cr.score,
                    execution_time_ms=cr.execution_time_ms,
                    metrics=cr.metrics,
                    error_message=cr.error_message,
                )
                qa_run.checks.append(db_check)

                for f in cr.findings:
                    db_finding = QAFinding(
                        id=uuid.uuid4(),
                        qa_run_id=qa_run.id,
                        check_id=db_check.id,
                        category=f.category,
                        severity=f.severity,
                        status=QAFindingStatus.OPEN.value,
                        affected_artifact=f.affected_artifact,
                        title=f.title,
                        explanation=f.explanation,
                        evidence=f.evidence,
                        recommended_correction=f.recommended_correction,
                        requires_human_review=f.requires_human_review,
                    )
                    db_finding.exceptions = []
                    qa_run.findings.append(db_finding)

            # 6. Persist Category Scores
            for cat_name, cat_data in report["category_scores"].items():
                db_cat = QACategoryScore(
                    id=uuid.uuid4(),
                    qa_run_id=qa_run.id,
                    category=cat_name,
                    weight=cat_data["weight"],
                    raw_score=cat_data["raw_score"],
                    weighted_score=cat_data["weighted_score"],
                    deductions=cat_data["deductions"],
                    check_count=cat_data["check_count"],
                    passed_count=cat_data["passed_count"],
                    warning_count=cat_data["warning_count"],
                    failed_count=cat_data["failed_count"],
                )
                qa_run.category_scores.append(db_cat)

            # 7. Update QARun
            qa_run.overall_score = report["overall_score"]
            qa_run.veto_decision = report["veto_decision"]
            qa_run.can_publish = report["can_publish"]
            qa_run.summary = report["summary"]
            qa_run.input_versions_snapshot = report["snapshot"]
            qa_run.status = "COMPLETED"

            # 8. Synchronize VideoProject state
            proj_res = await db.execute(select(VideoProject).where(VideoProject.id == qa_run.project_id))
            proj = proj_res.scalars().first()
            if proj:
                if qa_run.veto_decision == "APPROVED":
                    proj.state = "READY_TO_PUBLISH"
                elif qa_run.can_publish:
                    proj.state = "READY_FOR_APPROVAL"
                else:
                    proj.state = "NEEDS_ATTENTION"

            await db.commit()
            return qa_run

        except Exception as e:
            logger.error("QA evaluation run failed", exc_info=True)
            qa_run.status = "FAILED"
            qa_run.error_message = str(e)
            await db.commit()
            raise

    @classmethod
    async def get_qa_run(
        cls,
        db: AsyncSession,
        run_id: UUID,
        user: Optional[User] = None,
    ) -> QARun:
        """Fetch full QA run with eager-loaded checks, findings, and category scores."""
        stmt = (
            select(QARun)
            .where(QARun.id == run_id)
            .options(
                selectinload(QARun.checks),
                selectinload(QARun.findings).selectinload(QAFinding.exceptions),
                selectinload(QARun.category_scores),
                selectinload(QARun.project),
            )
        )
        res = await db.execute(stmt)
        qa_run = res.scalars().first()
        if not qa_run:
            raise ValueError(f"QA Run {run_id} not found.")

        if user:
            await cls.verify_project_access(db, qa_run.project_id, user)

        return qa_run

    @classmethod
    async def list_qa_runs_for_project(
        cls,
        db: AsyncSession,
        project_id: UUID,
        user: User,
    ) -> List[QARun]:
        """List all historical QA runs for a project."""
        await cls.verify_project_access(db, project_id, user)
        stmt = (
            select(QARun)
            .where(QARun.project_id == project_id)
            .order_by(QARun.run_number.desc())
            .options(
                selectinload(QARun.checks),
                selectinload(QARun.findings).selectinload(QAFinding.exceptions),
                selectinload(QARun.category_scores),
            )
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @classmethod
    async def resolve_finding(
        cls,
        db: AsyncSession,
        finding_id: UUID,
        user: User,
        resolution_notes: str,
    ) -> QAFinding:
        """Mark a finding as resolved with notes and recalculate veto gate."""
        stmt = (
            select(QAFinding)
            .where(QAFinding.id == finding_id)
            .options(selectinload(QAFinding.qa_run), selectinload(QAFinding.exceptions))
        )
        res = await db.execute(stmt)
        finding = res.scalars().first()
        if not finding:
            raise ValueError(f"Finding {finding_id} not found.")

        # Check project ownership
        await cls.verify_project_access(db, finding.qa_run.project_id, user)

        finding.status = QAFindingStatus.RESOLVED.value
        finding.resolved_by_user_id = user.id
        finding.resolved_at = datetime.datetime.now(datetime.timezone.utc)
        finding.resolution_notes = resolution_notes

        await db.commit()

        # Recalculate parent QARun veto decision
        await cls.recompute_run_veto(db, finding.qa_run_id)

        await db.refresh(finding)
        return finding

    @classmethod
    async def authorize_exception(
        cls,
        db: AsyncSession,
        finding_id: UUID,
        user: User,
        reason: str,
        expires_at: Optional[datetime.datetime] = None,
    ) -> QAException:
        """Grant authorized administrative exception for a HIGH severity finding."""
        # 1. RBAC Check: Only SUPER_ADMIN and ADMIN can authorize exceptions
        if user.role not in ["SUPER_ADMIN", "ADMIN"]:
            raise PermissionError("Only administrators can authorize QA exceptions.")

        stmt = (
            select(QAFinding)
            .where(QAFinding.id == finding_id)
            .options(selectinload(QAFinding.qa_run), selectinload(QAFinding.exceptions))
        )
        res = await db.execute(stmt)
        finding = res.scalars().first()
        if not finding:
            raise ValueError(f"Finding {finding_id} not found.")

        # Check project ownership
        await cls.verify_project_access(db, finding.qa_run.project_id, user)

        # 2. Hard Policy: CRITICAL findings can NEVER be overridden
        if finding.severity == QASeverity.CRITICAL.value:
            raise ValueError("CRITICAL severity findings represent hard blockers and cannot be overridden by exception.")

        finding.status = QAFindingStatus.ACCEPTED_WITH_EXCEPTION.value

        exception = QAException(
            id=uuid.uuid4(),
            finding_id=finding.id,
            authorized_by_user_id=user.id,
            reason=reason,
            expires_at=expires_at,
        )
        db.add(exception)
        await db.commit()

        # Recalculate parent QARun veto decision
        await cls.recompute_run_veto(db, finding.qa_run_id)

        await db.refresh(exception)
        return exception

    @classmethod
    async def recompute_run_veto(cls, db: AsyncSession, run_id: UUID) -> QARun:
        """Re-evaluate the veto gate for a run after finding resolution or exception."""
        qa_run = await cls.get_qa_run(db, run_id)

        # Collect active findings dict
        findings_payload = []
        for f in qa_run.findings:
            findings_payload.append({
                "id": str(f.id),
                "severity": f.severity,
                "status": f.status,
                "title": f.title,
            })

        # Collect excepted finding IDs
        exc_ids = {str(f.id) for f in qa_run.findings if f.status == QAFindingStatus.ACCEPTED_WITH_EXCEPTION.value}

        overall_score = float(qa_run.overall_score or 100.0)
        veto_decision, can_publish, breakdown = QAVetoGate.evaluate(
            findings=findings_payload,
            excepted_finding_ids=exc_ids,
            overall_score=overall_score,
        )

        qa_run.veto_decision = veto_decision
        qa_run.can_publish = can_publish
        summary = dict(qa_run.summary or {})
        summary.update(breakdown)
        qa_run.summary = summary

        # Sync project state
        proj_res = await db.execute(select(VideoProject).where(VideoProject.id == qa_run.project_id))
        proj = proj_res.scalars().first()
        if proj:
            if qa_run.veto_decision == "APPROVED":
                proj.state = "READY_TO_PUBLISH"
            elif qa_run.can_publish:
                proj.state = "READY_FOR_APPROVAL"
            else:
                proj.state = "NEEDS_ATTENTION"

        await db.commit()
        await db.refresh(qa_run)
        return qa_run
