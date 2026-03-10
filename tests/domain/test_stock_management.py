from app.services import inventory_service


class TestStockIncrement:
    """Test stock increment business logic."""

    def test_increment_stock_increases_quantity(
        self, db, test_user, test_inventory_item
    ):
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

    def test_decrement_stock_decreases_quantity(
        self, db, test_user, test_inventory_item
    ):
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


class TestNegativeStockPrevention:
    """Test the critical business rule: prevent negative stock."""

    def test_prevent_negative_stock_basic(self, db, test_user, test_inventory_item):
        """Test that stock cannot go negative."""
        test_inventory_item.quantity = 5
        db.commit()

        import pytest

        with pytest.raises(ValueError, match="negative stock"):
            inventory_service.adjust_stock_quantity(
                db=db,
                item_id=test_inventory_item.id,
                quantity_change=-10,
                user_id=test_user.id,
            )

        # Verify quantity was not changed (transaction rolled back)
        db.refresh(test_inventory_item)
        assert test_inventory_item.quantity == 5

    def test_prevent_negative_stock_by_one(self, db, test_user, test_inventory_item):
        """Test edge case: attempting to go negative by one."""
        test_inventory_item.quantity = 10
        db.commit()

        import pytest

        with pytest.raises(ValueError, match="negative stock"):
            inventory_service.adjust_stock_quantity(
                db, test_inventory_item.id, -11, test_user.id
            )

        db.refresh(test_inventory_item)
        assert test_inventory_item.quantity == 10

    def test_prevent_negative_from_zero(self, db, test_user, test_inventory_item):
        """Test that stock cannot go negative from zero."""
        test_inventory_item.quantity = 0
        db.commit()

        import pytest

        with pytest.raises(ValueError, match="negative stock"):
            inventory_service.adjust_stock_quantity(
                db, test_inventory_item.id, -1, test_user.id
            )

        db.refresh(test_inventory_item)
        assert test_inventory_item.quantity == 0

    def test_error_message_includes_details(self, db, test_user, test_inventory_item):
        """Test that error message includes current and attempted quantities."""
        test_inventory_item.quantity = 8
        db.commit()

        import pytest

        with pytest.raises(ValueError) as exc_info:
            inventory_service.adjust_stock_quantity(
                db, test_inventory_item.id, -15, test_user.id
            )

        error_message = str(exc_info.value)
        assert "8" in error_message  # Current quantity
        assert "-15" in error_message  # Attempted change


class TestLowStockDetection:
    """Test low stock threshold detection logic."""

    def test_is_low_stock_below_threshold(self, db, test_user):
        """Test item is flagged as low stock when below threshold."""
        from app.models.inventory import InventoryItem

        item = InventoryItem(
            name="Low Stock Item",
            quantity=5,
            low_stock_threshold=10,
            user_id=test_user.id,
        )
        db.add(item)
        db.commit()
        db.refresh(item)

        assert item.is_low_stock is True

    def test_is_low_stock_at_threshold(self, db, test_user):
        """Test item is flagged as low stock when at threshold."""
        from app.models.inventory import InventoryItem

        item = InventoryItem(
            name="At Threshold Item",
            quantity=10,
            low_stock_threshold=10,
            user_id=test_user.id,
        )
        db.add(item)
        db.commit()
        db.refresh(item)

        assert item.is_low_stock is True

    def test_is_not_low_stock_above_threshold(self, db, test_user):
        """Test item is not flagged as low stock when above threshold."""
        from app.models.inventory import InventoryItem

        item = InventoryItem(
            name="Good Stock Item",
            quantity=15,
            low_stock_threshold=10,
            user_id=test_user.id,
        )
        db.add(item)
        db.commit()
        db.refresh(item)

        assert item.is_low_stock is False

    def test_is_not_low_stock_when_no_threshold(self, db, test_user):
        """Test item is not flagged as low stock when threshold is not set."""
        from app.models.inventory import InventoryItem

        item = InventoryItem(
            name="No Threshold Item",
            quantity=1,
            low_stock_threshold=None,
            user_id=test_user.id,
        )
        db.add(item)
        db.commit()
        db.refresh(item)

        assert item.is_low_stock is False

    def test_is_not_low_stock_zero_quantity_no_threshold(self, db, test_user):
        """Test zero quantity with no threshold is not flagged as low stock."""
        from app.models.inventory import InventoryItem

        item = InventoryItem(
            name="Zero No Threshold",
            quantity=0,
            low_stock_threshold=None,
            user_id=test_user.id,
        )
        db.add(item)
        db.commit()
        db.refresh(item)

        assert item.is_low_stock is False


