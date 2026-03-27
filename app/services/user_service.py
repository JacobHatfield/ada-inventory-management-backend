from sqlalchemy.orm import Session

from app.models.user import User


def get_user_profile(db: Session, user_id: int) -> User:
    """Get user profile by ID."""
    return db.query(User).filter(User.id == user_id).first()


def validate_email_uniqueness(db: Session, email: str, current_user_id: int) -> bool:
    """Check if email is unique."""
    existing_user = db.query(User).filter(User.email == email).first()

    if existing_user is None:
        return True

    # Allow current user to keep their email
    if existing_user.id == current_user_id:
        return True

    return False


def update_user_profile(
    db: Session,
    user_id: int,
    email: str = None,
    full_name: str = None,
    profile_image_url: str = None,
) -> User:
    """Update user profile."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError(f"User {user_id} not found")

    # Validate email uniqueness if email is being changed
    if email and email != user.email:
        if not validate_email_uniqueness(db, email, user_id):
            raise ValueError(f"Email {email} is already registered")
        user.email = email

    # Update optional fields if provided
    if full_name is not None:
        user.full_name = full_name

    if profile_image_url is not None:
        user.profile_image_url = profile_image_url

    db.commit()
    db.refresh(user)
    return user
