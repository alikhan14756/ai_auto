"""Comprehensive tests for M15 Concurrency, Security, Governance, and QA Artifact Invalidation."""

import uuid
import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import select

from app.models.user import User
from app.models.channel import Channel, ChannelSettings
from app.models.project import VideoProject
from app.models.script import Script
from app.models.publication import PublicationPackage
from app.models.qa import QARun
from app.services.qa.constants import QAVetoDecision
from app.models.workflow import (
    WorkflowPolicy,
    WorkflowExecution,
    WorkflowStage,
    WORKFLOW_STATUS_RUNNING,
    WORKFLOW_STATUS_FAILED,
    WORKFLOW_STATUS_RECOVERING,
    STAGE_STATUS_RUNNING,
)
from app.models.job import AutomationJob, JOB_STATUS_PROCESSING
from app.services.orchestration.policy_engine import PolicyEngine
from app.services.orchestration.governor import ResourceGovernor
from app.services.orchestration.health_monitor import ProductionHealthMonitor
from app.services.qa.invalidation import QAInvalidationTracker
from app.services.qa.models import QAExecutionContext
from app.services.youtube.publishing_service import YouTubePublishingService, ERR_QA_DRIFT_DETECTED
from app.core.security import encrypt_token


@pytest.mark.asyncio
async def test_concurrent_workflow_creation_limit_enforced(db_session):
    """Verify that starting workflows beyond max_concurrent_workflows is strictly rejected."""
    user = User(
        supabase_user_id=f"user_{uuid.uuid4().hex[:8]}",
        email=f"creator_{uuid.uuid4().hex[:6]}@example.com",
        full_name="Concurrency Tester",
        role="CREATOR",
    )
    db_session.add(user)
    await db_session.flush()

    channel = Channel(
        user_id=user.id,
        youtube_channel_id=f"UC_{uuid.uuid4().hex[:10]}",
        title="Concurrency Channel",
        oauth_refresh_token_encrypted=encrypt_token("mock-token"),
        is_active=True,
    )
    db_session.add(channel)
    await db_session.flush()

    policy_engine = PolicyEngine(db_session)
    policy = await policy_engine.get_or_create_policy(channel.id)
    policy.max_concurrent_workflows = 2
    await db_session.flush()

    # Create 2 running workflow executions
    exec1 = WorkflowExecution(
        channel_id=channel.id,
        template_key="TEMPLATE_LONG_FORM",
        status=WORKFLOW_STATUS_RUNNING,
    )
    exec2 = WorkflowExecution(
        channel_id=channel.id,
        template_key="TEMPLATE_SHORTS",
        status=WORKFLOW_STATUS_RUNNING,
    )
    db_session.add_all([exec1, exec2])
    await db_session.flush()

    # Attempt to start a 3rd concurrent workflow
    can_start, reason = await policy_engine.can_start_workflow(
        channel.id, "TEMPLATE_LONG_FORM", "LONG_FORM"
    )

    assert can_start is False
    assert "Maximum concurrent workflows reached" in reason


@pytest.mark.asyncio
async def test_simultaneous_budget_reservations_zero_spend_lock(db_session):
    """Verify that multiple concurrent budget checks strictly reject paid operations under $0.00 cap."""
    user = User(
        supabase_user_id=f"user_{uuid.uuid4().hex[:8]}",
        email=f"budget_{uuid.uuid4().hex[:6]}@example.com",
        full_name="Budget Tester",
        role="CREATOR",
    )
    db_session.add(user)
    await db_session.flush()

    channel = Channel(
        user_id=user.id,
        youtube_channel_id=f"UC_{uuid.uuid4().hex[:10]}",
        title="Zero Spend Channel",
        oauth_refresh_token_encrypted=encrypt_token("mock-token"),
        is_active=True,
    )
    db_session.add(channel)
    await db_session.flush()

    governor = ResourceGovernor(db_session)

    # 1. Zero cost operation is allowed
    free_check = await governor.check_budget_availability(channel.id, 0.0)
    assert free_check is True

    # 2. Paid operations are strictly blocked under $0.00 ceiling
    paid_check1 = await governor.check_budget_availability(channel.id, 0.50)
    paid_check2 = await governor.check_budget_availability(channel.id, 10.00)
    assert paid_check1 is False
    assert paid_check2 is False


