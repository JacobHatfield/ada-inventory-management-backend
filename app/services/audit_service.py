"""Audit service for inventory change tracking."""

from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def create_audit_log(
    db: Session,
    inventory_item_id: int,
    user_id: int,
    action: str,
    field_name: Optional[str] = None,
    old_value: Optional[str] = None,
    new_value: Optional[str] = None,
) -> AuditLog:
    """Create a new audit log entry."""
    audit_log = AuditLog(
        inventory_item_id=inventory_item_id,
        user_id=user_id,
        action=action,
        field_name=field_name,
        old_value=old_value,
        new_value=new_value,
    )

    db.add(audit_log)
    db.commit()
    db.refresh(audit_log)

    return audit_log


def get_audit_logs_for_item(
    db: Session,
    inventory_item_id: int,
    skip: int = 0,
    limit: int = 100,
) -> List[AuditLog]:
    """Get audit logs for an item."""
    return (
        db.query(AuditLog)
        .filter(AuditLog.inventory_item_id == inventory_item_id)
        .order_by(AuditLog.timestamp.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_audit_logs_count_for_item(
    db: Session,
    inventory_item_id: int,
) -> int:
    """Get total count of audit logs for an item."""
    return (
        db.query(AuditLog)
        .filter(AuditLog.inventory_item_id == inventory_item_id)
        .count()
    )


def get_audit_logs_for_user(
    db: Session,
    user_id: int,
    skip: int = 0,
    limit: int = 100,
) -> List[AuditLog]:
    """Get audit logs for a user."""
    return (
        db.query(AuditLog)
        .filter(AuditLog.user_id == user_id)
        .order_by(AuditLog.timestamp.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_audit_logs_count_for_user(
    db: Session,
    user_id: int,
) -> int:
    """Get total count of audit logs created by a user."""
    return db.query(AuditLog).filter(AuditLog.user_id == user_id).count()
