"""Alert service for low stock notifications."""

import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User
from app.services import email_service, inventory_service

logger = logging.getLogger(__name__)


async def check_and_notify_low_stock(db: Session, user_id: int) -> dict:
    """Check all items for a user and send low stock alerts if needed."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        logger.error(f"User {user_id} not found for low stock check")
        return {"success": False, "error": "User not found"}

    return await notify_user_low_stock(db, user)


async def notify_user_low_stock(db: Session, user: User) -> dict:
    """Send low stock notifications to a specific user."""
    low_stock_items = inventory_service.get_low_stock_items(db, user.id)

    if not low_stock_items:
        return {
            "success": True,
            "low_stock_sent": False,
            "critical_stock_sent": False,
            "message": "No low stock items found",
        }

    critical_items = inventory_service.get_critical_stock_items(
        db, user.id, threshold_percentage=0.5
    )

    low_only_items = [item for item in low_stock_items if item not in critical_items]

    result = {
        "success": True,
        "low_stock_sent": False,
        "critical_stock_sent": False,
        "low_stock_count": len(low_only_items),
        "critical_stock_count": len(critical_items),
    }

    if critical_items:
        critical_data = [
            {
                "name": item.name,
                "quantity": item.quantity,
                "low_stock_threshold": item.low_stock_threshold,
                "category": item.category.name if item.category else "Uncategorized",
            }
            for item in critical_items
        ]

        try:
            sent = await email_service.send_critical_stock_alert_email(
                to_email=user.email,
                items=critical_data,
                frontend_url=settings.FRONTEND_URL,
            )
            result["critical_stock_sent"] = sent
            if sent:
                logger.info(
                    f"Sent critical stock alert to {user.email} for {len(critical_items)} items"
                )
        except Exception as e:
            logger.error(f"Failed to send critical stock alert to {user.email}: {e}")
            result["critical_error"] = str(e)

    if low_only_items:
        low_data = [
            {
                "name": item.name,
                "quantity": item.quantity,
                "low_stock_threshold": item.low_stock_threshold,
                "category": item.category.name if item.category else "Uncategorized",
            }
            for item in low_only_items
        ]

        try:
            sent = await email_service.send_low_stock_alert_email(
                to_email=user.email, items=low_data, frontend_url=settings.FRONTEND_URL
            )
            result["low_stock_sent"] = sent
            if sent:
                logger.info(
                    f"Sent low stock alert to {user.email} for {len(low_only_items)} items"
                )
        except Exception as e:
            logger.error(f"Failed to send low stock alert to {user.email}: {e}")
            result["low_error"] = str(e)

    return result


async def check_and_notify_all_users(db: Session) -> dict:
    """Check and notify all active users about their low stock items."""
    users = db.query(User).filter(User.is_active == True).all()

    results = {
        "total_users": len(users),
        "users_notified": 0,
        "total_low_stock": 0,
        "total_critical_stock": 0,
    }

    for user in users:
        try:
            result = await notify_user_low_stock(db, user)
            if result["success"] and (
                result["low_stock_sent"] or result["critical_stock_sent"]
            ):
                results["users_notified"] += 1
                results["total_low_stock"] += result.get("low_stock_count", 0)
                results["total_critical_stock"] += result.get("critical_stock_count", 0)
        except Exception as e:
            logger.error(f"Failed to check/notify user {user.id}: {e}")

    return results
