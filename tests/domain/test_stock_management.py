
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


class TestStockDecrement:
    """Test stock decrement business logic."""

    def test_decrement_stock_decreases_quantity(self, db, test_user, test_inventory_item):
        """Test that decrementing stock decreases the quantity correctly."""
        test_inventory_item.quantity = 50
        db.commit()

        decrement_amount = 20

        result = inventory_service.adjust_stock_quantity(
            db=db,
            item_id=test_inventory_item.id,
            quantity_change=-decrement_amount,
            user_id=test_user.id,
            reason="Sold products",
        )

        assert result is not None
        assert result.quantity == 30

    def test_decrement_exact_amount_to_zero(self, db, test_user, test_inventory_item):
        """Test decrementing to exactly zero is allowed."""
        test_inventory_item.quantity = 25
        db.commit()

        result = inventory_service.adjust_stock_quantity(
            db=db,
            item_id=test_inventory_item.id,
            quantity_change=-25,
            user_id=test_user.id,
        )

        assert result is not None
        assert result.quantity == 0

    def test_decrement_multiple_times(self, db, test_user, test_inventory_item):
        """Test multiple decrements compound correctly."""
        test_inventory_item.quantity = 100
        db.commit()

        # First decrement
        inventory_service.adjust_stock_quantity(
            db, test_inventory_item.id, -10, test_user.id
        )
        # Second decrement
        inventory_service.adjust_stock_quantity(
            db, test_inventory_item.id, -15, test_user.id
        )
        # Third decrement
        result = inventory_service.adjust_stock_quantity(
            db, test_inventory_item.id, -20, test_user.id
        )

        assert result.quantity == 100 - 10 - 15 - 20
        assert result.quantity == 55
