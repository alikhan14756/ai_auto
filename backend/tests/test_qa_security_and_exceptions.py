"""Security, RBAC, and Exception Policy tests for the QA subsystem."""

import uuid
import pytest
import pytest_asyncio
from tests.conftest import auth_headers_for, TestingSessionLocal
from app.models.user import User
from app.models.channel import Channel
from app.models.project import VideoProject
from app.models.qa import QARun, QAFinding
from app.services.qa.constants import QASeverity, QAFindingStatus


@pytest_asyncio.fixture
async def admin_user():
    async with TestingSessionLocal() as session:
        user = User(
            id=uuid.uuid4(),
            email=f"admin_{uuid.uuid4().hex[:8]}@alibuild.site",
            supabase_user_id=f"sub_admin_{uuid.uuid4().hex[:8]}",
            role="ADMIN",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest_asyncio.fixture
async def other_user():
    async with TestingSessionLocal() as session:
        user = User(
            id=uuid.uuid4(),
            email=f"other_{uuid.uuid4().hex[:8]}@alibuild.site",
            supabase_user_id=f"sub_other_{uuid.uuid4().hex[:8]}",
            role="CREATOR",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest_asyncio.fixture
async def other_channel(other_user):
    async with TestingSessionLocal() as session:
        channel = Channel(
            id=uuid.uuid4(),
            user_id=other_user.id,
            title="Other Channel",
            youtube_channel_id=f"UC_other_{uuid.uuid4().hex[:8]}",
            oauth_refresh_token_encrypted="mock_enc_tok",
        )
        session.add(channel)
        await session.commit()
        await session.refresh(channel)
        return channel


@pytest.mark.asyncio
async def test_admin_can_authorize_exception_for_high_severity(client, test_user, test_channel, admin_user):
    """Verify that an ADMIN or SUPER_ADMIN can authorize an exception for a HIGH severity finding."""
    headers_creator = auth_headers_for(test_user)
    headers_admin = auth_headers_for(admin_user)

    # 1. Create project
    p_resp = client.post(
        "/api/v1/projects",
        json={"channel_id": str(test_channel.id), "title": "Exception Test Project", "format": "LONG_FORM"},
        headers=headers_creator,
    )
    assert p_resp.status_code == 201
    project_id = p_resp.json()["id"]

    # 2. Add an explicit HIGH severity finding
    async with TestingSessionLocal() as session:
        qa_run = QARun(
            id=uuid.uuid4(),
            project_id=uuid.UUID(project_id),
            status="COMPLETED",
            overall_score=85.0,
            veto_decision="BLOCKED",
            can_publish=False,
        )
        finding = QAFinding(
            id=uuid.uuid4(),
            qa_run_id=qa_run.id,
            category="FACTUAL_ACCURACY",
            severity=QASeverity.HIGH.value,
            status=QAFindingStatus.OPEN.value,
            affected_artifact="script_claim",
            title="High Severity Claim Notice",
            explanation="Unverified research citation",
            evidence={},
            recommended_correction="Attach citation",
        )
        qa_run.findings = [finding]
        session.add(qa_run)
        await session.commit()
        finding_id = str(finding.id)

    # 3. Admin authorizes exception
    exc_resp = client.post(
        f"/api/v1/qa/findings/{finding_id}/exception",
        json={"reason": "Approved editorial exception with historical citation backing."},
        headers=headers_admin,
    )
    assert exc_resp.status_code == 200
    assert exc_resp.json()["finding_id"] == finding_id


@pytest.mark.asyncio
async def test_creator_cannot_authorize_exception(client, test_user, test_channel):
    """Verify that a CREATOR role is rejected with 403 when trying to authorize an exception."""
    headers = auth_headers_for(test_user)  # role is CREATOR

    # Create project & finding
    p_resp = client.post(
        "/api/v1/projects",
        json={"channel_id": str(test_channel.id), "title": "Creator Rejection Test", "format": "LONG_FORM"},
        headers=headers,
    )
    project_id = p_resp.json()["id"]

    async with TestingSessionLocal() as session:
        qa_run = QARun(
            id=uuid.uuid4(),
            project_id=uuid.UUID(project_id),
            status="COMPLETED",
            overall_score=85.0,
            veto_decision="BLOCKED",
            can_publish=False,
        )
        finding = QAFinding(
            id=uuid.uuid4(),
            qa_run_id=qa_run.id,
            category="FACTUAL_ACCURACY",
            severity=QASeverity.HIGH.value,
            status=QAFindingStatus.OPEN.value,
            affected_artifact="script_claim",
            title="High Severity Finding",
            explanation="Test",
            evidence={},
            recommended_correction="Fix it",
        )
        qa_run.findings = [finding]
        session.add(qa_run)
        await session.commit()
        finding_id = str(finding.id)

    # Creator attempts exception
    exc_resp = client.post(
        f"/api/v1/qa/findings/{finding_id}/exception",
        json={"reason": "I am self-approving this defect."},
        headers=headers,
    )
    assert exc_resp.status_code == 403
    assert "Only administrators" in exc_resp.json()["detail"]


@pytest.mark.asyncio
async def test_critical_finding_cannot_be_overridden(client, test_user, test_channel, admin_user):
    """Verify that CRITICAL severity findings represent hard blockers and CANNOT be overridden by anyone."""
    headers_admin = auth_headers_for(admin_user)

    p_resp = client.post(
        "/api/v1/projects",
        json={"channel_id": str(test_channel.id), "title": "Critical Veto Test", "format": "LONG_FORM"},
        headers=auth_headers_for(test_user),
    )
    project_id = p_resp.json()["id"]

    async with TestingSessionLocal() as session:
        qa_run = QARun(
            id=uuid.uuid4(),
            project_id=uuid.UUID(project_id),
            status="COMPLETED",
            overall_score=85.0,
            veto_decision="BLOCKED",
            can_publish=False,
        )
        finding = QAFinding(
            id=uuid.uuid4(),
            qa_run_id=qa_run.id,
            category="SECURITY_PRIVACY",
            severity=QASeverity.CRITICAL.value,
            status=QAFindingStatus.OPEN.value,
            affected_artifact="script",
            title="CRITICAL: Live API Key Leaked",
            explanation="Exposed secret token in video narration",
            evidence={},
            recommended_correction="Revoke key",
        )
        qa_run.findings = [finding]
        session.add(qa_run)
        await session.commit()
        finding_id = str(finding.id)

    # Admin attempts to override CRITICAL finding
    exc_resp = client.post(
        f"/api/v1/qa/findings/{finding_id}/exception",
        json={"reason": "Trying to bypass critical leak blocker."},
        headers=headers_admin,
    )
    assert exc_resp.status_code == 400
    assert "CRITICAL severity findings represent hard blockers and cannot be overridden" in exc_resp.json()["detail"]


@pytest.mark.asyncio
async def test_multi_tenant_isolation_qa(client, test_user, test_channel, other_user, other_channel):
    """Verify that User B cannot view or trigger QA on Channel A's project."""
    headers_a = auth_headers_for(test_user)
    headers_b = auth_headers_for(other_user)

    # User A creates project and QA run
    p_resp = client.post(
        "/api/v1/projects",
        json={"channel_id": str(test_channel.id), "title": "Tenant A Project", "format": "LONG_FORM"},
        headers=headers_a,
    )
    project_a_id = p_resp.json()["id"]

    run_resp = client.post(
        "/api/v1/qa/runs",
        json={"project_id": project_a_id, "run_async": False},
        headers=headers_a,
    )
    run_a_id = run_resp.json()["id"]

    # User B attempts to access User A's QA run
    b_get_resp = client.get(f"/api/v1/qa/runs/{run_a_id}", headers=headers_b)
    assert b_get_resp.status_code == 403

    # User B attempts to trigger QA run on User A's project
    b_trig_resp = client.post(
        "/api/v1/qa/runs",
        json={"project_id": project_a_id, "run_async": False},
        headers=headers_b,
    )
    assert b_trig_resp.status_code == 403


@pytest.mark.asyncio
async def test_cross_tenant_package_id_rejected(client, test_user, test_channel, other_user, other_channel):
    """Verify that a user cannot reference a PublicationPackage belonging to another project (IDOR protection)."""
    headers_a = auth_headers_for(test_user)
    headers_b = auth_headers_for(other_user)

    # 1. User A creates project A and assembles package A
    p_a = client.post(
        "/api/v1/projects",
        json={"channel_id": str(test_channel.id), "title": "Project A", "format": "LONG_FORM"},
        headers=headers_a,
    )
    proj_a_id = p_a.json()["id"]

    pkg_a = client.post(
        "/api/v1/publication-packages",
        json={"project_id": proj_a_id},
        headers=headers_a,
    )
    assert pkg_a.status_code == 201
    pkg_a_id = pkg_a.json()["id"]

    # 2. User B creates project B
    p_b = client.post(
        "/api/v1/projects",
        json={"channel_id": str(other_channel.id), "title": "Project B", "format": "LONG_FORM"},
        headers=headers_b,
    )
    proj_b_id = p_b.json()["id"]

    # 3. User B attempts to run QA on Project B while supplying User A's package_id
    idor_resp = client.post(
        "/api/v1/qa/runs",
        json={
            "project_id": proj_b_id,
            "publication_package_id": pkg_a_id,
            "run_async": False,
        },
        headers=headers_b,
    )
    assert idor_resp.status_code == 400
    assert "does not belong to project" in idor_resp.json()["detail"]
