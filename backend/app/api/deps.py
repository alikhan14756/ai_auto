"""API Dependencies: Database Session, Authentication, RBAC, and Tenant Isolation."""

import uuid
from typing import AsyncGenerator, Callable, List
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.models.channel import Channel
from app.core.security import (
    verify_supabase_jwt,
    ROLE_SUPER_ADMIN,
    ROLE_ADMIN,
    ROLE_CREATOR,
)
from app.core.logging import logger

# HTTP Bearer scheme
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    auth: HTTPAuthorizationCredentials = Security(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Validate Bearer JWT token from Supabase Auth and return authenticated User record.
    Automatically provisions new user record on first valid authenticated request.
    """
    if not auth or not auth.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = verify_supabase_jwt(auth.credentials)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        )

    supabase_user_id = payload.get("sub")
    email = payload.get("email")

    if not supabase_user_id or not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token: missing sub or email claims",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Query existing user
    stmt = select(User).where(User.supabase_user_id == supabase_user_id)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        # Check by email in case created beforehand
        stmt_email = select(User).where(User.email == email)
        result_email = await db.execute(stmt_email)
        user = result_email.scalars().first()

        if user:
            # Link existing email to supabase_user_id
            user.supabase_user_id = supabase_user_id
            await db.commit()
            await db.refresh(user)
        else:
            # Auto-provision new User
            user_meta = payload.get("user_metadata", {}) or {}
            full_name = user_meta.get("full_name") or user_meta.get("name")
            user = User(
                supabase_user_id=supabase_user_id,
                email=email,
                full_name=full_name,
                role=ROLE_CREATOR,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            logger.info(f"Auto-provisioned new user: {user.email} (id: {user.id})")

    return user


get_current_active_user = get_current_user


def require_roles(*allowed_roles: str) -> Callable:
    """Dependency factory enforcing Role-Based Access Control (RBAC)."""

    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required role: {', '.join(allowed_roles)}",
            )
        return current_user

    return role_checker


async def get_tenant_channel(
    channel_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Channel:
    """Retrieve channel ensuring strict multi-tenant isolation.
    Returns 404 if channel does not exist or belongs to another user (unless SUPER_ADMIN).
    """
    stmt = select(Channel).where(Channel.id == channel_id)
    result = await db.execute(stmt)
    channel = result.scalars().first()

    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel workspace not found",
        )

    # Multi-tenant ownership verification
    if channel.user_id != current_user.id and current_user.role != ROLE_SUPER_ADMIN:
        # Return 404 to avoid information leakage of channel existence
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel workspace not found",
        )

    return channel
