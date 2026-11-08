"""User profile and account management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserRead, UserUpdate
from app.api.deps import get_current_user
from app.core.security import ROLE_SUPER_ADMIN

router = APIRouter()


@router.get("/me", response_model=UserRead, summary="Get current user profile")
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
) -> User:
    """Retrieve the current user profile."""
    return current_user


@router.patch("/me", response_model=UserRead, summary="Update current user profile")
async def update_current_user_profile(
    update_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Update profile information for the current user."""
    if update_data.full_name is not None:
        current_user.full_name = update_data.full_name

    # Only SUPER_ADMIN can alter roles
    if update_data.role is not None:
        if current_user.role != ROLE_SUPER_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only super administrators can alter user roles",
            )
        current_user.role = update_data.role

    await db.commit()
    await db.refresh(current_user)
    return current_user