@pytest.mark.asyncio
async def test_worker_crash_recovery_and_bounded_retry_limit(db_session):
    """Verify that stalled jobs are detected by watchdog and retried only up to max_retry_attempts."""
    user = User(
        supabase_user_id=f"user_{uuid.uuid4().hex[:8]}",
        email=f"watchdog_{uuid.uuid4().hex[:6]}@example.com",
        full_name="Watchdog Tester",
        role="CREATOR",
    )
    db_session.add(user)
    await db_session.flush()

    channel = Channel(
        user_id=user.id,
        youtube_channel_id=f"UC_{uuid.uuid4().hex[:10]}",
        title="Watchdog Channel",
        oauth_refresh_token_encrypted=encrypt_token("mock-token"),
        is_active=True,
    )
    db_session.add(channel)
    await db_session.flush()

    policy_engine = PolicyEngine(db_session)
    policy = await policy_engine.get_or_create_policy(channel.id)
    policy.max_retry_attempts = 2  # Low bound for test
    await db_session.flush()

    execution = WorkflowExecution(
        channel_id=channel.id,
        template_key="TEMPLATE_LONG_FORM",
        status=WORKFLOW_STATUS_RUNNING,
        failure_count=0,
    )
    db_session.add(execution)
    await db_session.flush()

    stale_time = datetime.now(timezone.utc) - timedelta(seconds=300)
    job = AutomationJob(
        job_type="GENERATE_SCRIPT",
        channel_id=channel.id,
        idempotency_key=f"idemp_{uuid.uuid4().hex[:12]}",
        status=JOB_STATUS_PROCESSING,
        payload={"topic": "test"},
        heartbeat_at=stale_time,
    )
    db_session.add(job)
    await db_session.flush()

    stage = WorkflowStage(
        execution_id=execution.id,
        stage_key="SCRIPT_GENERATION",
        stage_name="Script Generation",
        job_type="GENERATE_SCRIPT",
        job_id=job.id,
        status=STAGE_STATUS_RUNNING,
    )
    db_session.add(stage)
    await db_session.flush()

    monitor = ProductionHealthMonitor(db_session)

    # 1. Watchdog detects stalled stage
    stalled = await monitor.detect_stalled_stages(channel.id)
    assert len(stalled) == 1
    assert stalled[0].id == stage.id

    # 2. First recovery attempt succeeds
    rec1 = await monitor.attempt_stage_recovery(stage)
    assert rec1 is True
    assert execution.failure_count == 1
    assert execution.status == WORKFLOW_STATUS_RECOVERING

    # 3. Second recovery attempt succeeds
    stage.status = STAGE_STATUS_RUNNING
    rec2 = await monitor.attempt_stage_recovery(stage)
    assert rec2 is True
    assert execution.failure_count == 2

    # 4. Third attempt exceeds max_retries (2) -> Bounded failure
    stage.status = STAGE_STATUS_RUNNING
    rec3 = await monitor.attempt_stage_recovery(stage)
    assert rec3 is False
    assert execution.status == WORKFLOW_STATUS_FAILED
    assert "Exhausted maximum retry attempts" in execution.error_message


@pytest.mark.asyncio
async def test_oauth_authorization_required_for_publishing(db_session):
    """Verify that a channel without OAuth credentials cannot authorize publication."""
    user = User(
        supabase_user_id=f"user_{uuid.uuid4().hex[:8]}",
        email=f"oauth_{uuid.uuid4().hex[:6]}@example.com",
        full_name="OAuth Tester",
        role="CREATOR",
    )
    db_session.add(user)
    await db_session.flush()

    channel = Channel(
        user_id=user.id,
        youtube_channel_id=f"UC_{uuid.uuid4().hex[:10]}",
        title="Unconnected OAuth Channel",
        oauth_refresh_token_encrypted="",  # Empty string (no OAuth credentials connected)
        is_active=True,
    )
    db_session.add(channel)
    await db_session.flush()

    project = VideoProject(
        channel_id=channel.id,
        title="OAuth Test Project",
        state="VIDEO_RENDERED",
    )
    db_session.add(project)
    await db_session.flush()

    policy_engine = PolicyEngine(db_session)
    can_publish, reason = await policy_engine.validate_publishing_authorization(
        channel.id, project.id
    )

    assert can_publish is False
    assert "YouTube OAuth credentials not connected" in reason


@pytest.mark.asyncio
async def test_qa_approval_invalidation_after_artifact_changes(db_session):
    """Verify that modifying production artifacts after QA approval strictly blocks publication via drift detection."""
    user = User(
        supabase_user_id=f"user_{uuid.uuid4().hex[:8]}",
        email=f"drift_{uuid.uuid4().hex[:6]}@example.com",
        full_name="Drift Tester",
        role="CREATOR",
    )
    db_session.add(user)
    await db_session.flush()

    channel = Channel(
        user_id=user.id,
        youtube_channel_id=f"UC_{uuid.uuid4().hex[:10]}",
        title="Drift Protection Channel",
        oauth_refresh_token_encrypted=encrypt_token("mock-token"),
        is_active=True,
    )
    db_session.add(channel)
    await db_session.flush()

    project = VideoProject(
        channel_id=channel.id,
        title="Drift Protected Project",
        format="LONG_FORM",
        state="READY_TO_PUBLISH",
    )
    db_session.add(project)
    await db_session.flush()

    script = Script(
        project_id=project.id,
        version=1,
        full_text="Original verified script text for QA review.",
        word_count=50,
        estimated_duration_seconds=30,
        is_locked=True,
    )
    db_session.add(script)
    await db_session.flush()

    package = PublicationPackage(
        project_id=project.id,
        status="APPROVED",
    )
    db_session.add(package)
    await db_session.flush()

    # 1. Capture snapshot of approved artifacts
    context = QAExecutionContext(
        project_id=project.id,
        project_title=project.title,
        project_format=project.format,
        channel_id=channel.id,
        script=script,
        scenes=[],
    )
    snapshot = QAInvalidationTracker.compute_context_snapshot(context)

    # 2. Approved QA run with saved snapshot
    qa_run = QARun(
        project_id=project.id,
        publication_package_id=package.id,
        run_number=1,
        status="COMPLETED",
        veto_decision=QAVetoDecision.APPROVED.value,
        overall_score=95.0,
        can_publish=True,
        input_versions_snapshot=snapshot,
    )
    db_session.add(qa_run)
    await db_session.commit()

    # 3. Simulate unauthorized modification of script artifact after QA approval
    script.full_text = "Modified unauthorized script text introduced after QA approval."
    await db_session.commit()

    # 4. Attempt to create publishing job -> Must fail with ERR_QA_DRIFT_DETECTED!
    with pytest.raises(ValueError) as excinfo:
        await YouTubePublishingService.create_publication_job(
            db=db_session,
            user_id=user.id,
            project_id=project.id,
            channel_id=channel.id,
            publication_package_id=package.id,
        )

    err_msg = str(excinfo.value)
    assert ERR_QA_DRIFT_DETECTED in err_msg
    assert "Production assets have drifted since last QA audit" in err_msg
