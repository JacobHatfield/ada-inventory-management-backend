"""Dependency injection functions for FastAPI endpoints."""

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import credentials_exception, inactive_user_exception
from app.core.security import decode_access_token
from app.database import get_db
from app.models.user import User

# HTTP Bearer token scheme for Authorization header
# Set auto_error=False so we can manually raise 401 (credentials_exception)
# instead of FastAPI's default 403 for missing credentials.
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Get the current authenticated user from JWT token."""
    if credentials is None:
        raise credentials_exception

    token = credentials.credentials

    # Decode and verify token
    token_data = decode_access_token(token)
    if token_data is None or token_data.sub is None:
        raise credentials_exception

    # Get user from database
    user = db.query(User).filter(User.id == token_data.sub).first()
    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Get the current authenticated user and verify they are active."""
    if not current_user.is_active:
        raise inactive_user_exception

    return current_user
