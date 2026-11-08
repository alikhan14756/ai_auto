"""Tests for Automation Policy Engine, execution boundaries, and non-bypassable gates."""

import pytest
from app.models.project import VideoProject
from app.models.qa import QARun
from app.models.workflow import (
    AUTOMATION_LEVEL_MANUAL,
    AUTOMATION_LEVEL_ASSISTED,
    AUTOMATION_LEVEL_CONTROLLED,
    AUTOMATION_LEVEL_SCHEDULED,
    WORKFLOW_STATUS_RUNNING,
)
from app.services.orchestration.policy_engine import (
    PolicyEngine,
    PolicyViolationError,
)
from app.services.orchestration.workflow_engine import WorkflowEngine


@pytest.mark.asyncio
async def test_policy_levels_and_approval_matrix(db_session, test_channel):
    """Verify approval requirement calculations across Automation Levels 0 through 3."""
    policy_engine = PolicyEngine(db_session)
    policy = await policy_engine.get_or_create_policy(test_channel.id)

    # Level 0: Manual - all stages require approval
    policy.automation_level = AUTOMATION_LEVEL_MANUAL
    assert await policy_engine.requires_approval(test_channel.id, "stage_render", False) is True

    # Level 1: Assisted (Default) - non-checkpoint stages execute automatically
    policy.automation_level = AUTOMATION_LEVEL_ASSISTED
    policy.require_topic_approval = True
    assert await policy_engine.requires_approval(test_channel.id, "stage_topic", False) is True
    assert await policy_engine.requires_approval(test_channel.id, "stage_narration", False) is False

    # Level 2: Controlled - halts only for QA and publishing
    policy.automation_level = AUTOMATION_LEVEL_CONTROLLED
    assert await policy_engine.requires_approval(test_channel.id, "stage_script", False) is False
    assert await policy_engine.requires_approval(test_channel.id, "stage_qa", False) is True
    assert await policy_engine.requires_approval(test_channel.id, "stage_publishing", False) is True

    # Level 3: Scheduled - publishing requires policy authorization
    policy.automation_level = AUTOMATION_LEVEL_SCHEDULED
    policy.require_publish_authorization = True
    assert await policy_engine.requires_approval(test_channel.id, "stage_publishing", False) is True


@pytest.mark.asyncio
async def test_non_bypassable_qa_veto_gate(db_session, test_channel):
    """Verify that publication authorization strictly rejects unreviewed or vetoed projects."""
    policy_engine = PolicyEngine(db_session)

    # Setup channel with YouTube credentials
    test_channel.oauth_refresh_token_encrypted = "mock_encrypted_refresh_token"
    await db_session.flush()

    project = VideoProject(
        channel_id=test_channel.id,
        title="Unreviewed Video Project",
        state="SCRIPT_APPROVED",
    )
    db_session.add(project)
    await db_session.flush()

    # 1. Unreviewed project (no QA report) must be rejected
    can_pub, reason = await policy_engine.validate_publishing_authorization(test_channel.id, project.id)
    assert can_pub is False
    assert "M11 Quality Assurance evaluation" in reason

    # 2. Vetoed / failed QA report (< 70 score) must be rejected
    failed_report = QARun(
        project_id=project.id,
        overall_score=55.0,
        veto_decision="REJECTED",
    )
    db_session.add(failed_report)
    await db_session.flush()

    can_pub_vetoed, reason_vetoed = await policy_engine.validate_publishing_authorization(test_channel.id, project.id)
    assert can_pub_vetoed is False
    assert "vetoed by M11 QA Gate" in reason_vetoed

    # 3. Approved QA report (>= 70 score) satisfies QA gate
    failed_report.overall_score = 92.0
    failed_report.veto_decision = "APPROVED"
    await db_session.flush()

    can_pub_ok, reason_ok = await policy_engine.validate_publishing_authorization(test_channel.id, project.id)
    assert can_pub_ok is True
    assert reason_ok is None


@pytest.mark.asyncio
async def test_unauthorized_publishing_credentials_missing(db_session, test_channel):
    """Verify that publication authorization fails if YouTube OAuth tokens are missing."""
    policy_engine = PolicyEngine(db_session)
    test_channel.oauth_refresh_token_encrypted = ""
    await db_session.flush()

    can_pub, reason = await policy_engine.validate_publishing_authorization(test_channel.id, None)
    assert can_pub is False
    assert "YouTube OAuth credentials not connected" in reason


@pytest.mark.asyncio
async def test_concurrency_and_weekly_limits_enforced(db_session, test_channel):
    """Verify max concurrent workflows limit is enforced server-side."""
    policy_engine = PolicyEngine(db_session)
    policy = await policy_engine.get_or_create_policy(test_channel.id)
    policy.max_concurrent_workflows = 1
    policy.require_topic_approval = False
    await db_session.flush()

    engine = WorkflowEngine(db_session)

    # 1. Start first execution
    exec_1 = await engine.create_execution(channel_id=test_channel.id, template_key="TEMPLATE_TOPIC_RESEARCH_ONLY")
    await engine.start_execution(exec_1.id)
    assert exec_1.status == WORKFLOW_STATUS_RUNNING

    # 2. Starting second execution must be rejected due to concurrency limit
    can_start, reason = await policy_engine.can_start_workflow(test_channel.id, "TEMPLATE_TOPIC_RESEARCH_ONLY", "LONG_FORM")
    assert can_start is False
    assert "Maximum concurrent workflows reached" in reason

    with pytest.raises(PolicyViolationError):
        exec_2 = await engine.create_execution(channel_id=test_channel.id, template_key="TEMPLATE_TOPIC_RESEARCH_ONLY")
        await engine.start_execution(exec_2.id)
