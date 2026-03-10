"""Inventory management API routes."""

from typing import Annotated, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_active_user
from app.models.user import User
from app.schemas.inventory import (
    InventoryItemCreate,
    InventoryItemResponse,
    InventoryItemUpdate,
    StockUpdate,
)
from app.services import inventory_service

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.post(
    "/", response_model=InventoryItemResponse, status_code=status.HTTP_201_CREATED
)
def create_inventory_item(
    item_data: InventoryItemCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Create a new inventory item for the authenticated user."""
    try:
        item = inventory_service.create_inventory_item(db, item_data, current_user.id)
        return item
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/", response_model=List[InventoryItemResponse])
def get_inventory_items(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    skip: int = 0,
    limit: int = 100,
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    search: Optional[str] = Query(
        None, description="Search items by name (case-insensitive)"
    ),
    stock_status: Optional[Literal["out_of_stock", "low_stock", "in_stock"]] = Query(
        None, description="Filter by stock status"
    ),
    sort_by: Literal["name", "quantity", "created_at", "updated_at"] = Query(
        "created_at", description="Field to sort by"
    ),
    sort_order: Literal["asc", "desc"] = Query("desc", description="Sort order"),
):
    """Get all inventory items with optional search, filters, and sorting."""
    items = inventory_service.get_user_inventory_items(
        db,
        current_user.id,
        skip,
        limit,
        category_id,
        search,
        stock_status,
        sort_by,
        sort_order,
    )
    return items


@router.get("/{item_id}", response_model=InventoryItemResponse)
def get_inventory_item(
    item_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Get a single inventory item by ID."""
    item = inventory_service.get_inventory_item_by_id(db, item_id, current_user.id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory item not found",
        )
    return item


@router.put("/{item_id}", response_model=InventoryItemResponse)
def update_inventory_item(
    item_id: int,
    item_data: InventoryItemUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Update an inventory item."""
    try:
        item = inventory_service.update_inventory_item(
            db, item_id, item_data, current_user.id
        )
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Inventory item not found",
            )
        return item
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_inventory_item(
    item_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Delete an inventory item."""
    success = inventory_service.delete_inventory_item(db, item_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory item not found",
        )
    return None


@router.post("/{item_id}/increment", response_model=InventoryItemResponse)
def increment_stock(
    item_id: int,
    stock_update: StockUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """
    Increment stock quantity for an inventory item.

    Add a specified amount to the current stock quantity.
    Optionally provide a reason for the stock change for audit purposes.
    """
    try:
        item = inventory_service.adjust_stock_quantity(
            db,
            item_id,
            stock_update.quantity_change,
            current_user.id,
            stock_update.reason,
        )
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Inventory item not found",
            )
        return item
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{item_id}/decrement", response_model=InventoryItemResponse)
def decrement_stock(
    item_id: int,
    stock_update: StockUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """
    Decrement stock quantity for an inventory item.

    Remove a specified amount from the current stock quantity.
    Prevents negative stock - returns 400 error if operation would result in negative quantity.
    Optionally provide a reason for the stock change for audit purposes.
    """
    try:
        item = inventory_service.adjust_stock_quantity(
            db,
            item_id,
            -stock_update.quantity_change,  # Negative to decrement
            current_user.id,
            stock_update.reason,
        )
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Inventory item not found",
            )
        return item
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
