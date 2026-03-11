"""Unit tests for email service."""

import smtplib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services import email_service


class TestEmailConfiguration:
    """Test email configuration detection."""

    @patch("app.services.email_service.settings")
    def test_is_email_configured_with_settings(self, mock_settings):
        # Test that email is detected as configured when all settings present
        mock_settings.SMTP_HOST = "smtp.gmail.com"
        mock_settings.SMTP_USER = "user@example.com"
        mock_settings.SMTP_PASSWORD = "password123"
        mock_settings.SMTP_FROM_EMAIL = "noreply@example.com"

        assert email_service.is_email_configured() is True

    @patch("app.services.email_service.settings")
    def test_is_email_configured_without_settings(self, mock_settings):
        # Test that email is detected as not configured when settings missing
        mock_settings.SMTP_HOST = ""
        mock_settings.SMTP_USER = ""
        mock_settings.SMTP_PASSWORD = ""
        mock_settings.SMTP_FROM_EMAIL = ""

        assert email_service.is_email_configured() is False

    @patch("app.services.email_service.settings")
    def test_is_email_configured_partial_settings(self, mock_settings):
        # Test that email is not configured if any setting is missing
        mock_settings.SMTP_HOST = "smtp.gmail.com"
        mock_settings.SMTP_USER = "user@example.com"
        mock_settings.SMTP_PASSWORD = ""  # Missing password
        mock_settings.SMTP_FROM_EMAIL = "noreply@example.com"

        assert email_service.is_email_configured() is False


