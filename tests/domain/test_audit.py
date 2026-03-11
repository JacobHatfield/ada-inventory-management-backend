"""Audit logging domain tests."""

import json
import time

import pytest

from app.models.audit import AuditLog
from app.services import audit_service, inventory_service
from app.schemas.inventory import InventoryItemCreate, InventoryItemUpdate


class TestAuditServiceFunctions:
    """Test audit service functions directly."""

    def test_create_audit_log_success(self, db, test_user, test_inventory_item):
        """Test creating an audit log with all required fields."""
        audit_log = audit_service.create_audit_log(
            db=db,
            inventory_item_id=test_inventory_item.id,
            user_id=test_user.id,
            action="created",
        )

        assert audit_log.id is not None
        assert audit_log.inventory_item_id == test_inventory_item.id
        assert audit_log.user_id == test_user.id
        assert audit_log.action == "created"
        assert audit_log.timestamp is not None

    def test_create_audit_log_with_all_fields(self, db, test_user, test_inventory_item):
        """Test creating an audit log with all optional fields."""
        audit_log = audit_service.create_audit_log(
            db=db,
            inventory_item_id=test_inventory_item.id,
            user_id=test_user.id,
            action="updated",
            field_name="quantity",
            old_value="100",
            new_value="150",
        )

        assert audit_log.id is not None
        assert audit_log.action == "updated"
        assert audit_log.field_name == "quantity"
        assert audit_log.old_value == "100"
        assert audit_log.new_value == "150"

    def test_get_audit_logs_for_item_returns_sorted(
        self, db, test_user, test_inventory_item
    ):
        """Test that audit logs are returned sorted by timestamp (newest first)."""
        import time
        
        # Create multiple audit logs with slight delays to ensure different timestamps
        audit_service.create_audit_log(
            db, test_inventory_item.id, test_user.id, "created"
        )
        time.sleep(0.01)  # Small delay to ensure different timestamp
        audit_service.create_audit_log(
            db, test_inventory_item.id, test_user.id, "updated"
        )
        time.sleep(0.01)
        audit_service.create_audit_log(
            db, test_inventory_item.id, test_user.id, "stock_increased"
        )

        logs = audit_service.get_audit_logs_for_item(db, test_inventory_item.id)

        assert len(logs) == 3
        # Verify logs are sorted by timestamp descending (newest first)
        # Timestamps should be in descending order
        assert logs[0].timestamp >= logs[1].timestamp >= logs[2].timestamp

    def test_get_audit_logs_for_item_pagination(
        self, db, test_user, test_inventory_item
    ):
        """Test pagination of audit logs."""
        # Create 10 audit logs
        for i in range(10):
            audit_service.create_audit_log(
                db, test_inventory_item.id, test_user.id, f"action_{i}"
            )

        # Get first page (5 items)
        logs_page1 = audit_service.get_audit_logs_for_item(
            db, test_inventory_item.id, skip=0, limit=5
        )
        assert len(logs_page1) == 5

        # Get second page (5 items)
        logs_page2 = audit_service.get_audit_logs_for_item(
            db, test_inventory_item.id, skip=5, limit=5
        )
        assert len(logs_page2) == 5

        # Verify no overlap
        page1_ids = [log.id for log in logs_page1]
        page2_ids = [log.id for log in logs_page2]
        assert len(set(page1_ids) & set(page2_ids)) == 0

    def test_get_audit_logs_count_for_item(self, db, test_user, test_inventory_item):
        """Test getting total count of audit logs for an item."""
        # Create 7 audit logs
        for i in range(7):
            audit_service.create_audit_log(
                db, test_inventory_item.id, test_user.id, f"action_{i}"
            )

        count = audit_service.get_audit_logs_count_for_item(db, test_inventory_item.id)
        assert count == 7

    def test_get_audit_logs_for_user(self, db, test_user, test_inventory_item):
        """Test getting audit logs filtered by user."""
        # Create logs for test_user
        audit_service.create_audit_log(
            db, test_inventory_item.id, test_user.id, "created"
        )
        audit_service.create_audit_log(
            db, test_inventory_item.id, test_user.id, "updated"
        )

        logs = audit_service.get_audit_logs_for_user(db, test_user.id)

        assert len(logs) >= 2
        for log in logs:
            assert log.user_id == test_user.id

    def test_get_audit_logs_count_for_user(self, db, test_user, test_inventory_item):
        """Test getting total count of audit logs created by a user."""
        # Create 5 audit logs
        for i in range(5):
            audit_service.create_audit_log(
                db, test_inventory_item.id, test_user.id, f"action_{i}"
            )

        count = audit_service.get_audit_logs_count_for_user(db, test_user.id)
        assert count == 5


