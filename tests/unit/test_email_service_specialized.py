"""Specialized unit tests for email service functions."""

from unittest.mock import patch

import pytest

from app.services import email_service


class TestSpecializedEmails:
    """Specialized email tests."""

    @pytest.mark.asyncio
    @patch("app.services.email_service.is_email_configured")
    @patch("app.services.email_service.send_email")
    @patch("app.services.email_service.settings")
    async def test_send_password_reset_email(
        self, mock_settings, mock_send_email, mock_is_configured
    ):
        mock_is_configured.return_value = True
        mock_settings.FRONTEND_URL = "http://test.com"
        mock_send_email.return_value = True

        result = await email_service.send_password_reset_email(
            "user@example.com", "reset-token-123"
        )

        assert result is True
        mock_send_email.assert_called_once()
        args = mock_send_email.call_args[0]
        assert args[0] == "user@example.com"
        assert "Password Reset" in args[1]
        assert "reset-token-123" in args[2]  # Plain text body
        assert "reset-token-123" in args[3]  # HTML body

    @pytest.mark.asyncio
    @patch("app.services.email_service.is_email_configured")
    @patch("app.services.email_service.send_email")
    async def test_send_password_reset_confirmation_email(
        self, mock_send_email, mock_is_configured
    ):
        mock_is_configured.return_value = True
        mock_send_email.return_value = True

        result = await email_service.send_password_reset_confirmation_email(
            "user@example.com"
        )

        assert result is True
        mock_send_email.assert_called_once()
        args = mock_send_email.call_args[0]
        assert args[0] == "user@example.com"
        assert "Password Successfully Reset" in args[1]

    @pytest.mark.asyncio
    @patch("app.services.email_service.is_email_configured")
    @patch("app.services.email_service.send_email")
    @patch("app.services.email_service.settings")
    async def test_send_low_stock_alert_email(
        self, mock_settings, mock_send_email, mock_is_configured
    ):
        mock_is_configured.return_value = True
        mock_settings.FRONTEND_URL = "http://test.com"
        mock_send_email.return_value = True

        items = [
            {"name": "Item 1", "quantity": 5, "low_stock_threshold": 10},
            {"name": "Item 2", "quantity": 2, "low_stock_threshold": 10},
        ]

        result = await email_service.send_low_stock_alert_email(
            "admin@example.com", items
        )

        assert result is True
        mock_send_email.assert_called_once()
        args = mock_send_email.call_args[0]
        assert args[0] == "admin@example.com"
        assert "Low Stock Alert" in args[1]
        assert "Item 1" in args[2]
        assert "Item 2" in args[2]
        assert "Item 1" in args[3]
        assert "Item 2" in args[3]

    @pytest.mark.asyncio
    @patch("app.services.email_service.is_email_configured")
    @patch("app.services.email_service.send_email")
    @patch("app.services.email_service.settings")
    async def test_send_critical_stock_alert_email(
        self, mock_settings, mock_send_email, mock_is_configured
    ):
        mock_is_configured.return_value = True
        mock_settings.FRONTEND_URL = "http://test.com"
        mock_send_email.return_value = True

        items = [
            {"name": "Critical Item", "quantity": 1, "low_stock_threshold": 10},
        ]

        result = await email_service.send_critical_stock_alert_email(
            "admin@example.com", items
        )

        assert result is True
        mock_send_email.assert_called_once()
        args = mock_send_email.call_args[0]
        assert args[0] == "admin@example.com"
        assert "CRITICAL Stock Alert" in args[1]
        assert "Critical Item" in args[2]
        assert "URGENT ACTION REQUIRED" in args[2]

    @pytest.mark.asyncio
    @patch("app.services.email_service.is_email_configured")
    async def test_specialized_emails_not_configured(self, mock_is_configured):
        mock_is_configured.return_value = False

        assert (
            await email_service.send_password_reset_email("test@test.com", "token")
            is False
        )
        assert (
            await email_service.send_password_reset_confirmation_email("test@test.com")
            is False
        )
        assert (
            await email_service.send_low_stock_alert_email("test@test.com", []) is False
        )
        assert (
            await email_service.send_critical_stock_alert_email("test@test.com", [])
            is False
        )
