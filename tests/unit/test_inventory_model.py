"""Unit tests for inventory model and schema."""
import pytest
from pydantic import ValidationError

from app.models.inventory import InventoryItem
from app.schemas.inventory import StockUpdate


class TestInventoryModel:
    """Test InventoryItem model properties."""

    def test_is_low_stock_with_none_threshold(self, db, test_user):
        """Test is_low_stock property when threshold is explicitly None."""
        item = InventoryItem(
            name="Test Item",
            description="Test Description",
            quantity=5,
            low_stock_threshold=None,  # Explicitly set to None (no default now)
            user_id=test_user.id,
        )
        db.add(item)
        db.commit()
        db.refresh(item)

        # Should return False when threshold is None
        assert item.low_stock_threshold is None
        assert item.is_low_stock is False

    def test_is_low_stock_below_threshold(self, db, test_user):
        """Test is_low_stock property when quantity is below threshold."""
        item = InventoryItem(
            name="Test Item",
            description="Test Description",
            quantity=5,
            low_stock_threshold=10,
            user_id=test_user.id,
        )
        db.add(item)
        db.commit()
        db.refresh(item)

        # Should return True when quantity <= threshold
        assert item.is_low_stock is True

    def test_is_low_stock_at_threshold(self, db, test_user):
        """Test is_low_stock property when quantity equals threshold."""
        item = InventoryItem(
            name="Test Item",
            description="Test Description",
            quantity=10,
            low_stock_threshold=10,
            user_id=test_user.id,
        )
        db.add(item)
        db.commit()
        db.refresh(item)

        # Should return True when quantity <= threshold
        assert item.is_low_stock is True

    def test_is_low_stock_above_threshold(self, db, test_user):
        """Test is_low_stock property when quantity is above threshold."""
        item = InventoryItem(
            name="Test Item",
            description="Test Description",
            quantity=15,
            low_stock_threshold=10,
            user_id=test_user.id,
        )
        db.add(item)
        db.commit()
        db.refresh(item)

        # Should return False when quantity > threshold
        assert item.is_low_stock is False


class TestStockUpdateSchema:
    """Test StockUpdate schema validators."""

    def test_validate_quantity_change_zero(self):
        """Test that quantity_change cannot be zero."""
        with pytest.raises(ValidationError) as exc_info:
            StockUpdate(quantity_change=0)

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "value_error"
        assert "cannot be zero" in str(errors[0]["ctx"]["error"])

    def test_validate_quantity_change_positive(self):
        """Test that positive quantity_change is valid."""
        stock_update = StockUpdate(quantity_change=10)
        assert stock_update.quantity_change == 10

    def test_validate_quantity_change_negative(self):
        """Test that negative quantity_change is valid."""
        stock_update = StockUpdate(quantity_change=-5)
        assert stock_update.quantity_change == -5
