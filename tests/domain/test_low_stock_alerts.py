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


class TestGetLowStockItems:
    """Test retrieving all low stock items for a user."""

    def test_get_low_stock_items_returns_items_at_threshold(self, db, test_user):
        """Test that items at threshold are included."""
        item = InventoryItem(
            name="Low Stock Item",
            quantity=10,
            low_stock_threshold=10,
            user_id=test_user.id,
        )
        db.add(item)
        db.commit()

        items = inventory_service.get_low_stock_items(db, test_user.id)
        assert len(items) == 1
        assert items[0].name == "Low Stock Item"

    def test_get_low_stock_items_returns_items_below_threshold(self, db, test_user):
        """Test that items below threshold are included."""
        item = InventoryItem(
            name="Low Stock Item",
            quantity=5,
            low_stock_threshold=10,
            user_id=test_user.id,
        )
        db.add(item)
        db.commit()

        items = inventory_service.get_low_stock_items(db, test_user.id)
        assert len(items) == 1

    def test_get_low_stock_items_excludes_items_above_threshold(self, db, test_user):
        """Test that items above threshold are excluded."""
        item1 = InventoryItem(
            name="Healthy Item",
            quantity=20,
            low_stock_threshold=10,
            user_id=test_user.id,
        )
        item2 = InventoryItem(
            name="Low Stock Item",
            quantity=5,
            low_stock_threshold=10,
            user_id=test_user.id,
        )
        db.add_all([item1, item2])
        db.commit()

        items = inventory_service.get_low_stock_items(db, test_user.id)
        assert len(items) == 1
        assert items[0].name == "Low Stock Item"

    def test_get_low_stock_items_excludes_items_without_threshold(self, db, test_user):
        """Test that items with no threshold are excluded."""
        item1 = InventoryItem(
            name="No Threshold Item",
            quantity=5,
            low_stock_threshold=None,
            user_id=test_user.id,
        )
        item2 = InventoryItem(
            name="Low Stock Item",
            quantity=5,
            low_stock_threshold=10,
            user_id=test_user.id,
        )
        db.add_all([item1, item2])
        db.commit()

        items = inventory_service.get_low_stock_items(db, test_user.id)
        assert len(items) == 1
        assert items[0].name == "Low Stock Item"

    def test_get_low_stock_items_sorts_by_quantity_asc(self, db, test_user):
        """Test that results are sorted by quantity ascending."""
        item1 = InventoryItem(
            name="Item A", quantity=8, low_stock_threshold=10, user_id=test_user.id
        )
        item2 = InventoryItem(
            name="Item B", quantity=3, low_stock_threshold=10, user_id=test_user.id
        )
        item3 = InventoryItem(
            name="Item C", quantity=5, low_stock_threshold=10, user_id=test_user.id
        )
        db.add_all([item1, item2, item3])
        db.commit()

        items = inventory_service.get_low_stock_items(db, test_user.id)
        assert len(items) == 3
        assert items[0].quantity == 3
        assert items[1].quantity == 5
        assert items[2].quantity == 8

    def test_get_low_stock_items_only_returns_user_items(
        self, db, test_user, other_user
    ):
        """Test that only the specified user's items are returned."""
        item1 = InventoryItem(
            name="User 1 Item",
            quantity=5,
            low_stock_threshold=10,
            user_id=test_user.id,
        )
        item2 = InventoryItem(
            name="User 2 Item",
            quantity=5,
            low_stock_threshold=10,
            user_id=other_user.id,
        )
        db.add_all([item1, item2])
        db.commit()

        items = inventory_service.get_low_stock_items(db, test_user.id)
        assert len(items) == 1
        assert items[0].name == "User 1 Item"
        assert items[0].user_id == test_user.id

    def test_get_low_stock_items_returns_empty_when_no_low_stock(self, db, test_user):
        """Test that empty list is returned when no items are low stock."""
        item = InventoryItem(
            name="Healthy Item",
            quantity=50,
            low_stock_threshold=10,
            user_id=test_user.id,
        )
        db.add(item)
        db.commit()

        items = inventory_service.get_low_stock_items(db, test_user.id)
        assert len(items) == 0


