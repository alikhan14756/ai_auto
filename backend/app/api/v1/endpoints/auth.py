"""Authentication API endpoints."""

import uuid
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.core.config import settings
from app.core.logging import logger
from app.core.security import create_access_token, ROLE_CREATOR
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserRead
from app.api.deps import get_current_user

router = APIRouter()


@router.get("/me", response_model=UserRead, summary="Get current authenticated user")
async def get_me(current_user: User = Depends(get_current_user)) -> User:
    """Retrieve profile of the currently authenticated user."""
    return current_user


@router.post("/register", response_model=TokenResponse, summary="Register new user")
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Register a new user account with Supabase Auth or local bridge."""
    # Check if user already exists
    stmt = select(User).where(User.email == request.email)
    result = await db.execute(stmt)
    existing_user = result.scalars().first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists",
        )

    supabase_user_id = f"usr_{uuid.uuid4().hex[:24]}"

    # In production with live Supabase configured, call Supabase Auth API
    if settings.SUPABASE_URL and settings.SUPABASE_ANON_KEY:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(
                    f"{settings.SUPABASE_URL}/auth/v1/signup",
                    headers={"apikey": settings.SUPABASE_ANON_KEY},
                    json={"email": request.email, "password": request.password},
                )
                if res.status_code in [200, 201]:
                    data = res.json()
                    supabase_user_id = data.get("user", {}).get("id", supabase_user_id)
        except Exception as exc:
            logger.warning(f"Supabase remote signup failed, using local registration: {exc}")

    # Provision user record
    new_user = User(
        supabase_user_id=supabase_user_id,
        email=request.email,
        full_name=request.full_name,
        role=ROLE_CREATOR,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    token = create_access_token({
        "sub": new_user.supabase_user_id,
        "email": new_user.email,
        "role": new_user.role,
        "user_metadata": {"full_name": new_user.full_name},
    })

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserRead.model_validate(new_user),
        expires_in=86400,
    )


@router.post("/login", response_model=TokenResponse, summary="Log in user")
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Log in an existing user and issue a JWT access token."""
    stmt = select(User).where(User.email == request.email)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # In production with live Supabase, verify with Supabase Auth
    if settings.SUPABASE_URL and settings.SUPABASE_ANON_KEY:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(
                    f"{settings.SUPABASE_URL}/auth/v1/token?grant_type=password",
                    headers={"apikey": settings.SUPABASE_ANON_KEY},
                    json={"email": request.email, "password": request.password},
                )
                if res.status_code == 200:
                    data = res.json()
                    token = data.get("access_token")
                    return TokenResponse(
                        access_token=token,
                        token_type="bearer",
                        user=UserRead.model_validate(user),
                        expires_in=data.get("expires_in", 86400),
                    )
        except Exception as exc:
            logger.warning(f"Supabase remote login failed, falling back to local JWT: {exc}")

    token = create_access_token({
        "sub": user.supabase_user_id,
        "email": user.email,
        "role": user.role,
        "user_metadata": {"full_name": user.full_name},
    })

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserRead.model_validate(user),
        expires_in=86400,
    )
