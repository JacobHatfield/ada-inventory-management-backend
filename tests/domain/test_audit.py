"""Audit logging domain tests."""

import json

import pytest

from app.models.audit import AuditLog
from app.services import audit_service, inventory_service
from app.schemas.inventory import InventoryItemCreate


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

