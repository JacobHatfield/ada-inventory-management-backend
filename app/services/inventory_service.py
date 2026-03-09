"""Inventory management service for CRUD operations."""

from typing import List, Optional

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models.inventory import InventoryItem
from app.schemas.inventory import InventoryItemCreate, InventoryItemUpdate


def create_inventory_item(
    db: Session, item_data: InventoryItemCreate, user_id: int
) -> InventoryItem:
    """Create a new inventory item for the authenticated user."""
    # Validate quantity is non-negative
    if item_data.quantity < 0:
        raise ValueError("Quantity cannot be negative")

    # Create item with user association
    db_item = InventoryItem(
        name=item_data.name,
        description=item_data.description,
        quantity=item_data.quantity,
        low_stock_threshold=item_data.low_stock_threshold,
        category_id=item_data.category_id,
        user_id=user_id,
    )

    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


def get_user_inventory_items(
    db: Session,
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    category_id: Optional[int] = None,
    search: Optional[str] = None,
    stock_status: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> List[InventoryItem]:
    """Get all inventory items for a user with optional search, filters, and sorting."""
    # Build base query filtered by user
    query = db.query(InventoryItem).filter(InventoryItem.user_id == user_id)

    # Add category filter if provided
    if category_id is not None:
        query = query.filter(InventoryItem.category_id == category_id)

    # Add search filter if provided (case-insensitive name search)
    if search:
        query = query.filter(InventoryItem.name.ilike(f"%{search}%"))

    # Add stock status filter if provided
    if stock_status:
        if stock_status == "out_of_stock":
            # Items with zero quantity
            query = query.filter(InventoryItem.quantity == 0)
        elif stock_status == "low_stock":
            # Items with quantity > 0 but below threshold
            query = query.filter(
                and_(
                    InventoryItem.quantity > 0,
                    InventoryItem.quantity < InventoryItem.low_stock_threshold,
                )
            )
        elif stock_status == "in_stock":
            # Items with quantity at or above threshold (or > 0 if no threshold)
            query = query.filter(
                or_(
                    InventoryItem.quantity >= InventoryItem.low_stock_threshold,
                    and_(
                        InventoryItem.quantity > 0,
                        InventoryItem.low_stock_threshold.is_(None),
                    ),
                )
            )

    # Apply sorting
    sort_column = getattr(InventoryItem, sort_by, InventoryItem.created_at)
    if sort_order == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    # Apply pagination and return
    return query.offset(skip).limit(limit).all()


def get_inventory_item_by_id(
    db: Session, item_id: int, user_id: int
) -> Optional[InventoryItem]:
    """Get a single inventory item by ID, verifying ownership."""
    # Query item with user ownership verification
    return (
        db.query(InventoryItem)
        .filter(InventoryItem.id == item_id, InventoryItem.user_id == user_id)
        .first()
    )


def update_inventory_item(
    db: Session, item_id: int, item_data: InventoryItemUpdate, user_id: int
) -> Optional[InventoryItem]:
    """Update an inventory item, verifying ownership."""
    # Get item with ownership check
    db_item = get_inventory_item_by_id(db, item_id, user_id)
    if not db_item:
        return None

    # Validate quantity if being updated
    if item_data.quantity is not None and item_data.quantity < 0:
        raise ValueError("Quantity cannot be negative")

    # Update fields that are provided (exclude_unset for partial updates)
    update_data = item_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_item, field, value)

    db.commit()
    db.refresh(db_item)
    return db_item


def delete_inventory_item(db: Session, item_id: int, user_id: int) -> bool:
    """Delete an inventory item, verifying ownership."""
    # Get item with ownership check
    db_item = get_inventory_item_by_id(db, item_id, user_id)
    if not db_item:
        return False

    # Delete item (cascade will handle audit logs)
    db.delete(db_item)
    db.commit()
    return True
