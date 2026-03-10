"""
Stock management domain logic tests
- Test stock increment logic
- Test stock increment validation
- Test stock decrement logic
- Test stock decrement validation
- Test prevent negative stock business rule
- Test stock update to zero
- Test low stock detection logic
- Test low stock threshold validation
- Test stock level alerts
- Test concurrent stock updates
- Test audit log creation on stock changes
Coverage target: >95%
"""

from app.services import inventory_service


class TestStockIncrement:
    """Test stock increment business logic."""

    def test_increment_stock_increases_quantity(self, db, test_user, test_inventory_item):
        """Test that incrementing stock increases the quantity correctly."""
        original_quantity = test_inventory_item.quantity
        increment_amount = 25

        result = inventory_service.adjust_stock_quantity(
            db=db,
            item_id=test_inventory_item.id,
            quantity_change=increment_amount,
            user_id=test_user.id,
            reason="New shipment arrived",
        )

        assert result is not None
        assert result.quantity == original_quantity + increment_amount

    def test_increment_large_stock_quantity(self, db, test_user, test_inventory_item):
        """Test incrementing with large quantities."""
        large_increment = 10000

        result = inventory_service.adjust_stock_quantity(
            db=db,
            item_id=test_inventory_item.id,
            quantity_change=large_increment,
            user_id=test_user.id,
        )

        assert result is not None
        assert result.quantity >= large_increment

    def test_increment_multiple_times(self, db, test_user, test_inventory_item):
        """Test multiple increments compound correctly."""
        original_quantity = test_inventory_item.quantity

        # First increment
        inventory_service.adjust_stock_quantity(
            db, test_inventory_item.id, 10, test_user.id
        )
        # Second increment
        inventory_service.adjust_stock_quantity(
            db, test_inventory_item.id, 15, test_user.id
        )
        # Third increment
        result = inventory_service.adjust_stock_quantity(
            db, test_inventory_item.id, 20, test_user.id
        )

        assert result.quantity == original_quantity + 10 + 15 + 20
