"""Pagination utilities for API endpoints."""

import math
from typing import Generic, List, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")

# Pagination constants
MIN_PAGE_SIZE = 1
MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 100


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response with items, total count, and page metadata."""

    items: List[T]
    total: int = Field(..., ge=0, description="Total number of items")
    page: int = Field(..., ge=1, description="Current page number (1-indexed)")
    page_size: int = Field(
        ..., ge=MIN_PAGE_SIZE, le=MAX_PAGE_SIZE, description="Items per page"
    )
    total_pages: int = Field(..., ge=0, description="Total number of pages")

    class Config:
        from_attributes = True


def calculate_total_pages(total_count: int, page_size: int) -> int:
    """Calculate total number of pages based on total count and page size."""
    if total_count <= 0:
        return 0
    if page_size <= 0:
        raise ValueError("page_size must be greater than 0")
    return math.ceil(total_count / page_size)


def get_pagination_params(
    page: int | None = None,
    skip: int | None = None,
    limit: int | None = None,
    page_size: int | None = None,
) -> tuple[int, int]:
    """Validate and normalize pagination parameters, returns (offset, limit)."""
    # Determine the limit (page_size takes precedence over limit)
    final_limit = page_size or limit or DEFAULT_PAGE_SIZE

    # Validate limit is within bounds
    if final_limit < MIN_PAGE_SIZE:
        final_limit = MIN_PAGE_SIZE
    elif final_limit > MAX_PAGE_SIZE:
        final_limit = MAX_PAGE_SIZE

    # Calculate offset
    if page is not None:
        if page < 1:
            raise ValueError("page must be >= 1")
        offset = (page - 1) * final_limit
    else:
        offset = skip if skip is not None else 0
        if offset < 0:
            raise ValueError("skip must be >= 0")

    return offset, final_limit


def page_to_offset(page: int, page_size: int) -> int:
    """Convert page number (1-indexed) to offset (0-indexed)."""
    if page < 1:
        raise ValueError("page must be >= 1")
    if page_size < 1:
        raise ValueError("page_size must be >= 1")
    return (page - 1) * page_size


def offset_to_page(offset: int, page_size: int) -> int:
    """Convert offset (0-indexed) to page number (1-indexed)."""
    if offset < 0:
        raise ValueError("offset must be >= 0")
    if page_size < 1:
        raise ValueError("page_size must be >= 1")
    return (offset // page_size) + 1
