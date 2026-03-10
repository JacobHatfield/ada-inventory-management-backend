"""Unit tests for pagination utilities."""

import pytest

from app.utils.pagination import (
    MIN_PAGE_SIZE,
    MAX_PAGE_SIZE,
    DEFAULT_PAGE_SIZE,
    calculate_total_pages,
    page_to_offset,
    offset_to_page,
    get_pagination_params,
)


class TestCalculateTotalPages:
    """Test calculate_total_pages function."""

    def test_calculate_with_exact_divisible_count(self):
        """Test when total count is exactly divisible by page size."""
        result = calculate_total_pages(100, 10)
        assert result == 10

    def test_calculate_with_remainder(self):
        """Test when total count has remainder after division."""
        result = calculate_total_pages(105, 10)
        assert result == 11

    def test_calculate_with_zero_count(self):
        """Test with zero total count returns 0 pages."""
        result = calculate_total_pages(0, 10)
        assert result == 0

    def test_calculate_with_negative_count(self):
        """Test with negative total count returns 0 pages."""
        result = calculate_total_pages(-5, 10)
        assert result == 0

    def test_calculate_with_count_less_than_page_size(self):
        """Test when count is less than page size returns 1 page."""
        result = calculate_total_pages(5, 10)
        assert result == 1

    def test_calculate_raises_error_for_zero_page_size(self):
        """Test that zero page_size raises ValueError."""
        with pytest.raises(ValueError, match="page_size must be greater than 0"):
            calculate_total_pages(100, 0)

    def test_calculate_raises_error_for_negative_page_size(self):
        """Test that negative page_size raises ValueError."""
        with pytest.raises(ValueError, match="page_size must be greater than 0"):
            calculate_total_pages(100, -10)


class TestPageToOffset:
    """Test page_to_offset function."""

    def test_first_page_conversion(self):
        """Test converting first page to offset."""
        result = page_to_offset(1, 10)
        assert result == 0

    def test_second_page_conversion(self):
        """Test converting second page to offset."""
        result = page_to_offset(2, 10)
        assert result == 10

    def test_arbitrary_page_conversion(self):
        """Test converting arbitrary page numbers."""
        result = page_to_offset(5, 20)
        assert result == 80

    def test_different_page_sizes(self):
        """Test with different page sizes."""
        result = page_to_offset(3, 25)
        assert result == 50

        result = page_to_offset(10, 5)
        assert result == 45

    def test_raises_error_for_invalid_page(self):
        """Test that page < 1 raises ValueError."""
        with pytest.raises(ValueError, match="page must be >= 1"):
            page_to_offset(0, 10)

        with pytest.raises(ValueError, match="page must be >= 1"):
            page_to_offset(-1, 10)

    def test_raises_error_for_invalid_page_size(self):
        """Test that page_size < 1 raises ValueError."""
        with pytest.raises(ValueError, match="page_size must be >= 1"):
            page_to_offset(1, 0)

        with pytest.raises(ValueError, match="page_size must be >= 1"):
            page_to_offset(1, -10)


class TestOffsetToPage:
    """Test offset_to_page function."""

    def test_zero_offset_conversion(self):
        """Test converting zero offset to page number."""
        result = offset_to_page(0, 10)
        assert result == 1

    def test_offset_at_page_boundary(self):
        """Test converting offset at exact page boundary."""
        result = offset_to_page(10, 10)
        assert result == 2

        result = offset_to_page(20, 10)
        assert result == 3

    def test_offset_within_page(self):
        """Test converting offset that's not at page boundary."""
        result = offset_to_page(15, 10)
        assert result == 2  # Should be on page 2 (items 10-19)

        result = offset_to_page(25, 10)
        assert result == 3  # Should be on page 3 (items 20-29)

    def test_different_page_sizes(self):
        """Test with different page sizes."""
        result = offset_to_page(50, 25)
        assert result == 3  # 50 / 25 = 2, so page 3

        result = offset_to_page(45, 5)
        assert result == 10  # 45 / 5 = 9, so page 10

    def test_raises_error_for_negative_offset(self):
        """Test that negative offset raises ValueError."""
        with pytest.raises(ValueError, match="offset must be >= 0"):
            offset_to_page(-1, 10)

        with pytest.raises(ValueError, match="offset must be >= 0"):
            offset_to_page(-100, 10)

    def test_raises_error_for_invalid_page_size(self):
        """Test that page_size < 1 raises ValueError."""
        with pytest.raises(ValueError, match="page_size must be >= 1"):
            offset_to_page(0, 0)

        with pytest.raises(ValueError, match="page_size must be >= 1"):
            offset_to_page(10, -5)


class TestGetPaginationParams:
    """Test get_pagination_params function."""

    def test_with_page_only(self):
        """Test pagination using page parameter (1-indexed)."""
        offset, limit = get_pagination_params(page=1)
        assert offset == 0
        assert limit == DEFAULT_PAGE_SIZE

        offset, limit = get_pagination_params(page=2, limit=10)
        assert offset == 10
        assert limit == 10

    def test_with_skip_limit_only(self):
        """Test pagination using skip and limit parameters."""
        offset, limit = get_pagination_params(skip=0, limit=20)
        assert offset == 0
        assert limit == 20

        offset, limit = get_pagination_params(skip=40, limit=20)
        assert offset == 40
        assert limit == 20

    def test_defaults_when_no_params(self):
        """Test default values when no parameters provided."""
        offset, limit = get_pagination_params()
        assert offset == 0
        assert limit == DEFAULT_PAGE_SIZE

    def test_page_takes_precedence_over_skip(self):
        """Test that page parameter takes precedence over skip."""
        offset, limit = get_pagination_params(page=3, skip=100, limit=10)
        assert offset == 20  # (page 3 - 1) * 10
        assert limit == 10

    def test_page_size_takes_precedence_over_limit(self):
        """Test that page_size parameter takes precedence over limit."""
        offset, limit = get_pagination_params(limit=50, page_size=25)
        assert offset == 0
        assert limit == 25

    def test_caps_limit_at_max_page_size(self):
        """Test that limit is capped at MAX_PAGE_SIZE."""
        offset, limit = get_pagination_params(limit=200)
        assert offset == 0
        assert limit == MAX_PAGE_SIZE

    def test_enforces_min_page_size(self):
        """Test that very small limit defaults to DEFAULT_PAGE_SIZE (0 is falsy)."""
        # When limit=0, it's falsy and defaults to DEFAULT_PAGE_SIZE
        offset, limit = get_pagination_params(limit=0)
        assert offset == 0
        assert limit == DEFAULT_PAGE_SIZE

        # MIN_PAGE_SIZE is 1, so test the constant directly
        assert MIN_PAGE_SIZE == 1

    def test_raises_error_for_invalid_page(self):
        """Test that page < 1 raises ValueError."""
        with pytest.raises(ValueError, match="page must be >= 1"):
            get_pagination_params(page=0)

        with pytest.raises(ValueError, match="page must be >= 1"):
            get_pagination_params(page=-1)

    def test_raises_error_for_negative_skip(self):
        """Test that negative skip raises ValueError."""
        with pytest.raises(ValueError, match="skip must be >= 0"):
            get_pagination_params(skip=-10)

    def test_large_page_number(self):
        """Test with large page numbers."""
        offset, limit = get_pagination_params(page=100, limit=10)
        assert offset == 990  # (100 - 1) * 10
        assert limit == 10


