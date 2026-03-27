"""Category management service for CRUD operations."""

from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.inventory import InventoryItem
from app.schemas.category import CategoryCreate, CategoryUpdate


def create_category(
    db: Session, category_data: CategoryCreate, user_id: int
) -> Category:
    """Create a new category for the authenticated user."""
    # Create category with user association
    db_category = Category(
        name=category_data.name,
        description=category_data.description,
        user_id=user_id,
    )

    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category


def get_user_categories(
    db: Session, user_id: int, skip: int = 0, limit: int = 100
) -> List[Category]:
    """Get all categories for a specific user."""
    # Query categories filtered by user, ordered by name
    return (
        db.query(Category)
        .filter(Category.user_id == user_id)
        .order_by(Category.name)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_user_categories_count(db: Session, user_id: int) -> int:
    """Get total count of categories for a specific user."""
    return db.query(Category).filter(Category.user_id == user_id).count()


def get_category_by_id(
    db: Session, category_id: int, user_id: int
) -> Optional[Category]:
    """Get a single category by ID, verifying ownership."""
    # Query category with user ownership verification
    return (
        db.query(Category)
        .filter(Category.id == category_id, Category.user_id == user_id)
        .first()
    )


def update_category(
    db: Session, category_id: int, category_data: CategoryUpdate, user_id: int
) -> Optional[Category]:
    """Update a category, verifying ownership."""
    # Get category with ownership check
    db_category = get_category_by_id(db, category_id, user_id)
    if not db_category:
        return None

    # Update fields that are provided (exclude_unset for partial updates)
    update_data = category_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_category, field, value)

    db.commit()
    db.refresh(db_category)
    return db_category


def delete_category(db: Session, category_id: int, user_id: int) -> bool:
    """Delete a category."""
    # Get category with ownership check
    db_category = get_category_by_id(db, category_id, user_id)
    if not db_category:
        return False

    # Check if category has any inventory items
    item_count = (
        db.query(InventoryItem).filter(InventoryItem.category_id == category_id).count()
    )

    if item_count > 0:
        raise ValueError(
            "Cannot delete category with existing inventory items. "
            "Please reassign or delete items first."
        )

    # Delete category
    db.delete(db_category)
    db.commit()
    return True
