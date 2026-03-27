"""Authentication service for user registration and login."""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.password_reset import PasswordResetToken
from app.models.user import User
from app.schemas.user import UserCreate


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get a user by email address."""
    return db.query(User).filter(User.email == email).first()


def register_user(db: Session, user_data: UserCreate) -> User:
    """Register a new user with hashed password."""
    # Check if user already exists
    existing_user = get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Hash the password
    hashed_password = hash_password(user_data.password)

    # Create new user
    db_user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """Authenticate a user with email and password."""
    user = get_user_by_email(db, email)
    if not user:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    return user


def generate_reset_token() -> str:
    """Generate a secure random token for password reset."""
    return secrets.token_urlsafe(32)


def create_password_reset_token(db: Session, user_id: int) -> PasswordResetToken:
    """Create a password reset token for a user."""
    # Invalidate any existing unused tokens for this user
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user_id,
        PasswordResetToken.is_used == False,  # noqa: E712
    ).update({"is_used": True})

    # Generate new token
    token = generate_reset_token()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)  # 1 hour expiry

    reset_token = PasswordResetToken(
        token=token, user_id=user_id, expires_at=expires_at
    )

    db.add(reset_token)
    db.commit()
    db.refresh(reset_token)

    return reset_token


def verify_reset_token(db: Session, token: str) -> Optional[PasswordResetToken]:
    """Verify a password reset token."""
    reset_token = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.token == token,
            PasswordResetToken.is_used == False,  # noqa: E712
        )
        .first()
    )

    if not reset_token:
        return None

    # Check if token is expired
    # Handle both naive and aware datetimes (SQLite stores as naive)
    now = datetime.now(timezone.utc)
    expires_at = reset_token.expires_at
    if expires_at.tzinfo is None:
        now = now.replace(tzinfo=None)

    if expires_at < now:
        return None

    return reset_token


def reset_user_password(db: Session, token: str, new_password: str) -> Optional[User]:
    """Reset user password using a valid reset token."""
    # Verify token
    reset_token = verify_reset_token(db, token)
    if not reset_token:
        return None

    # Get user
    user = db.query(User).filter(User.id == reset_token.user_id).first()
    if not user:
        return None

    # Update password
    user.hashed_password = hash_password(new_password)

    # Mark token as used
    reset_token.is_used = True

    db.commit()
    db.refresh(user)

    return user