class TestLowStockThresholdChanges:
    """Test how stock status changes relative to threshold."""

    def test_decrement_triggers_low_stock_status(
        self, db, test_user, test_inventory_item
    ):
        """Test that decrementing below threshold triggers low stock status."""
        test_inventory_item.quantity = 12
        test_inventory_item.low_stock_threshold = 10
        db.commit()

        # Initially not low stock
        db.refresh(test_inventory_item)
        assert test_inventory_item.is_low_stock is False

        # Decrement below threshold
        result = inventory_service.adjust_stock_quantity(
            db, test_inventory_item.id, -5, test_user.id
        )

        assert result.quantity == 7
        assert result.is_low_stock is True

    def test_increment_removes_low_stock_status(
        self, db, test_user, test_inventory_item
    ):
        """Test that incrementing above threshold removes low stock status."""
        test_inventory_item.quantity = 8
        test_inventory_item.low_stock_threshold = 10
        db.commit()

        # Initially low stock
        db.refresh(test_inventory_item)
        assert test_inventory_item.is_low_stock is True

        # Increment above threshold
        result = inventory_service.adjust_stock_quantity(
            db, test_inventory_item.id, 5, test_user.id
        )

        assert result.quantity == 13
        assert result.is_low_stock is False


class TestStockOwnershipValidation:
    """Test that stock operations respect user ownership."""

    def test_cannot_adjust_other_user_item(
        self, db, test_user, other_user, test_inventory_item
    ):
        """Test that users cannot adjust stock for items they don't own."""
        original_quantity = test_inventory_item.quantity

        result = inventory_service.adjust_stock_quantity(
            db=db,
            item_id=test_inventory_item.id,
            quantity_change=10,
            user_id=other_user.id,  # Different user
        )

        assert result is None

        # Verify quantity was not changed
        db.refresh(test_inventory_item)
        assert test_inventory_item.quantity == original_quantity

    def test_adjust_nonexistent_item_returns_none(self, db, test_user):
        """Test that adjusting non-existent item returns None."""
        result = inventory_service.adjust_stock_quantity(
            db=db,
            item_id=999999,  # Non-existent
            quantity_change=10,
            user_id=test_user.id,
        )

        assert result is None


class TestStockReasonTracking:
    """Test optional reason parameter for stock adjustments."""

    def test_adjust_with_reason(self, db, test_user, test_inventory_item):
        """Test that stock can be adjusted with a reason provided."""
        result = inventory_service.adjust_stock_quantity(
            db=db,
            item_id=test_inventory_item.id,
            quantity_change=15,
            user_id=test_user.id,
            reason="Quarterly restock",
        )

        assert result is not None
        # Reason is logged but doesn't affect the item itself
        # (would be in audit logs in future implementation)

    def test_adjust_without_reason(self, db, test_user, test_inventory_item):
        """Test that stock can be adjusted without a reason (optional)."""
        result = inventory_service.adjust_stock_quantity(
            db=db,
            item_id=test_inventory_item.id,
            quantity_change=15,
            user_id=test_user.id,
            # No reason parameter
        )

        assert result is not None


class TestStockEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_adjust_stock_with_zero_initial_quantity(self, db, test_user):
        """Test adjusting stock for item with zero initial quantity."""
        from app.models.inventory import InventoryItem

        item = InventoryItem(
            name="Zero Stock Item",
            quantity=0,
            low_stock_threshold=10,
            user_id=test_user.id,
        )
        db.add(item)
        db.commit()
        db.refresh(item)

        result = inventory_service.adjust_stock_quantity(db, item.id, 5, test_user.id)

        assert result.quantity == 5

    def test_very_large_stock_quantities(self, db, test_user, test_inventory_item):
        """Test handling of very large stock quantities."""
        very_large_number = 1000000

        result = inventory_service.adjust_stock_quantity(
            db, test_inventory_item.id, very_large_number, test_user.id
        )

        assert result is not None
        assert result.quantity >= very_large_number

    def test_stock_threshold_zero(self, db, test_user):
        """Test low stock behavior when threshold is zero."""
        from app.models.inventory import InventoryItem

        item = InventoryItem(
            name="Zero Threshold Item",
            quantity=1,
            low_stock_threshold=0,
            user_id=test_user.id,
        )
        db.add(item)
        db.commit()
        db.refresh(item)

        # Quantity 1 is above threshold 0
        assert item.is_low_stock is False

        # At threshold
        item.quantity = 0
        db.commit()
        db.refresh(item)
        assert item.is_low_stock is True
