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
