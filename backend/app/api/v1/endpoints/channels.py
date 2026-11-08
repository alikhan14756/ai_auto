"""Channel and ChannelSettings management endpoints with tenant isolation."""

import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.models.channel import Channel, ChannelSettings
from app.schemas.channel import (
    ChannelCreate,
    ChannelUpdate,
    ChannelRead,
    ChannelSettingsRead,
    ChannelSettingsUpdate,
)
from app.api.deps import get_current_user, get_tenant_channel
from app.core.security import encrypt_token

router = APIRouter()


@router.get("", response_model=List[ChannelRead], summary="List channels for current user")
async def list_channels(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[Channel]:
    """Retrieve all YouTube channels owned by the authenticated user."""
    stmt = (
        select(Channel)
        .where(Channel.user_id == current_user.id)
        .options(selectinload(Channel.settings))
        .order_by(Channel.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("", response_model=ChannelRead, status_code=status.HTTP_201_CREATED, summary="Connect new channel")
async def create_channel(
    channel_in: ChannelCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Channel:
    """Connect a new YouTube channel with encrypted OAuth tokens."""
    # Check if channel is already connected
    stmt = select(Channel).where(Channel.youtube_channel_id == channel_in.youtube_channel_id)
    result = await db.execute(stmt)
    existing = result.scalars().first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A channel with this YouTube ID is already registered",
        )

    # Encrypt OAuth refresh token with AES-256-GCM
    encrypted_token = encrypt_token(channel_in.oauth_refresh_token)

    channel = Channel(
        user_id=current_user.id,
        youtube_channel_id=channel_in.youtube_channel_id,
        title=channel_in.title,
        description=channel_in.description,
        custom_url=channel_in.custom_url,
        thumbnail_url=channel_in.thumbnail_url,
        oauth_refresh_token_encrypted=encrypted_token,
        token_expires_at=channel_in.token_expires_at,
        is_active=True,
    )
    db.add(channel)
    await db.flush()

    # Create default settings
    settings = ChannelSettings(
        channel_id=channel.id,
        niche_keywords=[],
        default_privacy="unlisted",
        default_category_id="28",
        weekly_cadence_long=2,
        weekly_cadence_shorts=3,
        auto_publish_enabled=False,
        max_monthly_spend_usd=0.00,
        topic_retention_weights={},
    )
    db.add(settings)
    await db.commit()
    await db.refresh(channel)
    # Eager load settings
    stmt_loaded = select(Channel).where(Channel.id == channel.id).options(selectinload(Channel.settings))
    res_loaded = await db.execute(stmt_loaded)
    return res_loaded.scalars().first()


@router.get("/{channel_id}", response_model=ChannelRead, summary="Get channel details")
async def get_channel(
    channel: Channel = Depends(get_tenant_channel),
    db: AsyncSession = Depends(get_db),
) -> Channel:
    """Retrieve details of a single channel with tenant isolation verified."""
    stmt = select(Channel).where(Channel.id == channel.id).options(selectinload(Channel.settings))
    result = await db.execute(stmt)
    return result.scalars().first()


@router.patch("/{channel_id}", response_model=ChannelRead, summary="Update channel")
async def update_channel(
    update_data: ChannelUpdate,
    channel: Channel = Depends(get_tenant_channel),
    db: AsyncSession = Depends(get_db),
) -> Channel:
    """Update channel metadata."""
    if update_data.title is not None:
        channel.title = update_data.title
    if update_data.description is not None:
        channel.description = update_data.description
    if update_data.custom_url is not None:
        channel.custom_url = update_data.custom_url
    if update_data.thumbnail_url is not None:
        channel.thumbnail_url = update_data.thumbnail_url
    if update_data.is_active is not None:
        channel.is_active = update_data.is_active

    await db.commit()
    await db.refresh(channel)
    stmt = select(Channel).where(Channel.id == channel.id).options(selectinload(Channel.settings))
    res = await db.execute(stmt)
    return res.scalars().first()


@router.get("/{channel_id}/settings", response_model=ChannelSettingsRead, summary="Get channel settings")
async def get_channel_settings(
    channel: Channel = Depends(get_tenant_channel),
    db: AsyncSession = Depends(get_db),
) -> ChannelSettings:
    """Retrieve production settings for a channel."""
    stmt = select(ChannelSettings).where(ChannelSettings.channel_id == channel.id)
    result = await db.execute(stmt)
    settings = result.scalars().first()
    if not settings:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel settings not found")
    return settings


@router.patch("/{channel_id}/settings", response_model=ChannelSettingsRead, summary="Update channel settings")
async def update_channel_settings(
    update_in: ChannelSettingsUpdate,
    channel: Channel = Depends(get_tenant_channel),
    db: AsyncSession = Depends(get_db),
) -> ChannelSettings:
    """Update production settings for a channel."""
    stmt = select(ChannelSettings).where(ChannelSettings.channel_id == channel.id)
    result = await db.execute(stmt)
    settings = result.scalars().first()
    if not settings:
        settings = ChannelSettings(channel_id=channel.id)
        db.add(settings)

    if update_in.niche_keywords is not None:
        settings.niche_keywords = update_in.niche_keywords
    if update_in.default_privacy is not None:
        settings.default_privacy = update_in.default_privacy
    if update_in.default_category_id is not None:
        settings.default_category_id = update_in.default_category_id
    if update_in.weekly_cadence_long is not None:
        settings.weekly_cadence_long = update_in.weekly_cadence_long
    if update_in.weekly_cadence_shorts is not None:
        settings.weekly_cadence_shorts = update_in.weekly_cadence_shorts
    if update_in.auto_publish_enabled is not None:
        settings.auto_publish_enabled = update_in.auto_publish_enabled
    if update_in.max_monthly_spend_usd is not None:
        settings.max_monthly_spend_usd = update_in.max_monthly_spend_usd
    if update_in.topic_retention_weights is not None:
        settings.topic_retention_weights = update_in.topic_retention_weights

    await db.commit()
    await db.refresh(settings)
    return settings
