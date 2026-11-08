"""Tests for YouTube Publishing: M11 QA Veto Gate Enforcement, Anti-Drift Verification, and Idempotency."""

import uuid
import pytest
from app.models.project import VideoProject
from app.models.publication import PublicationPackage
from app.models.qa import QARun, QAFinding
from app.services.qa.constants import QAVetoDecision, QASeverity, QAFindingStatus
from app.services.youtube.publishing_service import YouTubePublishingService
from app.services.youtube.constants import (
    ERR_QA_VETO_BLOCKED,
    ERR_QA_DRIFT_DETECTED,
    ERR_CROSS_TENANT_FORBIDDEN,
    STATUS_PENDING,
    STAGE_QUEUED,
)
from tests.conftest import auth_headers_for


@pytest.mark.asyncio
async def test_publishing_rejected_when_no_qa_run_exists(db_session, test_user, test_channel):
    """Verify that a project without any QA audit run is strictly rejected with ERR_QA_VETO_BLOCKED."""
    project = VideoProject(
        channel_id=test_channel.id,
        title="Unverified Project",
        target_duration_seconds=300,
        state="DRAFT",
    )
    db_session.add(project)
    await db_session.flush()

    package = PublicationPackage(
        project_id=project.id,
        status="DRAFT",
    )
    db_session.add(package)
    await db_session.commit()

    with pytest.raises(ValueError, match=ERR_QA_VETO_BLOCKED):
        await YouTubePublishingService.create_publication_job(
            db=db_session,
            user_id=test_user.id,
            project_id=project.id,
            channel_id=test_channel.id,
            publication_package_id=package.id,
        )


@pytest.mark.asyncio
async def test_publishing_rejected_when_qa_veto_blocked(db_session, test_user, test_channel):
    """Verify that a project with a BLOCKED QA run and can_publish=False cannot publish."""
    project = VideoProject(
        channel_id=test_channel.id,
        title="Blocked Project",
        target_duration_seconds=300,
        state="DRAFT",
    )
    db_session.add(project)
    await db_session.flush()

    package = PublicationPackage(
        project_id=project.id,
        status="DRAFT",
    )
    db_session.add(package)
    await db_session.flush()

    # QA Run marked BLOCKED
    qa_run = QARun(
        project_id=project.id,
        publication_package_id=package.id,
        run_number=1,
        status="COMPLETED",
        veto_decision=QAVetoDecision.BLOCKED.value,
        can_publish=False,
    )
    db_session.add(qa_run)
    await db_session.commit()

    with pytest.raises(ValueError, match=ERR_QA_VETO_BLOCKED):
        await YouTubePublishingService.create_publication_job(
            db=db_session,
            user_id=test_user.id,
            project_id=project.id,
            channel_id=test_channel.id,
            publication_package_id=package.id,
        )


@pytest.mark.asyncio
async def test_publishing_rejected_when_unresolved_critical_finding_present(db_session, test_user, test_channel):
    """Verify that an unresolved CRITICAL finding strictly blocks publication even if flag is toggled."""
    project = VideoProject(
        channel_id=test_channel.id,
        title="Critical Finding Project",
        target_duration_seconds=300,
        state="DRAFT",
    )
    db_session.add(project)
    await db_session.flush()

    package = PublicationPackage(
        project_id=project.id,
        status="DRAFT",
    )
    db_session.add(package)
    await db_session.flush()

    qa_run = QARun(
        project_id=project.id,
        publication_package_id=package.id,
        run_number=1,
        status="COMPLETED",
        veto_decision=QAVetoDecision.APPROVED.value,
        can_publish=True,
    )
    db_session.add(qa_run)
    await db_session.flush()

    # Add unresolved critical finding
    critical_finding = QAFinding(
        qa_run_id=qa_run.id,
        category="SECURITY_PRIVACY",
        severity=QASeverity.CRITICAL.value,
        affected_artifact="script",
        title="Stolen API Key in Video",
        explanation="Secret key exposed in video transcript",
        recommended_correction="Scan and remove secret key from video",
        status=QAFindingStatus.OPEN.value,
    )
    db_session.add(critical_finding)
    await db_session.commit()

    with pytest.raises(ValueError, match="Blocking CRITICAL finding detected"):
        await YouTubePublishingService.create_publication_job(
            db=db_session,
            user_id=test_user.id,
            project_id=project.id,
            channel_id=test_channel.id,
            publication_package_id=package.id,
        )


