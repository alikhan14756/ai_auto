"""Integration tests for YouTube Analytics REST API endpoints and multi-tenant isolation."""

import uuid
import datetime
import pytest
from app.models.user import User
from app.models.channel import Channel, ChannelSettings
from app.models.analytics import (
    ChannelAnalyticsSnapshot,
    VideoAnalyticsSnapshot,
    PerformanceRecommendation,
)
from app.services.youtube.constants import CONTENT_LONG_FORM, CONTENT_SHORTS
from tests.conftest import auth_headers_for


@pytest.mark.asyncio
async def test_analytics_overview_and_trends_api(client, test_user, test_channel, db_session):
    """Test GET /api/v1/analytics/overview and GET /api/v1/analytics/trends."""
    headers = auth_headers_for(test_user)

    # Seed channel daily snapshot
    now_dt = datetime.datetime.now(datetime.timezone.utc)
    snap = ChannelAnalyticsSnapshot(
        channel_id=test_channel.id,
        snapshot_date=now_dt,
        views=4500,
        watch_time_minutes=1800.0,
        average_view_duration_seconds=240.0,
        average_view_percentage=55.0,
        subscribers_gained=85,
        subscribers_lost=5,
        net_subscribers=80,
        likes=320,
        comments=45,
        shares=25,
        impressions=36000,
        click_through_rate=0.065,
    )
    db_session.add(snap)
    await db_session.commit()

    # 1. Overview endpoint
    ov_resp = client.get(f"/api/v1/analytics/overview?channel_id={test_channel.id}", headers=headers)
    assert ov_resp.status_code == 200
    ov_data = ov_resp.json()
    assert ov_data["total_views"] == 4500
    assert ov_data["total_subscribers"] == test_channel.subscriber_count
    assert ov_data["data_freshness"] == "FRESH"

    # 2. Trends endpoint
    tr_resp = client.get(f"/api/v1/analytics/trends?channel_id={test_channel.id}", headers=headers)
    assert tr_resp.status_code == 200
    tr_data = tr_resp.json()
    assert len(tr_data) == 1
    assert tr_data[0]["views"] == 4500


@pytest.mark.asyncio
async def test_analytics_videos_and_retention_api(client, test_user, test_channel, db_session):
    """Test GET /api/v1/analytics/videos and format filtering."""
    headers = auth_headers_for(test_user)

    now_dt = datetime.datetime.now(datetime.timezone.utc)
    v1 = VideoAnalyticsSnapshot(
        channel_id=test_channel.id,
        youtube_video_id="mock_vid_long_01",
        snapshot_date=now_dt,
        views=8000,
        watch_time_minutes=2500.0,
        average_view_duration_seconds=260.0,
        average_view_percentage=60.0,
        click_through_rate=0.075,
        retention_at_30s=0.72,
        content_type=CONTENT_LONG_FORM,
    )
    v2 = VideoAnalyticsSnapshot(
        channel_id=test_channel.id,
        youtube_video_id="mock_vid_shorts_01",
        snapshot_date=now_dt,
        views=15000,
        watch_time_minutes=150.0,
        average_view_duration_seconds=42.0,
        average_view_percentage=85.0,
        click_through_rate=0.088,
        retention_at_30s=0.84,
        content_type=CONTENT_SHORTS,
    )
    db_session.add_all([v1, v2])
    await db_session.commit()

    # Query all
    all_resp = client.get(f"/api/v1/analytics/videos?channel_id={test_channel.id}&content_type=ALL", headers=headers)
    assert all_resp.status_code == 200
    assert len(all_resp.json()) == 2

    # Query shorts only
    sh_resp = client.get(f"/api/v1/analytics/videos?channel_id={test_channel.id}&content_type=SHORTS", headers=headers)
    assert sh_resp.status_code == 200
    sh_data = sh_resp.json()
    assert len(sh_data) == 1
    assert sh_data[0]["youtube_video_id"] == "mock_vid_shorts_01"

    # Query retention endpoint
    ret_resp = client.get(f"/api/v1/analytics/videos/mock_vid_long_01/retention?channel_id={test_channel.id}", headers=headers)
    assert ret_resp.status_code == 200
    assert "relative_retention_points" in ret_resp.json()


