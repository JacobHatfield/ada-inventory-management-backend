"""Unit tests for inventory service layer."""

import pytest

from app.services import inventory_service


class TestInventoryServiceValidation:
    """Test service-layer validation for inventory operations."""

    def test_create_item_service_validates_negative_quantity(self, db, test_user):
        """Test that service layer catches negative quantity in create."""

        # Create a mock object that bypasses Pydantic validation
        # to test the service layer's defensive validation
        class MockItemData:
            name = "Test Item"
            description = "Mock data"
            quantity = -5  # Negative quantity
            low_stock_threshold = 10
            category_id = None

        with pytest.raises(ValueError, match="negative"):
            inventory_service.create_inventory_item(db, MockItemData(), test_user.id)

    def test_update_item_service_validates_negative_quantity(
        self, db, test_user, test_inventory_item
    ):
        """Test that service layer catches negative quantity in update."""

        # Create a mock object that bypasses Pydantic validation
        class MockUpdateData:
            quantity = -10  # Negative quantity
            name = None
            description = None
            low_stock_threshold = None
            category_id = None

            def model_dump(self, exclude_unset=False):
                return {"quantity": self.quantity}

        with pytest.raises(ValueError, match="negative"):
            inventory_service.update_inventory_item(
                db, test_inventory_item.id, MockUpdateData(), test_user.id
            )


class TestAdjustStockQuantity:
    """Test stock quantity adjustment functionality."""

    def test_increment_stock_successfully(self, db, test_user, test_inventory_item):
        """Test successfully incrementing stock quantity."""
        initial_quantity = test_inventory_item.quantity
        change = 10

        result = inventory_service.adjust_stock_quantity(
            db=db,
            item_id=test_inventory_item.id,
            quantity_change=change,
            user_id=test_user.id,
            reason="Restocking",
        )

        assert result is not None
        assert result.id == test_inventory_item.id
        assert result.quantity == initial_quantity + change

    def test_decrement_stock_successfully(self, db, test_user, test_inventory_item):
        """Test successfully decrementing stock quantity."""
        # Ensure item has sufficient stock
        test_inventory_item.quantity = 20
        db.commit()

        initial_quantity = test_inventory_item.quantity
        change = -5

        result = inventory_service.adjust_stock_quantity(
            db=db,
            item_id=test_inventory_item.id,
            quantity_change=change,
            user_id=test_user.id,
            reason="Sales",
        )

        assert result is not None
        assert result.quantity == initial_quantity + change
        assert result.quantity == 15

    def test_adjust_to_exactly_zero(self, db, test_user, test_inventory_item):
        """Test decrementing stock to exactly zero (should succeed)."""
        initial_quantity = 10
        test_inventory_item.quantity = initial_quantity
        db.commit()

        result = inventory_service.adjust_stock_quantity(
            db=db,
            item_id=test_inventory_item.id,
            quantity_change=-initial_quantity,
            user_id=test_user.id,
        )

        assert result is not None
        assert result.quantity == 0

    def test_prevent_negative_stock(self, db, test_user, test_inventory_item):
        """Test that adjustment prevents negative stock."""
        test_inventory_item.quantity = 5
        db.commit()

        with pytest.raises(ValueError, match="negative stock"):
            inventory_service.adjust_stock_quantity(
                db=db,
                item_id=test_inventory_item.id,
                quantity_change=-10,  # Would result in -5
                user_id=test_user.id,
            )

        # Verify quantity was not changed
        db.refresh(test_inventory_item)
        assert test_inventory_item.quantity == 5

    def test_adjust_nonexistent_item(self, db, test_user):
        """Test adjusting quantity of non-existent item returns None."""
        result = inventory_service.adjust_stock_quantity(
            db=db,
            item_id=99999,  # Non-existent ID
            quantity_change=10,
            user_id=test_user.id,
        )

        assert result is None

    def test_adjust_item_wrong_user(
        self, db, test_user, test_inventory_item, other_user
    ):
        """Test that user cannot adjust another user's item."""
        initial_quantity = test_inventory_item.quantity

        result = inventory_service.adjust_stock_quantity(
            db=db,
            item_id=test_inventory_item.id,
            quantity_change=10,
            user_id=other_user.id,  # Wrong user
        )

        assert result is None
        # Verify quantity was not changed
        db.refresh(test_inventory_item)
        assert test_inventory_item.quantity == initial_quantity

    def test_adjust_without_reason(self, db, test_user, test_inventory_item):
        """Test that reason parameter is optional."""
        initial_quantity = test_inventory_item.quantity

        result = inventory_service.adjust_stock_quantity(
            db=db,
            item_id=test_inventory_item.id,
            quantity_change=5,
            user_id=test_user.id,
            # No reason provided
        )

        assert result is not None
        assert result.quantity == initial_quantity + 5
