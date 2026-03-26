"""Email service for sending emails via SMTP."""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional
import os

try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail, Email, To, Content
    HAS_SENDGRID = True
except ImportError:
    HAS_SENDGRID = False

from app.core.config import settings

logger = logging.getLogger(__name__)


def is_email_configured() -> bool:
    # Check if SendGrid is configured AND the library is installed
    if settings.SENDGRID_API_KEY and HAS_SENDGRID:
        return True
        
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
        # Prefer SendGrid API if configured and library is installed
        if settings.SENDGRID_API_KEY and HAS_SENDGRID:
            sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
            message = Mail(
                from_email=(settings.SMTP_FROM_EMAIL or "noreply@inventory.local"),
                to_emails=to_email,
                subject=subject,
                plain_text_content=body,
                html_content=html_body
            )
            response = sg.send(message)
            if response.status_code >= 200 and response.status_code < 300:
                logger.info(f"Email sent successfully to {to_email} via SendGrid API")
                return True
            else:
                logger.error(f"SendGrid API error: {response.body}")
                # Fall back to SMTP if configured, or just return False
                if not all([settings.SMTP_HOST, settings.SMTP_USER, settings.SMTP_PASSWORD]):
                    return False

        # Create message container for SMTP
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

        logger.info(f"Email sent successfully to {to_email} via SMTP")
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
    frontend_url: Optional[str] = None,
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


async def send_low_stock_alert_email(
    to_email: str, items: list[dict], frontend_url: Optional[str] = None
) -> bool:
    """Send low stock alert email with list of items needing restocking."""
    if frontend_url is None:
        frontend_url = settings.FRONTEND_URL

    if not is_email_configured():
        logger.warning("Email not configured. Skipping low stock alert email.")
        return False

    subject = f"Low Stock Alert - {len(items)} Item(s) Need Restocking"

    items_text = "\n".join(
        [
            f"- {item['name']}: {item['quantity']} left (threshold: {item['low_stock_threshold']})"
            for item in items
        ]
    )

    body = f"""
Hello,

You have {len(items)} inventory item(s) that are below their stock threshold:

{items_text}

Please consider restocking these items soon.

Best regards,
Inventory Management Team
"""

    items_html = "\n".join(
        [
            f"""
            <tr>
                <td style="padding: 12px; border-bottom: 1px solid #f0f0f0;">{item['name']}</td>
                <td style="padding: 12px; border-bottom: 1px solid #f0f0f0; text-align: center;">{item['quantity']}</td>
                <td style="padding: 12px; border-bottom: 1px solid #f0f0f0; text-align: center;">{item['low_stock_threshold']}</td>
                <td style="padding: 12px; border-bottom: 1px solid #f0f0f0;">{item.get('category', 'Uncategorised')}</td>
            </tr>
            """
            for item in items
        ]
    )

    html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 700px; margin: 0 auto; padding: 20px; }}
        .alert {{ background-color: #FEF3C7; border-left: 4px solid #F59E0B; padding: 15px; margin: 20px 0; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th {{ background-color: #F59E0B; color: white; padding: 12px; text-align: left; }}
        .btn {{ display: inline-block; padding: 12px 24px; background-color: #F59E0B; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
        .footer {{ margin-top: 30px; font-size: 12px; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <h2>Low Stock Alert</h2>
        <div class="alert">
            <strong>Attention:</strong> You have {len(items)} inventory item(s) that need restocking.
        </div>
        <table>
            <thead>
                <tr>
                    <th>Item Name</th>
                    <th style="text-align: center;">Current Stock</th>
                    <th style="text-align: center;">Threshold</th>
                    <th>Category</th>
                </tr>
            </thead>
            <tbody>
{items_html}
            </tbody>
        </table>
        <a href="{frontend_url}/inventory?filter=low_stock" class="btn">View Inventory</a>
        <div class="footer">
            <p>This is an automated alert. Please restock these items to maintain optimal inventory levels.</p>
            <p>Best regards,<br>Inventory Management Team</p>
        </div>
    </div>
</body>
</html>
"""

    return await send_email(to_email, subject, body, html_body)


async def send_critical_stock_alert_email(
    to_email: str, items: list[dict], frontend_url: Optional[str] = None
) -> bool:
    """Send critical stock alert email for items at critically low levels."""
    if frontend_url is None:
        frontend_url = settings.FRONTEND_URL

    if not is_email_configured():
        logger.warning("Email not configured. Skipping critical stock alert email.")
        return False

    subject = f"CRITICAL Stock Alert - {len(items)} Item(s) Urgently Need Restocking"

    items_text = "\n".join(
        [
            f"- {item['name']}: Only {item['quantity']} left! (threshold: {item['low_stock_threshold']})"
            for item in items
        ]
    )

    body = f"""
URGENT ACTION REQUIRED

You have {len(items)} inventory item(s) in CRITICAL stock condition:

{items_text}

These items are at or below 50% of their stock threshold. Please restock immediately.

Best regards,
Inventory Management Team
"""

    items_html = "\n".join(
        [
            f"""
            <tr style="background-color: #FEE2E2;">
                <td style="padding: 12px; border-bottom: 1px solid #f0f0f0; font-weight: bold;">{item['name']}</td>
                <td style="padding: 12px; border-bottom: 1px solid #f0f0f0; text-align: center; color: #DC2626; font-weight: bold;">{item['quantity']}</td>
                <td style="padding: 12px; border-bottom: 1px solid #f0f0f0; text-align: center;">{item['low_stock_threshold']}</td>
                <td style="padding: 12px; border-bottom: 1px solid #f0f0f0;">{item.get('category', 'Uncategorised')}</td>
            </tr>
            """
            for item in items
        ]
    )

    html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 700px; margin: 0 auto; padding: 20px; }}
        .critical-alert {{ background-color: #FEE2E2; border-left: 4px solid #DC2626; padding: 15px; margin: 20px 0; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th {{ background-color: #DC2626; color: white; padding: 12px; text-align: left; }}
        .btn {{ display: inline-block; padding: 12px 24px; background-color: #DC2626; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
        .footer {{ margin-top: 30px; font-size: 12px; color: #666; }}
        .urgent {{ color: #DC2626; font-weight: bold; font-size: 18px; }}
    </style>
</head>
<body>
    <div class="container">
        <h2>CRITICAL Stock Alert</h2>
        <div class="critical-alert">
            <p class="urgent">URGENT ACTION REQUIRED</p>
            <strong>Critical:</strong> You have {len(items)} inventory item(s) at critically low levels.
        </div>
        <table>
            <thead>
                <tr>
                    <th>Item Name</th>
                    <th style="text-align: center;">Current Stock</th>
                    <th style="text-align: center;">Threshold</th>
                    <th>Category</th>
                </tr>
            </thead>
            <tbody>
{items_html}
            </tbody>
        </table>
        <a href="{frontend_url}/inventory?filter=critical_stock" class="btn">Restock Now</a>
        <div class="footer">
            <p style="color: #DC2626; font-weight: bold;">These items require immediate attention to prevent stockouts.</p>
            <p>Best regards,<br>Inventory Management Team</p>
        </div>
    </div>
</body>
</html>
"""

    return await send_email(to_email, subject, body, html_body)
