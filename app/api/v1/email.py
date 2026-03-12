"""Email API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_current_active_user
from app.models.user import User
from app.services import email_service

router = APIRouter(prefix="/email", tags=["email"])


@router.post("/test", status_code=status.HTTP_200_OK)
async def send_test_email_endpoint(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    # Send a test email to the authenticated user to verify email configuration
    if not email_service.is_email_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Email service is not configured. Please check SMTP settings.",
        )

    success = await email_service.send_test_email(current_user.email)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send test email. Check server logs for details.",
        )

    return {
        "message": f"Test email sent successfully to {current_user.email}",
        "email": current_user.email,
    }
