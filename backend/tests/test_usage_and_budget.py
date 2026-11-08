"""Unit and integration tests for Usage Tracking and Budget Guardrails."""

import pytest
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.channel import Channel, ChannelSettings
from app.models.user import User
from app.providers.ai.base import AIBudgetExceededError
from app.services.usage import UsageTrackingService


@pytest.mark.asyncio
async def test_usage_recording_and_budget_guardrails(db_session: AsyncSession):
    # Setup test user and channel
    user = User(
        supabase_user_id=f"test-sub-{uuid4()}",
        email=f"creator-{uuid4()}@example.com",
        full_name="Muhammad Ali",
    )
    db_session.add(user)
    await db_session.flush()

    channel = Channel(
        user_id=user.id,
        youtube_channel_id=f"UC_{uuid4().hex[:16]}",
        title="Ali Tech Engineering",
        oauth_refresh_token_encrypted="encrypted-test-token",
    )
    db_session.add(channel)
    await db_session.flush()

    settings = ChannelSettings(
        channel_id=channel.id,
        max_monthly_spend_usd=10.00,
        niche_keywords=["AI Agents", "Databases"],
    )
    db_session.add(settings)
    await db_session.commit()

    # Initial spend should be 0.00
    spend = await UsageTrackingService.get_current_month_spend(channel.id, db_session)
    assert spend == 0.00

    # Budget check with $1.00 estimated cost should pass
    await UsageTrackingService.check_budget_guardrail(
        channel_id=channel.id,
        db=db_session,
        estimated_additional_cost=1.00,
    )

    # Record usage of $4.50
    await UsageTrackingService.record_usage(
        channel_id=channel.id,
        provider_name="GEMINI",
        model_name="gemini-1.5-flash",
        input_tokens=1000,
        output_tokens=500,
        cost_usd=4.50,
        db=db_session,
    )

    # Record second usage of $5.00
    await UsageTrackingService.record_usage(
        channel_id=channel.id,
        provider_name="GEMINI",
        model_name="gemini-1.5-pro",
        input_tokens=5000,
        output_tokens=2000,
        cost_usd=5.00,
        db=db_session,
    )

    # Total spend is now $9.50
    spend = await UsageTrackingService.get_current_month_spend(channel.id, db_session)
    assert spend == 9.50

    # Next call with estimated cost $1.00 would bring total to $10.50 (> $10.00 max spend)
    with pytest.raises(AIBudgetExceededError) as exc_info:
        await UsageTrackingService.check_budget_guardrail(
            channel_id=channel.id,
            db=db_session,
            estimated_additional_cost=1.00,
        )
    assert "spending limit ($10.00) reached or exceeded" in str(exc_info.value)

    # Check summary aggregation
    summary = await UsageTrackingService.get_channel_usage_summary(channel.id, db_session)
    assert summary["current_month_spend_usd"] == 9.50
    assert summary["max_monthly_spend_usd"] == 10.00
    assert summary["total_requests"] == 2
    assert summary["current_month_input_tokens"] == 6000
    assert summary["current_month_output_tokens"] == 2500
    assert len(summary["breakdown_by_model"]) == 2


@pytest.mark.asyncio
async def test_zero_dollar_budget_guardrail(db_session: AsyncSession):
    """$0.00 budget (Free Tier) must block any paid spend strictly."""
    user = User(
        supabase_user_id=f"test-sub-{uuid4()}",
        email=f"free-{uuid4()}@example.com",
    )
    db_session.add(user)
    await db_session.flush()

    channel = Channel(
        user_id=user.id,
        youtube_channel_id=f"UC_{uuid4().hex[:16]}",
        title="Zero Budget Channel",
        oauth_refresh_token_encrypted="encrypted-test-token",
    )
    db_session.add(channel)
    await db_session.flush()

    settings = ChannelSettings(
        channel_id=channel.id,
        max_monthly_spend_usd=0.00,  # Default hard stop
    )
    db_session.add(settings)
    await db_session.commit()

    # $0.00 estimated cost allowed
    await UsageTrackingService.check_budget_guardrail(
        channel_id=channel.id,
        db=db_session,
        estimated_additional_cost=0.00,
    )

    # Any positive spend estimation must be rejected immediately
    with pytest.raises(AIBudgetExceededError) as exc:
        await UsageTrackingService.check_budget_guardrail(
            channel_id=channel.id,
            db=db_session,
            estimated_additional_cost=0.01,
        )
    assert "Channel monthly spending cap is $0.00" in str(exc.value)
