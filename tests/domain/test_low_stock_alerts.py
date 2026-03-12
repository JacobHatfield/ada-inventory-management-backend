"""Low stock alerts domain logic tests."""

import pytest
from unittest.mock import AsyncMock, patch

from app.models.category import Category
from app.models.inventory import InventoryItem
from app.models.user import User
from app.services import alert_service, inventory_service


class TestCheckLowStock:
    """Test low stock detection for individual items."""

    def test_check_low_stock_returns_true_when_at_threshold(self, db, test_user):
        """Test that item at threshold is considered low stock."""
        item = InventoryItem(
            name="Test Item",
            quantity=10,
            low_stock_threshold=10,
            user_id=test_user.id,
        )
        assert inventory_service.check_low_stock(item) is True

    def test_check_low_stock_returns_true_when_below_threshold(self, db, test_user):
        """Test that item below threshold is considered low stock."""
        item = InventoryItem(
            name="Test Item",
            quantity=5,
            low_stock_threshold=10,
            user_id=test_user.id,
        )
        assert inventory_service.check_low_stock(item) is True

    def test_check_low_stock_returns_false_when_above_threshold(self, db, test_user):
        """Test that item above threshold is not considered low stock."""
        item = InventoryItem(
            name="Test Item",
            quantity=15,
            low_stock_threshold=10,
            user_id=test_user.id,
        )
        assert inventory_service.check_low_stock(item) is False

    def test_check_low_stock_returns_false_when_threshold_is_none(
        self, db, test_user
    ):
        """Test that item with no threshold is not considered low stock."""
        item = InventoryItem(
            name="Test Item", quantity=5, low_stock_threshold=None, user_id=test_user.id
        )
        assert inventory_service.check_low_stock(item) is False

    def test_check_low_stock_returns_true_when_quantity_is_zero(self, db, test_user):
        """Test that out of stock item is considered low stock."""
        item = InventoryItem(
            name="Test Item",
            quantity=0,
            low_stock_threshold=10,
            user_id=test_user.id,
        )
        assert inventory_service.check_low_stock(item) is True
