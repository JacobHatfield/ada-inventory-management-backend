"""Email API endpoint tests."""

from unittest.mock import patch

from fastapi import status


class TestSendTestEmail:
    """Test the POST /api/v1/email/test endpoint."""

    @patch("app.api.v1.email.email_service.is_email_configured")
    @patch("app.api.v1.email.email_service.send_test_email")
    def test_send_test_email_success(
        self, mock_send_test_email, mock_is_configured, client, auth_headers, test_user
    ):
        # Test successful test email sending
        mock_is_configured.return_value = True
        mock_send_test_email.return_value = True

        response = client.post(
            "/api/v1/email/test",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "message" in data
        assert "sent successfully" in data["message"].lower()
        assert data["email"] == test_user.email
        assert test_user.email in data["message"]
        mock_send_test_email.assert_called_once_with(test_user.email)

    @patch("app.api.v1.email.email_service.is_email_configured")
    def test_send_test_email_not_configured(
        self, mock_is_configured, client, auth_headers
    ):
        # Test that endpoint returns 503 when email service not configured
        mock_is_configured.return_value = False

        response = client.post(
            "/api/v1/email/test",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        assert "not configured" in data["detail"].lower()
        assert "smtp" in data["detail"].lower()

    @patch("app.api.v1.email.email_service.is_email_configured")
    @patch("app.api.v1.email.email_service.send_test_email")
    def test_send_test_email_send_failure(
        self, mock_send_test_email, mock_is_configured, client, auth_headers
    ):
        # Test that endpoint returns 500 when email sending fails
        mock_is_configured.return_value = True
        mock_send_test_email.return_value = False

        response = client.post(
            "/api/v1/email/test",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "failed to send" in data["detail"].lower()

    def test_send_test_email_unauthenticated(self, client):
        # Test that endpoint requires authentication
        response = client.post("/api/v1/email/test")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        # Match the detail in credentials_exception
        assert "credentials" in data["detail"].lower()

    def test_send_test_email_invalid_token(self, client):
        # Test that endpoint rejects invalid authentication token
        response = client.post(
            "/api/v1/email/test",
            headers={"Authorization": "Bearer invalid_token_here"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @patch("app.api.v1.email.email_service.is_email_configured")
    @patch("app.api.v1.email.email_service.send_test_email")
    def test_send_test_email_uses_current_user_email(
        self, mock_send_test_email, mock_is_configured, client, auth_headers, test_user
    ):
        # Test that the endpoint sends email to the authenticated user's email
        mock_is_configured.return_value = True
        mock_send_test_email.return_value = True

        response = client.post(
            "/api/v1/email/test",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        # Verify the service was called with the correct user's email
        mock_send_test_email.assert_called_once_with(test_user.email)
        # Verify the response contains the user's email
        data = response.json()
        assert data["email"] == test_user.email


class TestEmailServiceIntegration:
    """Integration tests for email service with API."""

    @patch("app.api.v1.email.email_service.is_email_configured")
    @patch("app.api.v1.email.email_service.send_test_email")
    def test_email_endpoint_calls_service_correctly(
        self, mock_send_test_email, mock_is_configured, client, auth_headers, test_user
    ):
        # Test that the API endpoint correctly integrates with email service
        mock_is_configured.return_value = True
        mock_send_test_email.return_value = True

        client.post("/api/v1/email/test", headers=auth_headers)

        # Verify service methods were called
        mock_is_configured.assert_called_once()
        mock_send_test_email.assert_called_once_with(test_user.email)

    @patch("app.api.v1.email.email_service.is_email_configured")
    @patch("app.api.v1.email.email_service.send_test_email")
    def test_email_endpoint_checks_configuration_first(
        self, mock_send_test_email, mock_is_configured, client, auth_headers
    ):
        # Test that configuration is checked before attempting to send
        mock_is_configured.return_value = False

        client.post("/api/v1/email/test", headers=auth_headers)

        # Verify configuration was checked
        mock_is_configured.assert_called_once()
        # Verify send_test_email was NOT called since not configured
        mock_send_test_email.assert_not_called()

    @patch("app.api.v1.email.email_service.is_email_configured")
    @patch("app.api.v1.email.email_service.send_test_email")
    def test_email_endpoint_response_format(
        self, mock_send_test_email, mock_is_configured, client, auth_headers, test_user
    ):
        # Test that response has correct format with message and email fields
        mock_is_configured.return_value = True
        mock_send_test_email.return_value = True

        response = client.post("/api/v1/email/test", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Verify response structure
        assert "message" in data
        assert "email" in data
        assert isinstance(data["message"], str)
        assert isinstance(data["email"], str)
        # Verify content
        assert len(data["message"]) > 0
        assert data["email"] == test_user.email
