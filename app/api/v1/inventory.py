"""Inventory management API routes."""

from typing import Annotated, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_active_user
from app.models.user import User
from app.schemas.audit import AuditLogResponse
from app.schemas.inventory import (InventoryItemCreate, InventoryItemResponse,
                                   InventoryItemUpdate, StockUpdate)
from app.services import audit_service, inventory_service
from app.utils.pagination import (PaginatedResponse, calculate_total_pages,
                                  get_pagination_params)

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


@router.get("/", response_model=PaginatedResponse[InventoryItemResponse])
def get_inventory_items(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    page: Optional[int] = Query(None, ge=1, description="Page number (1-indexed)"),
    page_size: Optional[int] = Query(
        None, ge=1, description="Number of items per page"
    ),
    skip: int = Query(0, ge=0, description="Number of items to skip (offset)"),
    limit: int = Query(100, ge=1, le=100, description="Maximum items per page"),
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
    """Get all inventory items with pagination, search, filters, and sorting."""
    # Get pagination parameters (supports both page/page_size and skip/limit)
    offset, final_page_size = get_pagination_params(
        page=page, skip=skip, limit=limit, page_size=page_size
    )

    # Get total count with filters applied
    total_count = inventory_service.get_user_inventory_items_count(
        db, current_user.id, category_id, search, stock_status
    )

    # Get items for current page
    items = inventory_service.get_user_inventory_items(
        db,
        current_user.id,
        offset,
        final_page_size,
        category_id,
        search,
        stock_status,
        sort_by,
        sort_order,
    )

    # Calculate pagination metadata
    total_pages = calculate_total_pages(total_count, final_page_size)
    current_page = (offset // final_page_size) + 1 if offset >= 0 else 1

    return PaginatedResponse(
        items=items,
        total=total_count,
        page=current_page,
        page_size=final_page_size,
        total_pages=total_pages,
    )


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


@router.get("/{item_id}/audit-history", response_model=PaginatedResponse[AuditLogResponse])
def get_item_audit_history(
    item_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    page: Optional[int] = Query(None, ge=1, description="Page number (1-indexed)"),
    page_size: Optional[int] = Query(
        None, ge=1, description="Number of items per page"
    ),
    skip: int = Query(0, ge=0, description="Number of items to skip (offset)"),
    limit: int = Query(100, ge=1, le=100, description="Maximum items per page"),
):
    """Get audit history for an inventory item with pagination."""
    # Verify item exists and user owns it
    item = inventory_service.get_inventory_item_by_id(db, item_id, current_user.id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory item not found",
        )

    # Get pagination parameters
    offset, final_page_size = get_pagination_params(
        page=page, skip=skip, limit=limit, page_size=page_size
    )

    # Get total count of audit logs
    total_count = audit_service.get_audit_logs_count_for_item(db, item_id)

    # Get audit logs for current page
    audit_logs = audit_service.get_audit_logs_for_item(
        db, item_id, skip=offset, limit=final_page_size
    )

    # Calculate pagination metadata
    total_pages = calculate_total_pages(total_count, final_page_size)
    current_page = (offset // final_page_size) + 1 if offset >= 0 else 1

    return PaginatedResponse(
        items=audit_logs,
        total=total_count,
        page=current_page,
        page_size=final_page_size,
        total_pages=total_pages,
    )
