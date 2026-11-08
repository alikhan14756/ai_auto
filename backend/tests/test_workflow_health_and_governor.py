"""Tests for Production Health Monitor, Watchdog Recovery, and Resource Governor."""

import datetime
from datetime import timezone, timedelta
import pytest
from app.models.workflow import (
    WorkflowExecution,
    WorkflowStage,
    WorkflowFailure,
    WORKFLOW_STATUS_RUNNING,
    WORKFLOW_STATUS_RECOVERING,
    WORKFLOW_STATUS_FAILED,
    STAGE_STATUS_RUNNING,
    STAGE_STATUS_PENDING,
)
from app.models.job import AutomationJob, JOB_STATUS_PROCESSING
from app.services.orchestration.health_monitor import ProductionHealthMonitor
from app.services.orchestration.governor import ResourceGovernor


@pytest.mark.asyncio
async def test_detect_stalled_stages(db_session, test_channel):
    """Verify watchdog detects stages whose background job heartbeats have lapsed."""
    monitor = ProductionHealthMonitor(db_session)

    # Create running execution
    execution = WorkflowExecution(
        channel_id=test_channel.id,
        template_key="TEMPLATE_LONG_FORM",
        status=WORKFLOW_STATUS_RUNNING,
    )
    db_session.add(execution)
    await db_session.flush()

    # Create stalled queue job (heartbeat lapsed 5 minutes ago)
    lapsed_time = datetime.datetime.now(timezone.utc) - timedelta(minutes=5)
    job = AutomationJob(
        channel_id=test_channel.id,
        job_type="RENDER_VIDEO",
        payload={},
        idempotency_key="stalled_job_test_01",
        status=JOB_STATUS_PROCESSING,
        heartbeat_at=lapsed_time,
        started_at=lapsed_time,
    )
    db_session.add(job)
    await db_session.flush()

    # Create running stage linked to stalled job
    stage = WorkflowStage(
        execution_id=execution.id,
        stage_key="stage_render",
        stage_name="FFmpeg Assembly",
        job_type="RENDER_VIDEO",
        job_id=job.id,
        status=STAGE_STATUS_RUNNING,
        started_at=lapsed_time,
    )
    db_session.add(stage)
    await db_session.flush()

    stalled = await monitor.detect_stalled_stages(test_channel.id)
    assert len(stalled) == 1
    assert stalled[0].stage_key == "stage_render"


@pytest.mark.asyncio
async def test_bounded_stage_recovery(db_session, test_channel):
    """Verify bounded recovery re-queues stalled stage and transitions execution to RECOVERING."""
    monitor = ProductionHealthMonitor(db_session)

    execution = WorkflowExecution(
        channel_id=test_channel.id,
        template_key="TEMPLATE_LONG_FORM",
        status=WORKFLOW_STATUS_RUNNING,
        failure_count=0,
    )
    db_session.add(execution)
    await db_session.flush()

    stage = WorkflowStage(
        execution_id=execution.id,
        stage_key="stage_narration",
        stage_name="Voice Synthesis",
        job_type="GENERATE_NARRATION",
        status=STAGE_STATUS_RUNNING,
    )
    db_session.add(stage)
    await db_session.flush()

    recovered = await monitor.attempt_stage_recovery(stage)
    assert recovered is True
    assert execution.status == WORKFLOW_STATUS_RECOVERING
    assert execution.failure_count == 1
    assert stage.status == STAGE_STATUS_PENDING


@pytest.mark.asyncio
async def test_exhausted_retries_fails_workflow(db_session, test_channel):
    """Verify that exceeding max_retry_attempts transitions execution to FAILED."""
    monitor = ProductionHealthMonitor(db_session)

    execution = WorkflowExecution(
        channel_id=test_channel.id,
        template_key="TEMPLATE_LONG_FORM",
        status=WORKFLOW_STATUS_RUNNING,
        failure_count=3,  # Already at limit
    )
    db_session.add(execution)
    await db_session.flush()

    stage = WorkflowStage(
        execution_id=execution.id,
        stage_key="stage_render",
        stage_name="FFmpeg Video Assembly",
        job_type="RENDER_VIDEO",
        status=STAGE_STATUS_RUNNING,
    )
    db_session.add(stage)
    await db_session.flush()

    recovered = await monitor.attempt_stage_recovery(stage)
    assert recovered is False
    assert execution.status == WORKFLOW_STATUS_FAILED
    assert "Exhausted maximum retry attempts" in execution.error_message


@pytest.mark.asyncio
async def test_resource_governor_usage_metering_and_spend(db_session, test_channel):
    """Verify resource usage recording, telemetry aggregation, and zero-dollar budget compliance."""
    governor = ResourceGovernor(db_session)

    # 1. Record free/local usage
    rec1 = await governor.record_usage(
        channel_id=test_channel.id,
        resource_type="GEMINI_TOKENS",
        amount_used=5000.0,
        unit="TOKENS",
        estimated_cost_usd=0.0,
    )
    assert rec1.id is not None

    rec2 = await governor.record_usage(
        channel_id=test_channel.id,
        resource_type="RENDER_SECONDS",
        amount_used=45.0,
        unit="SECONDS",
        estimated_cost_usd=0.0,
    )
    assert rec2.id is not None

    # 2. Check summary
    summary = await governor.get_resource_summary(test_channel.id)
    assert summary["current_month_spend_usd"] == 0.0
    assert "GEMINI_TOKENS" in summary["resource_breakdown"]
    assert summary["resource_breakdown"]["GEMINI_TOKENS"]["amount"] == 5000.0

    # 3. Check budget availability for free operations
    can_run_free = await governor.check_budget_availability(test_channel.id, 0.0)
    assert can_run_free is True

    # 4. Check budget availability for billable operation when budget is $0.00
    can_run_paid = await governor.check_budget_availability(test_channel.id, 5.0)
    assert can_run_paid is False
