"""Category management API routes."""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_active_user
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate
from app.services import category_service
from app.utils.pagination import (
    PaginatedResponse,
    calculate_total_pages,
    get_pagination_params,
)

router = APIRouter(prefix="/categories", tags=["categories"])


@router.post("/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    category_data: CategoryCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Create a new category for the authenticated user."""
    category = category_service.create_category(db, category_data, current_user.id)
    return category


@router.get("/", response_model=PaginatedResponse[CategoryResponse])
def get_categories(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    page: Optional[int] = Query(None, ge=1, description="Page number (1-indexed)"),
    page_size: Optional[int] = Query(
        None, ge=1, description="Number of items per page"
    ),
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=100, description="Number of items per page"),
):
    """Get all categories for the authenticated user with pagination metadata."""
    # Get pagination parameters (supports both page/page_size and skip/limit)
    offset, final_page_size = get_pagination_params(
        page=page, skip=skip, limit=limit, page_size=page_size
    )

    # Get categories and total count
    categories = category_service.get_user_categories(
        db, current_user.id, offset, final_page_size
    )
    total = category_service.get_user_categories_count(db, current_user.id)

    # Calculate pagination metadata
    total_pages = calculate_total_pages(total, final_page_size)
    current_page = (offset // final_page_size) + 1 if offset >= 0 else 1

    return {
        "items": categories,
        "total": total,
        "page": current_page,
        "page_size": final_page_size,
        "total_pages": total_pages,
    }


@router.get("/{category_id}", response_model=CategoryResponse)
def get_category(
    category_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Get a single category by ID."""
    category = category_service.get_category_by_id(db, category_id, current_user.id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )
    return category


@router.put("/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: int,
    category_data: CategoryUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Update a category."""
    category = category_service.update_category(
        db, category_id, category_data, current_user.id
    )
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )
    return category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Delete a category. Will fail if category has associated inventory items."""
    try:
        success = category_service.delete_category(db, category_id, current_user.id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found",
            )
        return None
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
