"""
Audit Log model
- AuditLog table definition
- Fields: id, item_id, user_id, action, old_value, new_value, timestamp
- Track all inventory changes for history
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class AuditLog(Base):
    """Audit Log model for tracking all inventory changes"""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    inventory_item_id = Column(Integer, ForeignKey("inventory_items.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    action = Column(String, nullable=False)  # e.g., 'created', 'updated', 'deleted', 'stock_increased', 'stock_decreased'
    field_name = Column(String, nullable=True)  # Which field was changed
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # Relationships
    inventory_item = relationship("InventoryItem", back_populates="audit_logs")
    user = relationship("User", back_populates="audit_logs")
