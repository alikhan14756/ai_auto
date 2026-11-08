"""Authentication request and response schemas."""

from typing import Optional, Dict, Any
from pydantic import BaseModel, EmailStr
from app.schemas.user import UserRead


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead
    expires_in: int = 86400
