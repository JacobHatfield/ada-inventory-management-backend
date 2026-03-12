"""Authentication API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.database import get_db
from app.dependencies import get_current_active_user
from app.models.user import User
from app.schemas.token import Token
from app.schemas.user import (
    PasswordResetConfirm,
    PasswordResetRequest,
    PasswordResetResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)
from app.services import email_service
from app.services.auth_service import (
    authenticate_user,
    create_password_reset_token,
    get_user_by_email,
    register_user,
    reset_user_password,
    verify_reset_token,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
def register(
    user_data: UserCreate,
    db: Annotated[Session, Depends(get_db)],
):
    """Register a new user account."""
    user = register_user(db, user_data)
    return user


@router.post("/login", response_model=Token)
def login(
    credentials: UserLogin,
    db: Annotated[Session, Depends(get_db)],
):
    """Login with email and password to get access token."""
    # Authenticate user
    user = authenticate_user(db, credentials.email, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account",
        )

    # Create access token
    access_token = create_access_token(user_id=user.id)

    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserResponse)
def get_current_user_info(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Get current authenticated user information."""
    return current_user


@router.post("/forgot-password", response_model=PasswordResetResponse)
async def forgot_password(
    request: PasswordResetRequest,
    db: Annotated[Session, Depends(get_db)],
):
    """
    Request a password reset email.

    Always returns success even if email doesn't exist (security best practice).
    """
    # Check if user exists
    user = get_user_by_email(db, request.email)

    if user:
        # Create reset token
        reset_token = create_password_reset_token(db, user.id)

        # Send reset email
        email_sent = await email_service.send_password_reset_email(
            to_email=user.email, reset_token=reset_token.token
        )

        if not email_sent:
            # Log but don't expose to user
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Email service temporarily unavailable. Please try again later.",
            )

    # Always return success message (security: don't reveal if email exists)
    return PasswordResetResponse(
        message="If that email exists, a password reset link has been sent.",
        email=request.email,
    )


@router.post("/reset-password", response_model=dict)
async def reset_password(
    request: PasswordResetConfirm,
    db: Annotated[Session, Depends(get_db)],
):
    """
    Reset password using a valid reset token.
    """
    # Attempt to reset password
    user = reset_user_password(db, request.token, request.new_password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    # Send confirmation email
    await email_service.send_password_reset_confirmation_email(user.email)

    return {
        "message": "Password successfully reset. You can now log in with your new password."
    }


@router.post("/verify-reset-token", response_model=dict)
async def verify_reset_token_endpoint(
    token: str,
    db: Annotated[Session, Depends(get_db)],
):
    """
    Verify if a password reset token is valid (for frontend validation).
    """
    reset_token = verify_reset_token(db, token)

    if not reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    return {"valid": True, "message": "Token is valid"}