@pytest.mark.asyncio
async def test_publishing_approved_when_qa_clean(db_session, test_user, test_channel):
    """Verify that an APPROVED QA run with can_publish=True succeeds in creating PublishingJob."""
    project = VideoProject(
        channel_id=test_channel.id,
        title="Clean Approved Project",
        target_duration_seconds=300,
        state="READY_TO_PUBLISH",
    )
    db_session.add(project)
    await db_session.flush()

    package = PublicationPackage(
        project_id=project.id,
        status="APPROVED",
    )
    db_session.add(package)
    await db_session.flush()

    qa_run = QARun(
        project_id=project.id,
        publication_package_id=package.id,
        run_number=1,
        status="COMPLETED",
        veto_decision=QAVetoDecision.APPROVED.value,
        can_publish=True,
    )
    db_session.add(qa_run)
    await db_session.commit()

    pub_job = await YouTubePublishingService.create_publication_job(
        db=db_session,
        user_id=test_user.id,
        project_id=project.id,
        channel_id=test_channel.id,
        publication_package_id=package.id,
        privacy_status="unlisted",
    )

    assert pub_job.id is not None
    assert pub_job.status == STATUS_PENDING
    assert pub_job.current_stage == STAGE_QUEUED
    assert pub_job.privacy_status == "unlisted"
    assert pub_job.synthetic_media_declared is True


@pytest.mark.asyncio
async def test_idempotency_duplicate_prevention(db_session, test_user, test_channel):
    """Verify that duplicate requests with the same idempotency_key return the identical job."""
    project = VideoProject(
        channel_id=test_channel.id,
        title="Idempotent Project",
        state="READY_TO_PUBLISH",
    )
    db_session.add(project)
    await db_session.flush()

    package = PublicationPackage(project_id=project.id, status="APPROVED")
    db_session.add(package)
    await db_session.flush()

    qa_run = QARun(
        project_id=project.id,
        publication_package_id=package.id,
        run_number=1,
        status="COMPLETED",
        veto_decision=QAVetoDecision.APPROVED.value,
        can_publish=True,
    )
    db_session.add(qa_run)
    await db_session.commit()

    idempotency_key = f"idempotent_test_{uuid.uuid4().hex}"

    job1 = await YouTubePublishingService.create_publication_job(
        db=db_session,
        user_id=test_user.id,
        project_id=project.id,
        channel_id=test_channel.id,
        publication_package_id=package.id,
        idempotency_key=idempotency_key,
    )

    job2 = await YouTubePublishingService.create_publication_job(
        db=db_session,
        user_id=test_user.id,
        project_id=project.id,
        channel_id=test_channel.id,
        publication_package_id=package.id,
        idempotency_key=idempotency_key,
    )

    assert job1.id == job2.id


@pytest.mark.asyncio
async def test_cross_tenant_isolation_on_publishing(db_session, test_user, other_user, test_channel):
    """Verify that a user cannot create a publication request for a channel they do not own."""
    project = VideoProject(
        channel_id=test_channel.id,
        title="Tenant Isolation Project",
        state="READY_TO_PUBLISH",
    )
    db_session.add(project)
    await db_session.flush()

    package = PublicationPackage(project_id=project.id, status="APPROVED")
    db_session.add(package)
    await db_session.flush()

    qa_run = QARun(
        project_id=project.id,
        publication_package_id=package.id,
        run_number=1,
        status="COMPLETED",
        veto_decision=QAVetoDecision.APPROVED.value,
        can_publish=True,
    )
    db_session.add(qa_run)
    await db_session.commit()

    with pytest.raises(ValueError, match=ERR_CROSS_TENANT_FORBIDDEN):
        # other_user attempts to publish on test_user's channel
        await YouTubePublishingService.create_publication_job(
            db=db_session,
            user_id=other_user.id,
            project_id=project.id,
            channel_id=test_channel.id,
            publication_package_id=package.id,
        )
