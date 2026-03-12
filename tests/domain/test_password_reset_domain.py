"""Password reset domain logic tests."""

from datetime import datetime, timedelta, timezone


from app.core.security import verify_password
from app.models.password_reset import PasswordResetToken
from app.models.user import User
from app.services.auth_service import (
    create_password_reset_token,
    generate_reset_token,
    reset_user_password,
    verify_reset_token,
)


class TestGenerateResetToken:
    """Test reset token generation."""

    def test_generate_reset_token_creates_string(self):
        """Test that generate_reset_token returns a string."""
        token = generate_reset_token()
        assert isinstance(token, str)
        assert len(token) > 0

    def test_generate_reset_token_creates_unique_tokens(self):
        """Test that each call generates a unique token."""
        tokens = [generate_reset_token() for _ in range(100)]
        # All tokens should be unique
        assert len(set(tokens)) == 100

    def test_generate_reset_token_is_url_safe(self):
        """Test that generated tokens are URL-safe."""
        token = generate_reset_token()
        # URL-safe tokens should not contain special characters
        assert "/" not in token or "_" in token  # base64 URL-safe encoding
        assert "+" not in token


class TestCreatePasswordResetToken:
    """Test password reset token creation."""

    def test_create_password_reset_token(self, db, test_user):
        """Test creating a password reset token for a user."""
        reset_token = create_password_reset_token(db, test_user.id)

        assert reset_token is not None
        assert reset_token.user_id == test_user.id
        assert reset_token.token is not None
        assert len(reset_token.token) > 0
        assert reset_token.is_used is False
        # Handle both naive and aware datetimes (SQLite returns naive)
        now = datetime.now(timezone.utc)
        if reset_token.expires_at.tzinfo is None:
            now = now.replace(tzinfo=None)
        assert reset_token.expires_at > now

    def test_create_password_reset_token_sets_one_hour_expiry(self, db, test_user):
        """Test that reset token expires in 1 hour."""
        reset_token = create_password_reset_token(db, test_user.id)

        # Calculate expected expiry (should be ~1 hour from now)
        now = datetime.now(timezone.utc)
        expected_expiry = now + timedelta(hours=1)

        # Handle naive datetimes from SQLite
        if reset_token.expires_at.tzinfo is None:
            expected_expiry = expected_expiry.replace(tzinfo=None)

        # Allow 1 second tolerance for test execution time
        time_diff = abs((reset_token.expires_at - expected_expiry).total_seconds())
        assert time_diff < 1

    def test_create_password_reset_token_invalidates_old_tokens(self, db, test_user):
        """Test that creating a new token invalidates existing unused tokens."""
        # Create first token
        token1 = create_password_reset_token(db, test_user.id)
        assert token1.is_used is False

        # Create second token
        token2 = create_password_reset_token(db, test_user.id)
        assert token2.is_used is False

        # Refresh token1 from database
        db.refresh(token1)

        # First token should now be marked as used
        assert token1.is_used is True
        assert token2.is_used is False

    def test_create_password_reset_token_stores_in_database(self, db, test_user):
        """Test that reset token is persisted to database."""
        reset_token = create_password_reset_token(db, test_user.id)

        # Query database to verify token exists
        db_token = (
            db.query(PasswordResetToken)
            .filter(PasswordResetToken.id == reset_token.id)
            .first()
        )

        assert db_token is not None
        assert db_token.token == reset_token.token
        assert db_token.user_id == test_user.id

    def test_create_password_reset_token_for_different_users(self, db, test_user):
        """Test creating reset tokens for multiple users."""
        # Create another user
        user2 = User(
            email="user2@example.com",
            hashed_password="hashedpass",
            full_name="User Two",
        )
        db.add(user2)
        db.commit()
        db.refresh(user2)

        # Create tokens for both users
        token1 = create_password_reset_token(db, test_user.id)
        token2 = create_password_reset_token(db, user2.id)

        assert token1.user_id == test_user.id
        assert token2.user_id == user2.id
        assert token1.token != token2.token


