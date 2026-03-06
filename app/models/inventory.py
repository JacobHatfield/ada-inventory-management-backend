"""Inventory item model for tracking stock and products."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class InventoryItem(Base):
    """Inventory Item model for tracking products/stock"""

    __tablename__ = "inventory_items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    quantity = Column(Integer, nullable=False, default=0)
    low_stock_threshold = Column(Integer, nullable=True, default=10)
    category_id = Column(
        Integer,
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    user = relationship("User", back_populates="inventory_items")
    category = relationship("Category", back_populates="inventory_items")
    audit_logs = relationship(
        "AuditLog", back_populates="inventory_item", cascade="all, delete-orphan"
    )

    @property
    def is_low_stock(self) -> bool:
        """Check if item is below low stock threshold"""
        if self.low_stock_threshold is None:
            return False
        return self.quantity <= self.low_stock_threshold