class TestEmailSending:
    """Test email sending functionality."""

    @pytest.mark.asyncio
    @patch("app.services.email_service.is_email_configured")
    @patch("app.services.email_service.smtplib.SMTP")
    @patch("app.services.email_service.settings")
    async def test_send_email_success(
        self, mock_settings, mock_smtp_class, mock_is_configured
    ):
        # Test successful email sending
        mock_is_configured.return_value = True
        mock_settings.SMTP_HOST = "smtp.gmail.com"
        mock_settings.SMTP_PORT = 587
        mock_settings.SMTP_USER = "user@example.com"
        mock_settings.SMTP_PASSWORD = "password123"
        mock_settings.SMTP_FROM_EMAIL = "noreply@example.com"
        mock_settings.SMTP_FROM_NAME = "Test System"

        mock_smtp = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_smtp

        result = await email_service.send_email(
            to_email="recipient@example.com",
            subject="Test Subject",
            body="Test body",
        )

        assert result is True
        mock_smtp.starttls.assert_called_once()
        mock_smtp.login.assert_called_once_with("user@example.com", "password123")
        mock_smtp.send_message.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.email_service.is_email_configured")
    @patch("app.services.email_service.smtplib.SMTP")
    @patch("app.services.email_service.settings")
    async def test_send_email_with_html_body(
        self, mock_settings, mock_smtp_class, mock_is_configured
    ):
        # Test email sending with HTML body
        mock_is_configured.return_value = True
        mock_settings.SMTP_HOST = "smtp.gmail.com"
        mock_settings.SMTP_PORT = 587
        mock_settings.SMTP_USER = "user@example.com"
        mock_settings.SMTP_PASSWORD = "password123"
        mock_settings.SMTP_FROM_EMAIL = "noreply@example.com"
        mock_settings.SMTP_FROM_NAME = "Test System"

        mock_smtp = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_smtp

        html_body = "<html><body><h1>Test</h1></body></html>"
        result = await email_service.send_email(
            to_email="recipient@example.com",
            subject="Test Subject",
            body="Plain text",
            html_body=html_body,
        )

        assert result is True
        mock_smtp.send_message.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.email_service.is_email_configured")
    async def test_send_email_when_not_configured(self, mock_is_configured):
        # Test that email returns False when not configured
        mock_is_configured.return_value = False

        result = await email_service.send_email(
            to_email="recipient@example.com",
            subject="Test Subject",
            body="Test body",
        )

        assert result is False

    @pytest.mark.asyncio
    @patch("app.services.email_service.is_email_configured")
    @patch("app.services.email_service.smtplib.SMTP")
    @patch("app.services.email_service.settings")
    async def test_send_email_smtp_authentication_failure(
        self, mock_settings, mock_smtp_class, mock_is_configured
    ):
        # Test handling of SMTP authentication failure
        mock_is_configured.return_value = True
        mock_settings.SMTP_HOST = "smtp.gmail.com"
        mock_settings.SMTP_PORT = 587
        mock_settings.SMTP_USER = "user@example.com"
        mock_settings.SMTP_PASSWORD = "wrong_password"
        mock_settings.SMTP_FROM_EMAIL = "noreply@example.com"
        mock_settings.SMTP_FROM_NAME = "Test System"

        mock_smtp = MagicMock()
        mock_smtp.login.side_effect = smtplib.SMTPAuthenticationError(
            535, b"Authentication failed"
        )
        mock_smtp_class.return_value.__enter__.return_value = mock_smtp

        result = await email_service.send_email(
            to_email="recipient@example.com",
            subject="Test Subject",
            body="Test body",
        )

        assert result is False

    @pytest.mark.asyncio
    @patch("app.services.email_service.is_email_configured")
    @patch("app.services.email_service.smtplib.SMTP")
    @patch("app.services.email_service.settings")
    async def test_send_email_smtp_connection_failure(
        self, mock_settings, mock_smtp_class, mock_is_configured
    ):
        # Test handling of SMTP connection failure
        mock_is_configured.return_value = True
        mock_settings.SMTP_HOST = "smtp.gmail.com"
        mock_settings.SMTP_PORT = 587
        mock_settings.SMTP_USER = "user@example.com"
        mock_settings.SMTP_PASSWORD = "password123"
        mock_settings.SMTP_FROM_EMAIL = "noreply@example.com"
        mock_settings.SMTP_FROM_NAME = "Test System"

        mock_smtp_class.side_effect = smtplib.SMTPConnectError(421, b"Service unavailable")

        result = await email_service.send_email(
            to_email="recipient@example.com",
            subject="Test Subject",
            body="Test body",
        )

        assert result is False

    @pytest.mark.asyncio
    @patch("app.services.email_service.is_email_configured")
    @patch("app.services.email_service.smtplib.SMTP")
    @patch("app.services.email_service.settings")
    async def test_send_email_generic_smtp_exception(
        self, mock_settings, mock_smtp_class, mock_is_configured
    ):
        # Test handling of generic SMTP exception
        mock_is_configured.return_value = True
        mock_settings.SMTP_HOST = "smtp.gmail.com"
        mock_settings.SMTP_PORT = 587
        mock_settings.SMTP_USER = "user@example.com"
        mock_settings.SMTP_PASSWORD = "password123"
        mock_settings.SMTP_FROM_EMAIL = "noreply@example.com"
        mock_settings.SMTP_FROM_NAME = "Test System"

        mock_smtp = MagicMock()
        mock_smtp.send_message.side_effect = smtplib.SMTPException("Generic error")
        mock_smtp_class.return_value.__enter__.return_value = mock_smtp

        result = await email_service.send_email(
            to_email="recipient@example.com",
            subject="Test Subject",
            body="Test body",
        )

        assert result is False

    @pytest.mark.asyncio
    @patch("app.services.email_service.is_email_configured")
    @patch("app.services.email_service.smtplib.SMTP")
    @patch("app.services.email_service.settings")
    async def test_send_email_unexpected_exception(
        self, mock_settings, mock_smtp_class, mock_is_configured
    ):
        # Test handling of unexpected exception
        mock_is_configured.return_value = True
        mock_settings.SMTP_HOST = "smtp.gmail.com"
        mock_settings.SMTP_PORT = 587
        mock_settings.SMTP_USER = "user@example.com"
        mock_settings.SMTP_PASSWORD = "password123"
        mock_settings.SMTP_FROM_EMAIL = "noreply@example.com"
        mock_settings.SMTP_FROM_NAME = "Test System"

        mock_smtp = MagicMock()
        mock_smtp.send_message.side_effect = Exception("Unexpected error")
        mock_smtp_class.return_value.__enter__.return_value = mock_smtp

        result = await email_service.send_email(
            to_email="recipient@example.com",
            subject="Test Subject",
            body="Test body",
        )

        assert result is False


