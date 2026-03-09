"""Inventory management API routes."""

from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_active_user
from app.models.user import User
from app.schemas.inventory import (InventoryItemCreate, InventoryItemResponse,
                                   InventoryItemUpdate)
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
    category_id: Optional[int] = None,
):
    """Get all inventory items for the authenticated user, optionally filtered by category."""
    items = inventory_service.get_user_inventory_items(
        db, current_user.id, skip, limit, category_id
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