class TestItemCreationAudit:
    """Test audit logging during item creation."""

    def test_create_item_generates_audit_log(self, db, test_user):
        """Test that creating an item generates an audit log."""
        item_data = InventoryItemCreate(
            name="New Widget",
            description="A newly created widget",
            quantity=50,
            low_stock_threshold=5,
        )

        item = inventory_service.create_inventory_item(db, item_data, test_user.id)

        # Check audit log was created
        logs = db.query(AuditLog).filter(AuditLog.inventory_item_id == item.id).all()
        assert len(logs) == 1

    def test_create_item_audit_log_content(self, db, test_user):
        """Test that the audit log contains correct information."""
        item_data = InventoryItemCreate(
            name="Logged Widget",
            description="Testing audit content",
            quantity=75,
            low_stock_threshold=10,
        )

        item = inventory_service.create_inventory_item(db, item_data, test_user.id)

        # Get the audit log
        log = (
            db.query(AuditLog)
            .filter(AuditLog.inventory_item_id == item.id)
            .first()
        )

        assert log is not None
        assert log.user_id == test_user.id
        assert log.inventory_item_id == item.id
        assert log.new_value is not None
        
        # Parse JSON content
        log_data = json.loads(log.new_value)
        assert log_data["name"] == "Logged Widget"
        assert log_data["quantity"] == 75

    def test_create_item_audit_log_has_correct_action(self, db, test_user):
        """Test that creation audit log has 'created' action."""
        item_data = InventoryItemCreate(
            name="Action Test Widget",
            quantity=100,
        )

        item = inventory_service.create_inventory_item(db, item_data, test_user.id)

        log = (
            db.query(AuditLog)
            .filter(AuditLog.inventory_item_id == item.id)
            .first()
        )

        assert log.action == "created"

    def test_create_multiple_items_generates_multiple_logs(self, db, test_user):
        """Test that creating multiple items generates separate audit logs."""
        items_data = [
            InventoryItemCreate(name=f"Widget {i}", quantity=i * 10)
            for i in range(1, 4)
        ]

        items = [
            inventory_service.create_inventory_item(db, data, test_user.id)
            for data in items_data
        ]

        # Check each item has its own audit log
        for item in items:
            logs = (
                db.query(AuditLog)
                .filter(AuditLog.inventory_item_id == item.id)
                .all()
            )
            assert len(logs) == 1
            assert logs[0].action == "created"


class TestItemUpdateAudit:
    """Test audit logging during item updates."""

    def test_update_item_generates_audit_log(self, db, test_user, test_inventory_item):
        """Test that updating an item generates audit logs."""
        update_data = InventoryItemUpdate(name="Updated Widget")

        inventory_service.update_inventory_item(
            db, test_inventory_item.id, update_data, test_user.id
        )

        # Check audit log was created
        logs = (
            db.query(AuditLog)
            .filter(AuditLog.inventory_item_id == test_inventory_item.id)
            .all()
        )
        assert len(logs) >= 1

    def test_update_item_logs_each_field_change(self, db, test_user, test_inventory_item):
        """Test that each field update creates a separate audit log."""
        update_data = InventoryItemUpdate(
            name="New Name",
            description="New Description",
            quantity=200,
        )

        inventory_service.update_inventory_item(
            db, test_inventory_item.id, update_data, test_user.id
        )

        # Get all audit logs for this item
        logs = (
            db.query(AuditLog)
            .filter(AuditLog.inventory_item_id == test_inventory_item.id)
            .all()
        )

        # Should have 3 logs (one for each changed field)
        assert len(logs) == 3

        # Verify each field has a log
        field_names = [log.field_name for log in logs]
        assert "name" in field_names
        assert "description" in field_names
        assert "quantity" in field_names

    def test_update_item_no_log_if_no_change(self, db, test_user, test_inventory_item):
        """Test that updating with the same values doesn't create audit logs."""
        # Update with current values
        update_data = InventoryItemUpdate(
            name=test_inventory_item.name,
            quantity=test_inventory_item.quantity,
        )

        inventory_service.update_inventory_item(
            db, test_inventory_item.id, update_data, test_user.id
        )

        # No audit logs should be created
        logs = (
            db.query(AuditLog)
            .filter(AuditLog.inventory_item_id == test_inventory_item.id)
            .all()
        )
        assert len(logs) == 0

    def test_update_multiple_fields_generates_multiple_logs(
        self, db, test_user, test_inventory_item
    ):
        """Test that updating multiple fields generates multiple logs."""
        update_data = InventoryItemUpdate(
            name="Double Update",
            low_stock_threshold=15,
        )

        inventory_service.update_inventory_item(
            db, test_inventory_item.id, update_data, test_user.id
        )

        logs = (
            db.query(AuditLog)
            .filter(AuditLog.inventory_item_id == test_inventory_item.id)
            .all()
        )

        # Should have 2 logs
        assert len(logs) == 2
        assert all(log.action == "updated" for log in logs)

    def test_update_item_captures_old_and_new_values(
        self, db, test_user, test_inventory_item
    ):
        """Test that update logs capture both old and new values."""
        original_name = test_inventory_item.name
        new_name = "Completely New Name"

        update_data = InventoryItemUpdate(name=new_name)

        inventory_service.update_inventory_item(
            db, test_inventory_item.id, update_data, test_user.id
        )

        # Get the name update log
        log = (
            db.query(AuditLog)
            .filter(
                AuditLog.inventory_item_id == test_inventory_item.id,
                AuditLog.field_name == "name",
            )
            .first()
        )

        assert log is not None
        assert log.old_value == original_name
        assert log.new_value == new_name


