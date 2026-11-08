"""Tests for state-machine driven Workflow Engine."""

import pytest
from app.models.workflow import (
    WorkflowExecution,
    WorkflowStage,
    WORKFLOW_STATUS_DRAFT,
    WORKFLOW_STATUS_READY,
    WORKFLOW_STATUS_RUNNING,
    WORKFLOW_STATUS_PAUSED,
    WORKFLOW_STATUS_WAITING_FOR_APPROVAL,
    WORKFLOW_STATUS_COMPLETED,
    WORKFLOW_STATUS_CANCELLED,
    STAGE_STATUS_PENDING,
    STAGE_STATUS_RUNNING,
    STAGE_STATUS_COMPLETED,
    STAGE_STATUS_SKIPPED,
)
from app.services.orchestration.workflow_engine import (
    WorkflowEngine,
    InvalidStateTransitionError,
)
from app.services.orchestration.templates import TEMPLATE_LONG_FORM, TEMPLATE_SHORTS


@pytest.mark.asyncio
async def test_workflow_creation_and_stage_materialization(db_session, test_channel):
    """Verify workflow execution instantiation materializes standard template stages in sequence."""
    engine = WorkflowEngine(db_session)

    execution = await engine.create_execution(
        channel_id=test_channel.id,
        template_key=TEMPLATE_LONG_FORM,
        context_data={"topic": "Autonomous AI Agents"},
    )
    await db_session.flush()

    assert execution.id is not None
    assert execution.channel_id == test_channel.id
    assert execution.status == WORKFLOW_STATUS_DRAFT
    assert execution.progress_percentage == 0
    assert len(execution.stages) == 8

    # Verify order and stage keys
    expected_keys = [
        "stage_topic",
        "stage_script",
        "stage_narration",
        "stage_visuals",
        "stage_render",
        "stage_seo",
        "stage_qa",
        "stage_publishing",
    ]
    actual_keys = [s.stage_key for s in execution.stages]
    assert actual_keys == expected_keys

    for stage in execution.stages:
        assert stage.status == STAGE_STATUS_PENDING


@pytest.mark.asyncio
async def test_workflow_lifecycle_transitions(db_session, test_channel):
    """Verify start, pause, resume, cancel and rejection of invalid state transitions."""
    engine = WorkflowEngine(db_session)
    policy = await engine.policy_engine.get_or_create_policy(test_channel.id)
    policy.require_topic_approval = False
    await db_session.flush()

    execution = await engine.create_execution(
        channel_id=test_channel.id,
        template_key=TEMPLATE_SHORTS,
    )
    await db_session.flush()

    # 1. Start execution: DRAFT -> READY -> RUNNING
    started = await engine.start_execution(execution.id)
    assert started.status == WORKFLOW_STATUS_RUNNING
    assert started.started_at is not None

    # 2. Pause execution: RUNNING -> PAUSED
    paused = await engine.pause_execution(execution.id)
    assert paused.status == WORKFLOW_STATUS_PAUSED

    # 3. Resume execution: PAUSED -> RUNNING
    resumed = await engine.resume_execution(execution.id)
    assert resumed.status == WORKFLOW_STATUS_RUNNING

    # 4. Cancel execution: RUNNING -> CANCELLED
    cancelled = await engine.cancel_execution(execution.id)
    assert cancelled.status == WORKFLOW_STATUS_CANCELLED

    # Verify pending stages are marked SKIPPED
    for st in cancelled.stages:
        assert st.status in (STAGE_STATUS_SKIPPED, STAGE_STATUS_RUNNING, STAGE_STATUS_COMPLETED)

    # 5. Invalid transition rejection: CANCELLED -> RUNNING must raise InvalidStateTransitionError
    with pytest.raises(InvalidStateTransitionError):
        await engine.resume_execution(execution.id)


@pytest.mark.asyncio
async def test_workflow_checkpoint_approval_and_advancement(db_session, test_channel):
    """Verify execution halts at configured approval checkpoints and advances when approved."""
    engine = WorkflowEngine(db_session)

    execution = await engine.create_execution(
        channel_id=test_channel.id,
        template_key=TEMPLATE_LONG_FORM,
    )
    await db_session.flush()

    # In default Level 1 (Assisted), stage_topic requires approval
    started = await engine.start_execution(execution.id)
    assert started.status == WORKFLOW_STATUS_WAITING_FOR_APPROVAL
    assert started.checkpoint_required == "stage_topic"

    # Approve checkpoint
    approved = await engine.approve_checkpoint(execution.id, "stage_topic")
    assert approved.status == WORKFLOW_STATUS_RUNNING
    assert approved.checkpoint_required is None

    # First stage should now be RUNNING with an enqueued job
    stage_0 = approved.stages[0]
    assert stage_0.status == STAGE_STATUS_RUNNING
    assert stage_0.job_id is not None


@pytest.mark.asyncio
async def test_workflow_completion_advancement(db_session, test_channel):
    """Verify that marking all stages completed advances progress to 100% and status to COMPLETED."""
    engine = WorkflowEngine(db_session)

    # Use a 1-stage template for clean completion test
    policy = await engine.policy_engine.get_or_create_policy(test_channel.id)
    policy.require_topic_approval = False
    await db_session.flush()

    execution = await engine.create_execution(
        channel_id=test_channel.id,
        template_key="TEMPLATE_TOPIC_RESEARCH_ONLY",
    )
    await db_session.flush()

    assert len(execution.stages) == 1
    stage = execution.stages[0]

    started = await engine.start_execution(execution.id)
    assert started.status == WORKFLOW_STATUS_RUNNING

    # Complete the stage
    await engine.record_stage_completed(stage.id, {"discovered_topics": 5})

    assert execution.status == WORKFLOW_STATUS_COMPLETED
    assert execution.progress_percentage == 100
    assert execution.completed_at is not None
