"""Inventory item schemas for request/response validation."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

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

    quantity_change: int = Field(
        ..., description="Positive to add, negative to subtract"
    )

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
    is_low_stock: bool
    category: Optional[CategoryResponse] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
