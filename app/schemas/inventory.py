"""Inventory item schemas for request/response validation."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from app.schemas.category import CategoryResponse


class InventoryItemBase(BaseModel):
    """Base inventory item schema with common fields."""

    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    quantity: int = Field(..., ge=0, description="Quantity must be non-negative")
    low_stock_threshold: Optional[int] = Field(default=10, ge=0)
    category_id: Optional[int] = None


class InventoryItemCreate(InventoryItemBase):
    """Schema for creating a new inventory item."""

    pass


class InventoryItemUpdate(BaseModel):
    """Schema for updating an inventory item."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    quantity: Optional[int] = Field(None, ge=0)
    low_stock_threshold: Optional[int] = Field(None, ge=0)
    category_id: Optional[int] = None


class StockUpdate(BaseModel):
    """Schema for stock increment/decrement operations."""

    quantity_change: int = Field(..., gt=0, description="Amount to add/remove (must be positive)")
    reason: Optional[str] = Field(None, max_length=200, description="Optional reason for stock change")

    @field_validator("quantity_change")
    @classmethod
    def validate_quantity_change(cls, v: int) -> int:
        if v == 0:
            raise ValueError("Quantity change cannot be zero")
        return v


class InventoryItemResponse(InventoryItemBase):
    """Schema for inventory item data returned in responses."""

    id: int
    user_id: int
    category: Optional[CategoryResponse] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def is_low_stock(self) -> bool:
        """Check if item is at or below low stock threshold."""
        if self.low_stock_threshold is None:
            return False
        return self.quantity <= self.low_stock_threshold

    @computed_field
    @property
    def stock_status(self) -> Literal["out_of_stock", "critical", "low", "healthy"]:
        """Determine stock status based on quantity and threshold."""
        if self.quantity == 0:
            return "out_of_stock"

        if self.low_stock_threshold is None:
            return "healthy"

        if self.quantity <= self.low_stock_threshold * 0.5:
            return "critical"
        elif self.quantity <= self.low_stock_threshold:
            return "low"
        else:
            return "healthy"


class StockSummaryResponse(BaseModel):
    """Schema for stock status summary statistics."""

    total_items: int
    out_of_stock: int
    critical_stock: int
    low_stock: int
    healthy_stock: int


class AlertCheckResponse(BaseModel):
    """Schema for alert check response."""

    success: bool
    low_stock_sent: bool
    critical_stock_sent: bool
    low_stock_count: int
    critical_stock_count: int
    message: Optional[str] = None
