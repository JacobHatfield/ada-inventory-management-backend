"""Unit tests for pagination utilities."""

import pytest

from app.utils.pagination import (
    calculate_total_pages,
    page_to_offset,
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

