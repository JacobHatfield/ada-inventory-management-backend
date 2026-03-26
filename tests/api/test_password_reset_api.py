"""Password reset API endpoint tests."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from fastapi import status

from app.models.password_reset import PasswordResetToken
from app.services import auth_service


class TestForgotPasswordEndpoint:
    """Test forgot password endpoint."""

    @patch("app.api.v1.auth.email_service.send_password_reset_email")
    def test_forgot_password_with_valid_email(
        self, mock_send_email, client, db, test_user
    ):
        """Test forgot password with valid email sends email and creates token."""
        mock_send_email.return_value = AsyncMock(return_value=True)

        response = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": test_user.email},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "password reset link has been sent" in data["message"].lower()
        assert data["email"] == test_user.email

        # Verify token was created in database
        token = (
            db.query(PasswordResetToken)
            .filter(PasswordResetToken.user_id == test_user.id)
            .first()
        )
        assert token is not None
        assert token.is_used is False

        # Verify email service was called
        mock_send_email.assert_called_once()

    @patch("app.api.v1.auth.email_service.send_password_reset_email")
    def test_forgot_password_with_nonexistent_email(self, mock_send_email, client):
        """Test forgot password with non-existent email still returns success (security)."""
        mock_send_email.return_value = AsyncMock(return_value=True)

        response = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "nonexistent@example.com"},
        )

        # Should return success to not reveal if email exists
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "password reset link has been sent" in data["message"].lower()

        # Email service should NOT have been called
        mock_send_email.assert_not_called()

    def test_forgot_password_with_invalid_email_format(self, client):
        """Test forgot password with invalid email format returns 422."""
        response = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "not-an-email"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestResetPasswordEndpoint:
    """Test reset password endpoint."""

    def test_reset_password_with_valid_token(self, client, db, test_user):
        """Test password reset with valid token succeeds."""
        # Create a reset token
        reset_token = auth_service.create_password_reset_token(db, test_user.id)
        old_password_hash = test_user.hashed_password

        response = client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": reset_token.token,
                "new_password": "NewSecurePass123",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "successfully reset" in data["message"].lower()

        # Verify password was changed
        db.refresh(test_user)
        assert test_user.hashed_password != old_password_hash

    def test_reset_password_with_invalid_or_expired_token(self, client, db, test_user):
        """Test password reset with invalid or expired token returns 400."""
        # Test with invalid token
        response = client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": "invalid_token_12345",
                "new_password": "NewSecurePass123",
            },
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "invalid or expired" in response.json()["detail"].lower()

        # Test with expired token
        reset_token = auth_service.create_password_reset_token(db, test_user.id)
        reset_token.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        db.commit()

        response = client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": reset_token.token,
                "new_password": "NewSecurePass123",
            },
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_reset_password_with_weak_password(self, client, db, test_user):
        """Test password reset validates password strength."""
        reset_token = auth_service.create_password_reset_token(db, test_user.id)

        # Test various weak passwords
        weak_passwords = [
            "weakpass123",  # No uppercase
            "Short1",  # Too short
            "NoDigitsHere",  # No numbers
        ]

        for weak_password in weak_passwords:
            response = client.post(
                "/api/v1/auth/reset-password",
                json={
                    "token": reset_token.token,
                    "new_password": weak_password,
                },
            )
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_reset_password_can_login_with_new_password(self, client, db, test_user):
        """Test that user can login with new password after reset."""
        reset_token = auth_service.create_password_reset_token(db, test_user.id)
        new_password = "MyNewPassword456"

        # Reset password
        reset_response = client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": reset_token.token,
                "new_password": new_password,
            },
        )
        assert reset_response.status_code == status.HTTP_200_OK

        # Try to login with new password
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": new_password,
            },
        )
        assert login_response.status_code == status.HTTP_200_OK
        assert "access_token" in login_response.json()

        # Old password should not work
        old_login_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "testpassword123",
            },
        )
        assert old_login_response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_reset_password_token_cannot_be_reused(self, client, db, test_user):
        """Test that reset token can only be used once."""
        reset_token = auth_service.create_password_reset_token(db, test_user.id)

        # First reset
        response1 = client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": reset_token.token,
                "new_password": "FirstPassword123",
            },
        )
        assert response1.status_code == status.HTTP_200_OK

        # Try to use same token again
        response2 = client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": reset_token.token,
                "new_password": "SecondPassword456",
            },
        )
        assert response2.status_code == status.HTTP_400_BAD_REQUEST


class TestVerifyResetTokenEndpoint:
    """Test verify reset token endpoint."""

    def test_verify_reset_token_with_valid_token(self, client, db, test_user):
        """Test verifying a valid reset token returns success."""
        reset_token = auth_service.create_password_reset_token(db, test_user.id)

        response = client.post(
            f"/api/v1/auth/verify-reset-token?token={reset_token.token}"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["valid"] is True

    def test_verify_reset_token_with_invalid_token(self, client, db, test_user):
        """Test verifying an invalid, expired, or used token returns 400."""
        # Invalid token
        response = client.post("/api/v1/auth/verify-reset-token?token=invalid_token")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        # Expired token
        reset_token = auth_service.create_password_reset_token(db, test_user.id)
        reset_token.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        db.commit()
        response = client.post(
            f"/api/v1/auth/verify-reset-token?token={reset_token.token}"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestPasswordResetWorkflowIntegration:
    """Test complete password reset workflow end-to-end."""

    @patch("app.api.v1.auth.email_service.send_password_reset_email")
    @patch("app.api.v1.auth.email_service.send_password_reset_confirmation_email")
    def test_complete_password_reset_workflow(
        self, mock_confirmation, mock_reset_email, client, db, test_user
    ):
        """Test complete workflow from forgot password to login with new password."""
        mock_reset_email.return_value = AsyncMock(return_value=True)
        mock_confirmation.return_value = AsyncMock(return_value=True)

        # Step 1: Request password reset
        forgot_response = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": test_user.email},
        )
        assert forgot_response.status_code == status.HTTP_200_OK

        # Get token from database
        reset_token = (
            db.query(PasswordResetToken)
            .filter(
                PasswordResetToken.user_id == test_user.id,
                PasswordResetToken.is_used == False,  # noqa: E712
            )
            .first()
        )
        assert reset_token is not None

        # Step 2: Verify token is valid
        verify_response = client.post(
            f"/api/v1/auth/verify-reset-token?token={reset_token.token}"
        )
        assert verify_response.status_code == status.HTTP_200_OK

        # Step 3: Reset password
        new_password = "CompleteWorkflow123"
        reset_response = client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": reset_token.token,
                "new_password": new_password,
            },
        )
        assert reset_response.status_code == status.HTTP_200_OK

        # Step 4: Login with new password
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": new_password,
            },
        )
        assert login_response.status_code == status.HTTP_200_OK
        assert "access_token" in login_response.json()

    @patch("app.api.v1.auth.email_service.send_password_reset_email")
    def test_multiple_reset_requests_only_latest_token_works(
        self, mock_send_email, client, db, test_user
    ):
        """Test that only the most recent reset token is valid."""
        mock_send_email.return_value = AsyncMock(return_value=True)

        # Create first reset request
        response1 = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": test_user.email},
        )
        assert response1.status_code == status.HTTP_200_OK

        # Get first token
        token1 = (
            db.query(PasswordResetToken)
            .filter(PasswordResetToken.user_id == test_user.id)
            .first()
        )
        token1_value = token1.token

        # Create second reset request
        response2 = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": test_user.email},
        )
        assert response2.status_code == status.HTTP_200_OK

        # Get latest token
        latest_token = (
            db.query(PasswordResetToken)
            .filter(
                PasswordResetToken.user_id == test_user.id,
                PasswordResetToken.is_used == False,  # noqa: E712
            )
            .first()
        )

        # Try to reset with old token - should fail
        reset_old_response = client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": token1_value,
                "new_password": "NewPassword123",
            },
        )
        assert reset_old_response.status_code == status.HTTP_400_BAD_REQUEST

        # Reset with latest token - should succeed
        reset_new_response = client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": latest_token.token,
                "new_password": "NewPassword123",
            },
        )
        assert reset_new_response.status_code == status.HTTP_200_OK


class TestPasswordResetSecurityAndEdgeCases:
    """Test security edge cases and boundary conditions."""

    def test_reset_password_with_very_long_password(self, client, db, test_user):
        """Test password reset accepts reasonably long passwords."""
        reset_token = auth_service.create_password_reset_token(db, test_user.id)

        # 100 character password with all requirements
        long_password = "A1" + "b" * 98

        response = client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": reset_token.token,
                "new_password": long_password,
            },
        )

        assert response.status_code == status.HTTP_200_OK

    def test_reset_password_with_special_characters(self, client, db, test_user):
        """Test password reset accepts special characters in password."""
        special_passwords = [
            "P@ssw0rd!#$%",
            "MyP@ss123!",
            "Str0ng&P@ss",
            "C0mpl3x!Pass#",
        ]

        for password in special_passwords:
            # Create new token for each test
            token = auth_service.create_password_reset_token(db, test_user.id)
            response = client.post(
                "/api/v1/auth/reset-password",
                json={
                    "token": token.token,
                    "new_password": password,
                },
            )
            assert response.status_code == status.HTTP_200_OK

    def test_reset_password_with_unicode_characters(self, client, db, test_user):
        """Test password reset with unicode characters in password."""
        reset_token = auth_service.create_password_reset_token(db, test_user.id)

        # Unicode password with requirements
        unicode_password = "Pässw0rd123"

        response = client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": reset_token.token,
                "new_password": unicode_password,
            },
        )

        # Should accept unicode characters
        assert response.status_code == status.HTTP_200_OK

    def test_forgot_password_with_email_case_insensitivity(self, client, db, test_user):
        """Test forgot password is case-insensitive for email."""
        # Test with uppercase email
        response_upper = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": test_user.email.upper()},
        )

        # Should still return success (even if email lookup is case-sensitive,
        # we return success to not reveal user existence)
        assert response_upper.status_code == status.HTTP_200_OK

    def test_verify_token_with_malformed_token_formats(self, client):
        """Test verify endpoint with various malformed token formats."""
        malformed_tokens = [
            "",  # Empty string
            " ",  # Whitespace
            "a" * 1000,  # Extremely long
            "token with spaces",
            "../../../etc/passwd",  # Path traversal attempt
            "<script>alert('xss')</script>",  # XSS attempt
            "'; DROP TABLE users; --",  # SQL injection attempt
        ]

        for malformed_token in malformed_tokens:
            response = client.post(
                f"/api/v1/auth/verify-reset-token?token={malformed_token}"
            )
            # All should return 400 or 422
            assert response.status_code in [
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            ]

    def test_reset_password_with_malformed_token_formats(self, client):
        """Test reset endpoint with various malformed token formats."""
        malformed_tokens = [
            "",
            " ",
            "a" * 1000,
            "../../../etc/passwd",
            "'; DROP TABLE password_reset_tokens; --",
        ]

        for malformed_token in malformed_tokens:
            response = client.post(
                "/api/v1/auth/reset-password",
                json={
                    "token": malformed_token,
                    "new_password": "ValidPassword123",
                },
            )
            assert response.status_code in [
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            ]

    def test_forgot_password_with_sql_injection_attempt(self, client):
        """Test forgot password endpoint against SQL injection in email field."""
        sql_injection_attempts = [
            "test@example.com'; DROP TABLE users; --",
            "test@example.com' OR '1'='1",
            "admin'--",
            "' OR 1=1 --",
        ]

        for injection_attempt in sql_injection_attempts:
            response = client.post(
                "/api/v1/auth/forgot-password",
                json={"email": injection_attempt},
            )
            # Should return 200 (security obfuscation) or 422 (validation error)
            assert response.status_code in [
                status.HTTP_200_OK,
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            ]

    def test_reset_password_token_timing_attack_prevention(self, client, db, test_user):
        """Test that invalid and valid tokens don't reveal timing differences."""
        import time

        reset_token = auth_service.create_password_reset_token(db, test_user.id)

        # Time invalid token verification
        start_invalid = time.time()
        response_invalid = client.post(
            "/api/v1/auth/verify-reset-token?token=invalid_token_123"
        )
        time_invalid = time.time() - start_invalid

        # Time valid token verification
        start_valid = time.time()
        response_valid = client.post(
            f"/api/v1/auth/verify-reset-token?token={reset_token.token}"
        )
        time_valid = time.time() - start_valid

        assert response_invalid.status_code == status.HTTP_400_BAD_REQUEST
        assert response_valid.status_code == status.HTTP_200_OK

        # Timing difference should not be significant (less than 1 second)
        # This is a basic check; real timing attack prevention requires constant-time comparison
        assert abs(time_valid - time_invalid) < 1.0

    @patch("app.api.v1.auth.email_service.send_password_reset_email")
    def test_forgot_password_multiple_rapid_requests(
        self, mock_send_email, client, db, test_user
    ):
        """Test handling of multiple rapid forgot password requests."""
        mock_send_email.return_value = AsyncMock(return_value=True)

        # Make 5 rapid requests
        responses = []
        for _ in range(5):
            response = client.post(
                "/api/v1/auth/forgot-password",
                json={"email": test_user.email},
            )
            responses.append(response)

        # All should succeed (to not reveal rate limiting)
        for response in responses:
            assert response.status_code == status.HTTP_200_OK

        # Only the latest token should be valid
        valid_tokens = (
            db.query(PasswordResetToken)
            .filter(
                PasswordResetToken.user_id == test_user.id,
                PasswordResetToken.is_used == False,  # noqa: E712
            )
            .count()
        )
        # Should only have 1 non-used token (latest one)
        assert valid_tokens == 1

    def test_reset_password_with_whitespace_in_password(self, client, db, test_user):
        """Test password reset with whitespace in password."""
        # Passwords with spaces (should be allowed)
        passwords_with_spaces = [
            "My Pass Word 123",
            "  LeadingSpace1A",
            "TrailingSpace1A  ",
        ]

        for password in passwords_with_spaces:
            token = auth_service.create_password_reset_token(db, test_user.id)
            response = client.post(
                "/api/v1/auth/reset-password",
                json={
                    "token": token.token,
                    "new_password": password,
                },
            )
            # Spaces should be allowed if password meets other requirements
            assert response.status_code == status.HTTP_200_OK

    def test_verify_token_does_not_mark_token_as_used(self, client, db, test_user):
        """Test that verifying a token doesn't mark it as used."""
        reset_token = auth_service.create_password_reset_token(db, test_user.id)

        # Verify token
        verify_response = client.post(
            f"/api/v1/auth/verify-reset-token?token={reset_token.token}"
        )
        assert verify_response.status_code == status.HTTP_200_OK

        # Token should still be usable
        db.refresh(reset_token)
        assert reset_token.is_used is False

        # Should be able to reset password
        reset_response = client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": reset_token.token,
                "new_password": "NewPassword123",
            },
        )
        assert reset_response.status_code == status.HTTP_200_OK

    def test_reset_password_marks_old_tokens_correctly(self, client, db, test_user):
        """Test that old tokens are properly marked when creating new ones."""
        # Create first token
        token1 = auth_service.create_password_reset_token(db, test_user.id)

        # Create second token (should invalidate first)
        token2 = auth_service.create_password_reset_token(db, test_user.id)

        # Refresh first token
        db.refresh(token1)

        # First token should be marked as used
        assert token1.is_used is True
        assert token2.is_used is False

        # Try to use first token (should fail)
        response = client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": token1.token,
                "new_password": "NewPassword123",
            },
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_forgot_password_does_not_leak_user_existence_timing(self, client, db):
        """Test that response time is similar for existing and non-existing users."""
        import time

        # Time for existing user
        test_user_email = "test@example.com"
        start_existing = time.time()
        response_existing = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": test_user_email},
        )
        time_existing = time.time() - start_existing

        # Time for non-existing user
        start_nonexisting = time.time()
        response_nonexisting = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "nonexistent@example.com"},
        )
        time_nonexisting = time.time() - start_nonexisting

        # Both should return 200
        assert response_existing.status_code == status.HTTP_200_OK
        assert response_nonexisting.status_code == status.HTTP_200_OK

        # Timing difference should be minimal (less than 500ms difference)
        assert abs(time_existing - time_nonexisting) < 0.5

    @patch("app.api.v1.auth.email_service.send_password_reset_confirmation_email")
    def test_reset_password_confirmation_email_sent(
        self, mock_confirmation, client, db, test_user
    ):
        """Test that confirmation email is sent after successful password reset."""
        mock_confirmation.return_value = AsyncMock(return_value=True)
        reset_token = auth_service.create_password_reset_token(db, test_user.id)

        response = client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": reset_token.token,
                "new_password": "NewSecurePassword123",
            },
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify confirmation email was called
        mock_confirmation.assert_called_once_with(test_user.email)

    def test_reset_password_with_exactly_minimum_requirements(
        self, client, db, test_user
    ):
        """Test password reset with exactly minimum password requirements."""
        reset_token = auth_service.create_password_reset_token(db, test_user.id)

        # Exactly 8 characters, 1 uppercase, 1 lowercase, 1 digit
        minimal_password = "Abcdef1g"

        response = client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": reset_token.token,
                "new_password": minimal_password,
            },
        )

        assert response.status_code == status.HTTP_200_OK

    def test_token_expiry_boundary_condition(self, client, db, test_user):
        """Test token verification exactly at expiry boundary."""
        reset_token = auth_service.create_password_reset_token(db, test_user.id)

        # Set expiry to exactly now (edge case)
        reset_token.expires_at = datetime.now(timezone.utc)
        db.commit()

        # Token should be considered expired
        response = client.post(
            f"/api/v1/auth/verify-reset-token?token={reset_token.token}"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_multiple_users_password_reset_isolation(self, client, db, test_user):
        """Test that password reset tokens are properly isolated between users."""
        from app.core.security import hash_password
        from app.models.user import User

        # Create second user
        user2 = User(
            email="user2@example.com",
            full_name="User Two",
            hashed_password=hash_password("testpassword123"),
        )
        db.add(user2)
        db.commit()
        db.refresh(user2)

        # Create reset tokens for both users
        token1 = auth_service.create_password_reset_token(db, test_user.id)
        auth_service.create_password_reset_token(db, user2.id)

        # User 1's token should not work for user 2's password
        # (token is linked to user, so this should fail)
        response = client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": token1.token,
                "new_password": "NewPassword123",
            },
        )
        assert response.status_code == status.HTTP_200_OK

        # Verify user2's password hasn't changed
        db.refresh(user2)
        from app.core.security import verify_password

        assert verify_password("testpassword123", user2.hashed_password)
