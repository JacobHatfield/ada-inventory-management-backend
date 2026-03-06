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