@pytest.mark.asyncio
async def test_analytics_sync_trigger_and_status(client, test_user, test_channel):
    """Test POST /api/v1/analytics/sync and GET /api/v1/analytics/sync/status."""
    headers = auth_headers_for(test_user)

    sync_resp = client.post(
        "/api/v1/analytics/sync",
        json={"channel_id": str(test_channel.id), "sync_type": "FULL"},
        headers=headers,
    )
    assert sync_resp.status_code == 200
    assert sync_resp.json()["status"] == "QUEUED"

    stat_resp = client.get(f"/api/v1/analytics/sync/status?channel_id={test_channel.id}", headers=headers)
    assert stat_resp.status_code == 200
    assert stat_resp.json()["active_jobs_count"] >= 1


@pytest.mark.asyncio
async def test_analytics_recommendations_and_acceptance(client, test_user, test_channel, db_session):
    """Test GET /api/v1/analytics/recommendations and POST /api/v1/analytics/recommendations/{id}/accept."""
    headers = auth_headers_for(test_user)

    rec = PerformanceRecommendation(
        channel_id=test_channel.id,
        recommendation_type="TOPIC_OPPORTUNITY",
        title="Expand Practical Coding Tutorials",
        explanation="Viewer watch time showed 24% higher engagement.",
        supporting_metrics={"watch_time_multiplier": 1.24},
        confidence_level="HIGH",
        status="NEW",
    )
    db_session.add(rec)
    await db_session.commit()
    await db_session.refresh(rec)

    # Fetch recommendations
    rec_resp = client.get(f"/api/v1/analytics/recommendations?channel_id={test_channel.id}", headers=headers)
    assert rec_resp.status_code == 200
    assert len(rec_resp.json()) >= 1

    # Accept recommendation
    acc_resp = client.post(f"/api/v1/analytics/recommendations/{rec.id}/accept", headers=headers)
    assert acc_resp.status_code == 200
    assert acc_resp.json()["new_status"] == "ACCEPTED"


@pytest.mark.asyncio
async def test_analytics_cross_tenant_isolation(client, test_user, db_session):
    """Verify Creator A cannot query or trigger sync for Creator B's channel."""
    # Create tenant B
    other_user = User(
        id=uuid.uuid4(),
        supabase_user_id="sub_other_user_tenant_b",
        email="tenant_b@example.com",
        full_name="Tenant B Creator",
        role="CREATOR",
    )
    other_channel = Channel(
        id=uuid.uuid4(),
        user_id=other_user.id,
        youtube_channel_id="UC_tenant_b_secret_channel",
        title="Tenant B Studio",
        subscriber_count=1000,
        oauth_refresh_token_encrypted="encrypted_b",
        is_active=True,
    )
    db_session.add_all([other_user, other_channel])
    await db_session.commit()

    # User A tries to view Channel B's overview
    headers_a = auth_headers_for(test_user)
    resp = client.get(f"/api/v1/analytics/overview?channel_id={other_channel.id}", headers=headers_a)
    assert resp.status_code == 403
    assert "Unauthorized" in resp.json()["detail"]

    # User A tries to accept Channel B's recommendation (BOLA defense)
    rec_b = PerformanceRecommendation(
        channel_id=other_channel.id,
        recommendation_type="TOPIC_OPPORTUNITY",
        title="Tenant B Target",
        explanation="Secret",
        status="NEW",
    )
    db_session.add(rec_b)
    await db_session.commit()
    await db_session.refresh(rec_b)

    bola_resp = client.post(f"/api/v1/analytics/recommendations/{rec_b.id}/accept", headers=headers_a)
    assert bola_resp.status_code == 403
    assert "Unauthorized" in bola_resp.json()["detail"]
