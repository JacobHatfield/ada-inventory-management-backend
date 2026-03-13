from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_active_user
from app.models.user import User
from app.schemas.user import ProfileResponse, ProfileUpdate
from app.services import user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me/profile", response_model=ProfileResponse)
def get_profile(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Return the current user's profile."""
    return current_user


@router.put("/me/profile", response_model=ProfileResponse)
def update_profile(
    profile_data: ProfileUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Update the current user's profile (email, full_name, profile_image_url)."""
    try:
        updated_user = user_service.update_user_profile(
            db,
            current_user.id,
            email=profile_data.email,
            full_name=profile_data.full_name,
            profile_image_url=profile_data.profile_image_url,
        )
        return updated_user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
