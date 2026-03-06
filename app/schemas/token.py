"""Token and authentication schemas for JWT handling."""
from typing import Optional
from pydantic import BaseModel, EmailStr


class Token(BaseModel):
    """Schema for JWT token response."""
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """Schema for decoded JWT token payload."""
    sub: Optional[int] = None  # subject (user_id)
    exp: Optional[int] = None  # expiration timestamp


class PasswordResetRequest(BaseModel):
    """Schema for requesting a password reset."""
    email: EmailStr


class PasswordReset(BaseModel):
    """Schema for completing password reset with token."""
    token: str
    new_password: str