class TestEmailContent:
    """Test email content and formatting."""

    @pytest.mark.asyncio
    @patch("app.services.email_service.is_email_configured")
    @patch("app.services.email_service.smtplib.SMTP")
    @patch("app.services.email_service.settings")
    async def test_email_from_address_correct(
        self, mock_settings, mock_smtp_class, mock_is_configured
    ):
        # Test that email From address is correctly set
        mock_is_configured.return_value = True
        mock_settings.SMTP_HOST = "smtp.gmail.com"
        mock_settings.SMTP_PORT = 587
        mock_settings.SMTP_USER = "user@example.com"
        mock_settings.SMTP_PASSWORD = "password123"
        mock_settings.SMTP_FROM_EMAIL = "noreply@example.com"
        mock_settings.SMTP_FROM_NAME = "My System"

        mock_smtp = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_smtp

        await email_service.send_email(
            to_email="recipient@example.com",
            subject="Test",
            body="Body",
        )

        # Verify send_message was called and check the message
        call_args = mock_smtp.send_message.call_args
        message = call_args[0][0]
        assert "noreply@example.com" in message["From"]
        assert "My System" in message["From"]

    @pytest.mark.asyncio
    @patch("app.services.email_service.is_email_configured")
    @patch("app.services.email_service.smtplib.SMTP")
    @patch("app.services.email_service.settings")
    async def test_email_subject_correct(
        self, mock_settings, mock_smtp_class, mock_is_configured
    ):
        # Test that email subject is correctly set
        mock_is_configured.return_value = True
        mock_settings.SMTP_HOST = "smtp.gmail.com"
        mock_settings.SMTP_PORT = 587
        mock_settings.SMTP_USER = "user@example.com"
        mock_settings.SMTP_PASSWORD = "password123"
        mock_settings.SMTP_FROM_EMAIL = "noreply@example.com"
        mock_settings.SMTP_FROM_NAME = "Test System"

        mock_smtp = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_smtp

        test_subject = "Important Test Email"
        await email_service.send_email(
            to_email="recipient@example.com",
            subject=test_subject,
            body="Body",
        )

        call_args = mock_smtp.send_message.call_args
        message = call_args[0][0]
        assert message["Subject"] == test_subject

    @pytest.mark.asyncio
    @patch("app.services.email_service.is_email_configured")
    @patch("app.services.email_service.smtplib.SMTP")
    @patch("app.services.email_service.settings")
    async def test_email_to_address_correct(
        self, mock_settings, mock_smtp_class, mock_is_configured
    ):
        # Test that email To address is correctly set
        mock_is_configured.return_value = True
        mock_settings.SMTP_HOST = "smtp.gmail.com"
        mock_settings.SMTP_PORT = 587
        mock_settings.SMTP_USER = "user@example.com"
        mock_settings.SMTP_PASSWORD = "password123"
        mock_settings.SMTP_FROM_EMAIL = "noreply@example.com"
        mock_settings.SMTP_FROM_NAME = "Test System"

        mock_smtp = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_smtp

        recipient = "recipient@example.com"
        await email_service.send_email(
            to_email=recipient,
            subject="Test",
            body="Body",
        )

        call_args = mock_smtp.send_message.call_args
        message = call_args[0][0]
        assert message["To"] == recipient


class TestTestEmail:
    """Test the send_test_email function."""

    @pytest.mark.asyncio
    @patch("app.services.email_service.send_email")
    async def test_send_test_email_calls_send_email(self, mock_send_email):
        # Test that send_test_email calls send_email with correct parameters
        mock_send_email.return_value = True

        result = await email_service.send_test_email("test@example.com")

        assert result is True
        mock_send_email.assert_called_once()
        call_args = mock_send_email.call_args
        # Args: (to_email, subject, body, html_body)
        assert call_args[0][0] == "test@example.com"
        assert "Test Email" in call_args[0][1]
        assert "test email" in call_args[0][2].lower()
        assert call_args[0][3] is not None

    @pytest.mark.asyncio
    @patch("app.services.email_service.send_email")
    async def test_send_test_email_includes_html(self, mock_send_email):
        # Test that test email includes HTML version
        mock_send_email.return_value = True

        await email_service.send_test_email("test@example.com")

        call_args = mock_send_email.call_args
        # Args: (to_email, subject, body, html_body)
        html_body = call_args[0][3]
        assert html_body is not None
        assert "<html>" in html_body
        assert "</html>" in html_body

    @pytest.mark.asyncio
    @patch("app.services.email_service.send_email")
    async def test_send_test_email_returns_false_on_failure(self, mock_send_email):
        # Test that send_test_email returns False when send_email fails
        mock_send_email.return_value = False

        result = await email_service.send_test_email("test@example.com")

        assert result is False
