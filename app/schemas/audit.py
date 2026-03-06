"""Audit log schemas for tracking inventory changes."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    """Schema for audit log entries returned in responses."""
    id: int
    inventory_item_id: int
    user_id: int
    action: str
    field_name: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)
