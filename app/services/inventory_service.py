"""Inventory management service for CRUD operations."""

import json
from typing import List, Optional

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models.inventory import InventoryItem
from app.schemas.inventory import InventoryItemCreate, InventoryItemUpdate
from app.services import audit_service


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

    # Log item creation
    audit_service.create_audit_log(
        db=db,
        inventory_item_id=db_item.id,
        user_id=user_id,
        action="created",
        new_value=json.dumps({
            "name": db_item.name,
            "quantity": db_item.quantity,
            "description": db_item.description,
            "category_id": db_item.category_id,
            "low_stock_threshold": db_item.low_stock_threshold,
        }),
    )

    return db_item


def _build_inventory_query(
    db: Session,
    user_id: int,
    category_id: Optional[int] = None,
    search: Optional[str] = None,
    stock_status: Optional[str] = None,
):
    """Build base query with filters for inventory items."""
    query = db.query(InventoryItem).filter(InventoryItem.user_id == user_id)

    if category_id is not None:
        query = query.filter(InventoryItem.category_id == category_id)

    if search:
        query = query.filter(InventoryItem.name.ilike(f"%{search}%"))

    if stock_status:
        if stock_status == "out_of_stock":
            query = query.filter(InventoryItem.quantity == 0)
        elif stock_status == "low_stock":
            query = query.filter(
                and_(
                    InventoryItem.quantity > 0,
                    InventoryItem.quantity < InventoryItem.low_stock_threshold,
                )
            )
        elif stock_status == "in_stock":
            query = query.filter(
                or_(
                    InventoryItem.quantity >= InventoryItem.low_stock_threshold,
                    and_(
                        InventoryItem.quantity > 0,
                        InventoryItem.low_stock_threshold.is_(None),
                    ),
                )
            )

    return query


def get_user_inventory_items_count(
    db: Session,
    user_id: int,
    category_id: Optional[int] = None,
    search: Optional[str] = None,
    stock_status: Optional[str] = None,
) -> int:
    """Get total count of inventory items for a user with filters applied."""
    query = _build_inventory_query(db, user_id, category_id, search, stock_status)
    return query.count()


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
    query = _build_inventory_query(db, user_id, category_id, search, stock_status)

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
        old_value = getattr(db_item, field)
        if old_value != value:
            # Log each field change
            audit_service.create_audit_log(
                db=db,
                inventory_item_id=db_item.id,
                user_id=user_id,
                action="updated",
                field_name=field,
                old_value=str(old_value) if old_value is not None else None,
                new_value=str(value) if value is not None else None,
            )
        setattr(db_item, field, value)

    db.commit()
    db.refresh(db_item)
    return db_item


def adjust_stock_quantity(
    db: Session,
    item_id: int,
    quantity_change: int,
    user_id: int,
    reason: Optional[str] = None,
) -> Optional[InventoryItem]:
    """Adjust inventory item quantity, preventing negative stock. Returns None if item not found, raises ValueError if would result in negative quantity."""
    # Get item with ownership verification
    db_item = get_inventory_item_by_id(db, item_id, user_id)
    if not db_item:
        return None
    
    # Calculate new quantity
    old_quantity = db_item.quantity
    new_quantity = old_quantity + quantity_change
    
    # Validate that new quantity is not negative
    if new_quantity < 0:
        raise ValueError(
            f"Cannot adjust quantity: would result in negative stock "
            f"(current: {old_quantity}, change: {quantity_change})"
        )
    
    # Update the quantity
    db_item.quantity = new_quantity
    
    # Determine action type
    action = "stock_increased" if quantity_change > 0 else "stock_decreased"
    
    # Log stock adjustment
    audit_service.create_audit_log(
        db=db,
        inventory_item_id=db_item.id,
        user_id=user_id,
        action=action,
        field_name="quantity",
        old_value=str(old_quantity),
        new_value=str(new_quantity) if reason is None else json.dumps({
            "quantity": new_quantity,
            "reason": reason,
        }),
    )
    
    db.commit()
    db.refresh(db_item)
    return db_item


def delete_inventory_item(db: Session, item_id: int, user_id: int) -> bool:
    """Delete an inventory item, verifying ownership."""
    # Get item with ownership check
    db_item = get_inventory_item_by_id(db, item_id, user_id)
    if not db_item:
        return False

    # Log deletion before removing item
    audit_service.create_audit_log(
        db=db,
        inventory_item_id=db_item.id,
        user_id=user_id,
        action="deleted",
        old_value=json.dumps({
            "name": db_item.name,
            "quantity": db_item.quantity,
            "description": db_item.description,
            "category_id": db_item.category_id,
        }),
    )

    # Delete item (cascade will handle audit logs)
    db.delete(db_item)
    db.commit()
    return True