class TestGetCriticalStockItems:
    """Test retrieving critically low stock items."""

    def test_get_critical_stock_items_with_default_threshold(self, db, test_user):
        """Test critical items at default 50% threshold."""
        item1 = InventoryItem(
            name="Critical Item",
            quantity=4,
            low_stock_threshold=10,
            user_id=test_user.id,
        )
        item2 = InventoryItem(
            name="Low Item",
            quantity=7,
            low_stock_threshold=10,
            user_id=test_user.id,
        )
        db.add_all([item1, item2])
        db.commit()

        items = inventory_service.get_critical_stock_items(db, test_user.id)
        assert len(items) == 1
        assert items[0].name == "Critical Item"

    def test_get_critical_stock_items_with_custom_threshold(self, db, test_user):
        """Test critical items with custom threshold percentage."""
        item1 = InventoryItem(
            name="Item A", quantity=2, low_stock_threshold=10, user_id=test_user.id
        )
        item2 = InventoryItem(
            name="Item B", quantity=6, low_stock_threshold=10, user_id=test_user.id
        )
        db.add_all([item1, item2])
        db.commit()

        items = inventory_service.get_critical_stock_items(
            db, test_user.id, threshold_percentage=0.3
        )
        assert len(items) == 1
        assert items[0].name == "Item A"

    def test_get_critical_stock_items_at_exact_threshold(self, db, test_user):
        """Test item at exactly the critical threshold percentage."""
        item = InventoryItem(
            name="Critical Item",
            quantity=5,
            low_stock_threshold=10,
            user_id=test_user.id,
        )
        db.add(item)
        db.commit()

        items = inventory_service.get_critical_stock_items(db, test_user.id)
        assert len(items) == 1

    def test_get_critical_stock_items_excludes_non_critical(self, db, test_user):
        """Test that non-critical low stock items are excluded."""
        item1 = InventoryItem(
            name="Critical Item",
            quantity=3,
            low_stock_threshold=10,
            user_id=test_user.id,
        )
        item2 = InventoryItem(
            name="Low Item",
            quantity=8,
            low_stock_threshold=10,
            user_id=test_user.id,
        )
        item3 = InventoryItem(
            name="Healthy Item",
            quantity=20,
            low_stock_threshold=10,
            user_id=test_user.id,
        )
        db.add_all([item1, item2, item3])
        db.commit()

        items = inventory_service.get_critical_stock_items(db, test_user.id)
        assert len(items) == 1
        assert items[0].name == "Critical Item"

    def test_get_critical_stock_items_sorts_by_quantity(self, db, test_user):
        """Test that results are sorted by quantity ascending."""
        item1 = InventoryItem(
            name="Item A", quantity=4, low_stock_threshold=10, user_id=test_user.id
        )
        item2 = InventoryItem(
            name="Item B", quantity=1, low_stock_threshold=10, user_id=test_user.id
        )
        item3 = InventoryItem(
            name="Item C", quantity=3, low_stock_threshold=10, user_id=test_user.id
        )
        db.add_all([item1, item2, item3])
        db.commit()

        items = inventory_service.get_critical_stock_items(db, test_user.id)
        assert items[0].quantity == 1
        assert items[1].quantity == 3
        assert items[2].quantity == 4

    def test_get_critical_stock_items_only_returns_user_items(
        self, db, test_user, other_user
    ):
        """Test user isolation for critical stock items."""
        item1 = InventoryItem(
            name="User 1 Critical",
            quantity=3,
            low_stock_threshold=10,
            user_id=test_user.id,
        )
        item2 = InventoryItem(
            name="User 2 Critical",
            quantity=3,
            low_stock_threshold=10,
            user_id=other_user.id,
        )
        db.add_all([item1, item2])
        db.commit()

        items = inventory_service.get_critical_stock_items(db, test_user.id)
        assert len(items) == 1
        assert items[0].user_id == test_user.id