class TestStockAdjustmentAudit:
    """Test audit logging during stock adjustments."""

    def test_increment_stock_generates_audit_log(
        self, db, test_user, test_inventory_item
    ):
        """Test that incrementing stock creates an audit log."""
        inventory_service.adjust_stock_quantity(
            db, test_inventory_item.id, 50, test_user.id
        )

        logs = (
            db.query(AuditLog)
            .filter(AuditLog.inventory_item_id == test_inventory_item.id)
            .all()
        )
        assert len(logs) == 1

    def test_increment_stock_has_correct_action(
        self, db, test_user, test_inventory_item
    ):
        """Test that stock increment has 'stock_increased' action."""
        inventory_service.adjust_stock_quantity(
            db, test_inventory_item.id, 25, test_user.id
        )

        log = (
            db.query(AuditLog)
            .filter(AuditLog.inventory_item_id == test_inventory_item.id)
            .first()
        )

        assert log.action == "stock_increased"

    def test_increment_stock_logs_old_and_new_quantity(
        self, db, test_user, test_inventory_item
    ):
        """Test that increment logs capture old and new quantities."""
        original_quantity = test_inventory_item.quantity
        change_amount = 30

        inventory_service.adjust_stock_quantity(
            db, test_inventory_item.id, change_amount, test_user.id
        )

        log = (
            db.query(AuditLog)
            .filter(AuditLog.inventory_item_id == test_inventory_item.id)
            .first()
        )

        assert log.old_value == str(original_quantity)
        assert str(original_quantity + change_amount) in log.new_value

    def test_increment_with_reason_stores_reason(
        self, db, test_user, test_inventory_item
    ):
        """Test that increment with reason stores the reason in the log."""
        reason = "New shipment from supplier"

        inventory_service.adjust_stock_quantity(
            db, test_inventory_item.id, 100, test_user.id, reason=reason
        )

        log = (
            db.query(AuditLog)
            .filter(AuditLog.inventory_item_id == test_inventory_item.id)
            .first()
        )

        assert log.new_value is not None
        # Reason should be in the new_value (as JSON)
        log_data = json.loads(log.new_value)
        assert log_data["reason"] == reason

    def test_decrement_stock_generates_audit_log(
        self, db, test_user, test_inventory_item
    ):
        """Test that decrementing stock creates an audit log."""
        inventory_service.adjust_stock_quantity(
            db, test_inventory_item.id, -20, test_user.id
        )

        logs = (
            db.query(AuditLog)
            .filter(AuditLog.inventory_item_id == test_inventory_item.id)
            .all()
        )
        assert len(logs) == 1

    def test_decrement_stock_has_correct_action(
        self, db, test_user, test_inventory_item
    ):
        """Test that stock decrement has 'stock_decreased' action."""
        inventory_service.adjust_stock_quantity(
            db, test_inventory_item.id, -15, test_user.id
        )

        log = (
            db.query(AuditLog)
            .filter(AuditLog.inventory_item_id == test_inventory_item.id)
            .first()
        )

        assert log.action == "stock_decreased"

    def test_decrement_stock_logs_old_and_new_quantity(
        self, db, test_user, test_inventory_item
    ):
        """Test that decrement logs capture old and new quantities."""
        original_quantity = test_inventory_item.quantity
        change_amount = -25

        inventory_service.adjust_stock_quantity(
            db, test_inventory_item.id, change_amount, test_user.id
        )

        log = (
            db.query(AuditLog)
            .filter(AuditLog.inventory_item_id == test_inventory_item.id)
            .first()
        )

        assert log.old_value == str(original_quantity)
        assert str(original_quantity + change_amount) in log.new_value

    def test_decrement_with_reason_stores_reason(
        self, db, test_user, test_inventory_item
    ):
        """Test that decrement with reason stores the reason in the log."""
        reason = "Product sold to customer"

        inventory_service.adjust_stock_quantity(
            db, test_inventory_item.id, -10, test_user.id, reason=reason
        )

        log = (
            db.query(AuditLog)
            .filter(AuditLog.inventory_item_id == test_inventory_item.id)
            .first()
        )

        assert log.new_value is not None
        # Reason should be in the new_value (as JSON)
        log_data = json.loads(log.new_value)
        assert log_data["reason"] == reason


