"""Inventory management API routes."""

import logging
from typing import Annotated, Literal, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.dependencies import get_current_active_user
from app.models.user import User
from app.schemas.audit import AuditLogResponse
from app.schemas.inventory import (
    AlertCheckResponse,
    InventoryItemCreate,
    InventoryItemResponse,
    InventoryItemUpdate,
    StockSummaryResponse,
    StockUpdate,
)
from app.services import alert_service, audit_service, inventory_service
from app.utils.pagination import (
    PaginatedResponse,
    calculate_total_pages,
    get_pagination_params,
)

router = APIRouter(prefix="/inventory", tags=["inventory"])
logger = logging.getLogger(__name__)


async def check_low_stock_background(user_id: int):
    """Background task to check low stock alerts."""
    db = SessionLocal()
    try:
        await alert_service.check_and_notify_low_stock(db, user_id)
    except Exception as e:
        logger.error(f"Failed to check low stock alerts for user {user_id}: {e}")
    finally:
        db.close()


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
    """Get inventory items with filters and pagination."""
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


@router.get("/low-stock", response_model=list[InventoryItemResponse])
def get_low_stock_items(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Get items at or below low stock threshold."""
    items = inventory_service.get_low_stock_items(db, current_user.id)
    return items


@router.get("/critical-stock", response_model=list[InventoryItemResponse])
def get_critical_stock_items(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    threshold_percentage: float = Query(
        0.5, ge=0, le=1, description="Critical threshold percentage (default 0.5 = 50%)"
    ),
):
    """Get critically low inventory items."""
    items = inventory_service.get_critical_stock_items(
        db, current_user.id, threshold_percentage
    )
    return items


@router.get("/stock-summary", response_model=StockSummaryResponse)
def get_stock_summary(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Get summary of stock status for all inventory items."""
    items = inventory_service.get_user_inventory_items(
        db, current_user.id, category_id=None, search=None, stock_status=None
    )

    summary = {
        "total_items": len(items),
        "out_of_stock": 0,
        "critical_stock": 0,
        "low_stock": 0,
        "healthy_stock": 0,
    }

    for item in items:
        status = (
            "out_of_stock"
            if item.quantity == 0
            else (
                "critical"
                if item.low_stock_threshold
                and item.quantity <= item.low_stock_threshold * 0.5
                else (
                    "low"
                    if item.low_stock_threshold
                    and item.quantity <= item.low_stock_threshold
                    else "healthy"
                )
            )
        )

        if status == "out_of_stock":
            summary["out_of_stock"] += 1
        elif status == "critical":
            summary["critical_stock"] += 1
        elif status == "low":
            summary["low_stock"] += 1
        else:
            summary["healthy_stock"] += 1

    return StockSummaryResponse(**summary)


@router.post("/alerts/check", response_model=AlertCheckResponse)
async def check_low_stock_alerts(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Manually trigger low stock alert check."""
    result = await alert_service.check_and_notify_low_stock(db, current_user.id)

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error", "Failed to check low stock alerts"),
        )

    return AlertCheckResponse(
        success=result["success"],
        low_stock_sent=result.get("low_stock_sent", False),
        critical_stock_sent=result.get("critical_stock_sent", False),
        low_stock_count=result.get("low_stock_count", 0),
        critical_stock_count=result.get("critical_stock_count", 0),
        message=result.get("message"),
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
async def update_inventory_item(
    item_id: int,
    item_data: InventoryItemUpdate,
    background_tasks: BackgroundTasks,
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

        # Check if quantity was decreased, trigger alert check in background
        if item_data.quantity is not None and inventory_service.check_low_stock(item):
            background_tasks.add_task(check_low_stock_background, current_user.id)

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
async def decrement_stock(
    item_id: int,
    stock_update: StockUpdate,
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
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

        # Always check for low stock alerts after decrementing
        if inventory_service.check_low_stock(item):
            background_tasks.add_task(check_low_stock_background, current_user.id)

        return item
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/{item_id}/audit-history", response_model=PaginatedResponse[AuditLogResponse]
)
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
    """Get audit history for an inventory item."""
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
