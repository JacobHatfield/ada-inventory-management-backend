"""Domain tests for user profile management features."""

import pytest

from app.services import user_service


class TestGetUserProfile:
    """Tests for retrieving user profile data."""

    def test_get_user_profile_returns_all_fields(self, db, test_user):
        """Return complete user profile with all fields."""
        profile = user_service.get_user_profile(db, test_user.id)

        assert profile.id == test_user.id
        assert profile.email == test_user.email
        assert profile.full_name == test_user.full_name
        assert profile.is_active is True
        assert profile.created_at is not None
        assert profile.updated_at is not None

    def test_get_user_profile_not_found(self, db):
        """Return None when user does not exist."""
        profile = user_service.get_user_profile(db, 99999)
        assert profile is None


class TestUpdateUserProfile:
    """Tests for updating user profile information."""

    def test_update_user_profile_email_only(self, db, test_user):
        """Update only email field."""
        new_email = "newemail@example.com"
        updated = user_service.update_user_profile(db, test_user.id, email=new_email)

        assert updated.email == new_email
        assert updated.full_name == test_user.full_name

    def test_update_user_profile_full_name_only(self, db, test_user):
        """Update only full_name field."""
        new_name = "Updated Name"
        updated = user_service.update_user_profile(db, test_user.id, full_name=new_name)

        assert updated.full_name == new_name
        assert updated.email == test_user.email

    def test_update_user_profile_all_fields(self, db, test_user):
        """Update all profile fields at once."""
        updated = user_service.update_user_profile(
            db,
            test_user.id,
            email="new@example.com",
            full_name="New Name",
            profile_image_url="http://example.com/image.png",
        )

        assert updated.email == "new@example.com"
        assert updated.full_name == "New Name"
        assert updated.profile_image_url == "http://example.com/image.png"

    def test_update_user_profile_image_url(self, db, test_user):
        """Update profile image URL."""
        image_url = "https://example.com/avatar.jpg"
        updated = user_service.update_user_profile(
            db, test_user.id, profile_image_url=image_url
        )

        assert updated.profile_image_url == image_url

    def test_update_user_profile_email_already_taken(self, db, test_user, other_user):
        """Raise error when email is already taken by another user."""
        with pytest.raises(ValueError, match="already registered"):
            user_service.update_user_profile(db, test_user.id, email=other_user.email)

    def test_update_user_profile_partial_update(self, db, test_user):
        """Only update specified fields, leave others unchanged."""
        original_name = test_user.full_name
        updated = user_service.update_user_profile(
            db, test_user.id, email="newemail@example.com"
        )

        assert updated.email == "newemail@example.com"
        assert updated.full_name == original_name

    def test_update_user_profile_user_not_found(self, db):
        """Raise error when user does not exist."""
        with pytest.raises(ValueError, match="not found"):
            user_service.update_user_profile(db, 99999, email="test@example.com")


class TestValidateEmailUniqueness:
    """Tests for email uniqueness validation."""

    def test_validate_email_uniqueness_available(self, db):
        """Return True when email is not taken."""
        result = user_service.validate_email_uniqueness(db, "available@example.com", 1)
        assert result is True

    def test_validate_email_uniqueness_taken(self, db, test_user):
        """Return False when email is taken by another user."""
        result = user_service.validate_email_uniqueness(
            db, test_user.email, current_user_id=999
        )
        assert result is False

    def test_validate_email_uniqueness_allows_current_user_email(self, db, test_user):
        """Allow user to keep their current email."""
        result = user_service.validate_email_uniqueness(
            db, test_user.email, test_user.id
        )
        assert result is True


class TestProfileEdgeCases:
    """Tests for edge cases and data validation."""

    def test_update_profile_with_empty_strings(self, db, test_user):
        """Allow empty strings for optional fields."""
        updated = user_service.update_user_profile(
            db, test_user.id, full_name="", profile_image_url=""
        )

        assert updated.full_name == ""
        assert updated.profile_image_url == ""

    def test_update_profile_with_none_values(self, db, test_user):
        """None values leave fields unchanged."""
        original_name = test_user.full_name
        updated = user_service.update_user_profile(
            db, test_user.id, full_name=None, profile_image_url=None
        )

        assert updated.full_name == original_name
        assert updated.profile_image_url is None

    def test_update_profile_email_case_insensitive(self, db, test_user):
        """Email updates are case-insensitive for uniqueness check."""
        original_email = test_user.email
        # Try to update to same email with different case
        updated = user_service.update_user_profile(
            db, test_user.id, email=original_email.upper()
        )

        # Email should be updated to new case
        assert updated.email == original_email.upper()

    def test_update_profile_persists_changes(self, db, test_user):
        """Changes persist when fetching profile again."""
        new_name = "Persistent Name"
        user_service.update_user_profile(db, test_user.id, full_name=new_name)

        # Fetch fresh from DB
        refreshed = user_service.get_user_profile(db, test_user.id)
        assert refreshed.full_name == new_name

    def test_update_profile_long_url(self, db, test_user):
        """Handle very long profile image URLs."""
        long_url = "https://example.com/" + "a" * 500 + ".jpg"
        updated = user_service.update_user_profile(
            db, test_user.id, profile_image_url=long_url
        )

        assert updated.profile_image_url == long_url