class TestVerifyResetToken:
    """Test password reset token verification."""

    def test_verify_reset_token_with_valid_token(self, db, test_user):
        """Test verifying a valid, unexpired token."""
        reset_token = create_password_reset_token(db, test_user.id)

        # Verify the token
        verified_token = verify_reset_token(db, reset_token.token)

        assert verified_token is not None
        assert verified_token.id == reset_token.id
        assert verified_token.user_id == test_user.id
        assert verified_token.is_used is False

    def test_verify_reset_token_with_invalid_token(self, db):
        """Test verifying a non-existent token returns None."""
        verified_token = verify_reset_token(db, "invalid_token_12345")

        assert verified_token is None

    def test_verify_reset_token_with_expired_token(self, db, test_user):
        """Test that expired tokens are rejected."""
        # Create token and manually set expiry to past
        reset_token = create_password_reset_token(db, test_user.id)
        reset_token.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        db.commit()

        # Verify should return None for expired token
        verified_token = verify_reset_token(db, reset_token.token)

        assert verified_token is None

    def test_verify_reset_token_with_used_token(self, db, test_user):
        """Test that used tokens are rejected."""
        reset_token = create_password_reset_token(db, test_user.id)

        # Mark token as used
        reset_token.is_used = True
        db.commit()

        # Verify should return None for used token
        verified_token = verify_reset_token(db, reset_token.token)

        assert verified_token is None

    def test_verify_reset_token_at_exact_expiry(self, db, test_user):
        """Test token verification at the exact expiry moment."""
        # Create token and set expiry to now
        reset_token = create_password_reset_token(db, test_user.id)
        reset_token.expires_at = datetime.now(timezone.utc)
        db.commit()

        # Token expired exactly now should be invalid
        verified_token = verify_reset_token(db, reset_token.token)

        assert verified_token is None

    def test_verify_reset_token_just_before_expiry(self, db, test_user):
        """Test token is valid just before expiry."""
        # Create token and set expiry to 1 second in future
        reset_token = create_password_reset_token(db, test_user.id)
        reset_token.expires_at = datetime.now(timezone.utc) + timedelta(seconds=1)
        db.commit()

        # Token should still be valid
        verified_token = verify_reset_token(db, reset_token.token)

        assert verified_token is not None
        assert verified_token.id == reset_token.id


class TestResetUserPassword:
    """Test password reset functionality."""

    def test_reset_user_password_success(self, db, test_user):
        """Test successfully resetting a user's password."""
        reset_token = create_password_reset_token(db, test_user.id)
        new_password = "NewSecurePass123"
        old_hashed = test_user.hashed_password

        # Reset the password
        updated_user = reset_user_password(db, reset_token.token, new_password)

        assert updated_user is not None
        assert updated_user.id == test_user.id
        assert updated_user.hashed_password != old_hashed

        # Verify new password works
        assert verify_password(new_password, updated_user.hashed_password)

    def test_reset_user_password_with_invalid_token(self, db):
        """Test that password reset fails with invalid token."""
        result = reset_user_password(db, "invalid_token", "NewPassword123")

        assert result is None

    def test_reset_user_password_with_expired_token(self, db, test_user):
        """Test that password reset fails with expired token."""
        reset_token = create_password_reset_token(db, test_user.id)

        # Expire the token
        reset_token.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        db.commit()

        result = reset_user_password(db, reset_token.token, "NewPassword123")

        assert result is None

    def test_reset_user_password_hashes_new_password(self, db, test_user):
        """Test that new password is properly hashed."""
        reset_token = create_password_reset_token(db, test_user.id)
        new_password = "MyNewPassword456"

        updated_user = reset_user_password(db, reset_token.token, new_password)

        # Password should be hashed, not stored in plain text
        assert updated_user.hashed_password != new_password
        assert len(updated_user.hashed_password) > 50  # Bcrypt hashes are long

        # Verify the password works
        assert verify_password(new_password, updated_user.hashed_password)

    def test_reset_user_password_marks_token_as_used(self, db, test_user):
        """Test that token is marked as used after password reset."""
        reset_token = create_password_reset_token(db, test_user.id)

        # Reset password
        reset_user_password(db, reset_token.token, "NewPassword123")

        # Refresh token from database
        db.refresh(reset_token)

        # Token should be marked as used
        assert reset_token.is_used is True

    def test_reset_user_password_token_cannot_be_reused(self, db, test_user):
        """Test that a token cannot be used twice."""
        reset_token = create_password_reset_token(db, test_user.id)

        # First reset should succeed
        result1 = reset_user_password(db, reset_token.token, "NewPassword123")
        assert result1 is not None

        # Second reset with same token should fail
        result2 = reset_user_password(db, reset_token.token, "AnotherPassword456")
        assert result2 is None

    def test_reset_user_password_persists_to_database(self, db, test_user):
        """Test that password change is persisted to database."""
        reset_token = create_password_reset_token(db, test_user.id)
        new_password = "PersistentPassword789"

        # Reset password
        reset_user_password(db, reset_token.token, new_password)

        # Query user directly from database
        db_user = db.query(User).filter(User.id == test_user.id).first()

        # Verify password was updated in database
        assert verify_password(new_password, db_user.hashed_password)

    def test_reset_user_password_with_special_characters(self, db, test_user):
        """Test password reset with special characters in password."""
        reset_token = create_password_reset_token(db, test_user.id)
        new_password = "P@ssw0rd!#$%^&*()"

        updated_user = reset_user_password(db, reset_token.token, new_password)

        assert updated_user is not None
        assert verify_password(new_password, updated_user.hashed_password)

    def test_reset_user_password_with_used_token(self, db, test_user):
        """Test that already-used tokens cannot reset password."""
        reset_token = create_password_reset_token(db, test_user.id)

        # Mark token as used
        reset_token.is_used = True
        db.commit()

        result = reset_user_password(db, reset_token.token, "NewPassword123")

        assert result is None


