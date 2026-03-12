"""Email service for sending emails via SMTP."""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


def is_email_configured() -> bool:
    # Check if all required SMTP settings are configured
    required_settings = [
        settings.SMTP_HOST,
        settings.SMTP_USER,
        settings.SMTP_PASSWORD,
        settings.SMTP_FROM_EMAIL,
    ]
    return all(required_settings)


async def send_email(
    to_email: str,
    subject: str,
    body: str,
    html_body: Optional[str] = None,
) -> bool:
    # Send an email via SMTP with optional HTML body
    if not is_email_configured():
        logger.warning("Email not configured. Skipping email send.")
        return False

    try:
        # Create message container
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        msg["To"] = to_email

        # Attach plain text version
        text_part = MIMEText(body, "plain")
        msg.attach(text_part)

        # Attach HTML version if provided
        if html_body:
            html_part = MIMEText(html_body, "html")
            msg.attach(html_part)

        # Connect to SMTP server and send email
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()  # Upgrade to secure connection
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)

        logger.info(f"Email sent successfully to {to_email}")
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP authentication failed. Check username/password.")
        return False
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error occurred: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending email: {str(e)}")
        return False


async def send_test_email(to_email: str) -> bool:
    # Send a test email to verify email configuration
    subject = "Test Email - Inventory Management System"
    body = """
This is a test email from your Inventory Management System.

If you received this email, your email configuration is working correctly!

You can now use email features like:
- Password reset
- Low stock alerts
- Notifications

--
Inventory Management System
"""

    html_body = """
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <h2 style="color: #4CAF50;">Test Email - Inventory Management System</h2>
    
    <p>This is a test email from your Inventory Management System.</p>
    
    <p><strong style="color: #4CAF50;">✓ Success!</strong> If you received this email, your email configuration is working correctly!</p>
    
    <p>You can now use email features like:</p>
    <ul>
        <li>Password reset</li>
        <li>Low stock alerts</li>
        <li>Notifications</li>
    </ul>
    
    <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
    <p style="font-size: 12px; color: #666;">
        Inventory Management System
    </p>
</body>
</html>
"""

    return await send_email(to_email, subject, body, html_body)


async def send_password_reset_email(
    to_email: str,
    reset_token: str,
    frontend_url: str = None,
) -> bool:
    """Send password reset email with reset link."""
    if frontend_url is None:
        frontend_url = settings.FRONTEND_URL

    if not is_email_configured():
        logger.warning("Email not configured. Skipping password reset email.")
        return False

    reset_link = f"{frontend_url}/reset-password?token={reset_token}"

    subject = "Password Reset Request"

    # Plain text version
    body = f"""
Hello,

You requested to reset your password for the Inventory Management System.

Click the link below to reset your password:
{reset_link}

This link will expire in 1 hour.

If you didn't request this, please ignore this email.

Best regards,
Inventory Management Team
"""

    # HTML version
    html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .button {{ 
            display: inline-block; 
            padding: 12px 24px; 
            background-color: #4F46E5; 
            color: white; 
            text-decoration: none; 
            border-radius: 5px; 
            margin: 20px 0;
        }}
        .footer {{ margin-top: 30px; font-size: 12px; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <h2>Password Reset Request</h2>
        <p>You requested to reset your password for the Inventory Management System.</p>
        <p>Click the button below to reset your password:</p>
        <a href="{reset_link}" class="button">Reset Password</a>
        <p>Or copy and paste this link into your browser:</p>
        <p style="word-break: break-all; color: #666;">{reset_link}</p>
        <p><strong>This link will expire in 1 hour.</strong></p>
        <div class="footer">
            <p>If you didn't request this, please ignore this email.</p>
            <p>Best regards,<br>Inventory Management Team</p>
        </div>
    </div>
</body>
</html>
"""

    return await send_email(to_email, subject, body, html_body)


async def send_password_reset_confirmation_email(to_email: str) -> bool:
    """Send confirmation email after successful password reset."""
    if not is_email_configured():
        logger.warning("Email not configured. Skipping confirmation email.")
        return False

    subject = "Password Successfully Reset"

    body = """
Hello,

Your password has been successfully reset.

If you didn't make this change, please contact support immediately.

Best regards,
Inventory Management Team
"""

    html_body = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .success { color: #10B981; font-weight: bold; }
        .footer { margin-top: 30px; font-size: 12px; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <h2>Password Successfully Reset</h2>
        <p class="success">✓ Your password has been successfully reset.</p>
        <p>You can now log in with your new password.</p>
        <div class="footer">
            <p>If you didn't make this change, please contact support immediately.</p>
            <p>Best regards,<br>Inventory Management Team</p>
        </div>
    </div>
</body>
</html>
"""

    return await send_email(to_email, subject, body, html_body)