class TestPasswordResetTokenExpiry:
    """Test token expiry edge cases and timing."""

    def test_token_expires_after_one_hour(self, db, test_user):
        """Test that token expiry is set to 1 hour from creation."""
        before = datetime.now(timezone.utc)
        reset_token = create_password_reset_token(db, test_user.id)
        after = datetime.now(timezone.utc)

        expected_expiry = before + timedelta(hours=1)
        expected_expiry_max = after + timedelta(hours=1)

        # Handle naive datetimes from SQLite
        if reset_token.expires_at.tzinfo is None:
            expected_expiry = expected_expiry.replace(tzinfo=None)
            expected_expiry_max = expected_expiry_max.replace(tzinfo=None)

        assert expected_expiry <= reset_token.expires_at <= expected_expiry_max

    def test_multiple_tokens_have_different_expiry_times(self, db, test_user):
        """Test that tokens created at different times have different expiries."""
        import time

        token1 = create_password_reset_token(db, test_user.id)
        time.sleep(0.1)  # Small delay
        token2 = create_password_reset_token(db, test_user.id)

        # Token 2 should expire slightly later than token 1
        assert token2.expires_at > token1.expires_at


class TestPasswordResetTokenInvalidation:
    """Test token invalidation scenarios."""

    def test_new_token_invalidates_all_previous_unused_tokens(self, db, test_user):
        """Test that only the newest token is valid."""
        # Create multiple tokens
        token1 = create_password_reset_token(db, test_user.id)
        token2 = create_password_reset_token(db, test_user.id)
        token3 = create_password_reset_token(db, test_user.id)

        # Refresh old tokens from database
        db.refresh(token1)
        db.refresh(token2)

        # Only the latest token should be unused
        assert token1.is_used is True
        assert token2.is_used is True
        assert token3.is_used is False

    def test_invalidation_only_affects_user_tokens(self, db, test_user):
        """Test that token invalidation only affects the specific user."""
        # Create another user
        user2 = User(
            email="user2@example.com",
            hashed_password="hashedpass",
            full_name="User Two",
        )
        db.add(user2)
        db.commit()
        db.refresh(user2)

        # Create tokens for both users
        token_user1 = create_password_reset_token(db, test_user.id)
        token_user2 = create_password_reset_token(db, user2.id)

        # Create new token for user1
        new_token_user1 = create_password_reset_token(db, test_user.id)

        # Refresh tokens
        db.refresh(token_user1)
        db.refresh(token_user2)

        # User1's old token should be invalidated
        assert token_user1.is_used is True

        # User2's token should still be valid
        assert token_user2.is_used is False

        # User1's new token should be valid
        assert new_token_user1.is_used is False
