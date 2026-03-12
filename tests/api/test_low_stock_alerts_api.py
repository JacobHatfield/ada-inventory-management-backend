"""API tests for low stock alerts endpoints."""

from unittest.mock import AsyncMock, patch

from fastapi import status

from app.models.inventory import InventoryItem


class TestLowStockItemsAPI:
    """Tests for the low stock items endpoint."""

    def test_get_low_stock_items_returns_sorted(
        self, client, auth_headers, db, test_user, other_user
    ):
        """Return only low stock items for the current user, sorted by quantity."""
        items = [
            InventoryItem(
                name="Critical",
                quantity=3,
                low_stock_threshold=10,
                user_id=test_user.id,
            ),
            InventoryItem(
                name="Low",
                quantity=7,
                low_stock_threshold=10,
                user_id=test_user.id,
            ),
            InventoryItem(
                name="Healthy",
                quantity=20,
                low_stock_threshold=10,
                user_id=test_user.id,
            ),
            InventoryItem(
                name="No Threshold",
                quantity=2,
                low_stock_threshold=None,
                user_id=test_user.id,
            ),
            InventoryItem(
                name="Other User Low",
                quantity=2,
                low_stock_threshold=10,
                user_id=other_user.id,
            ),
        ]
        db.add_all(items)
        db.commit()

        response = client.get("/api/v1/inventory/low-stock", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert [item["name"] for item in data] == ["Critical", "Low"]
        assert all(item["user_id"] == test_user.id for item in data)
        assert data[0]["is_low_stock"] is True
        assert data[0]["stock_status"] == "critical"
        assert data[1]["stock_status"] == "low"

    def test_get_low_stock_items_unauthenticated(self, client):
        """Authentication is required."""
        response = client.get("/api/v1/inventory/low-stock")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestCriticalStockItemsAPI:
    """Tests for the critical stock items endpoint."""

    def test_get_critical_stock_items_default_percentage(
        self, client, auth_headers, db, test_user
    ):
        """Return items at or below 50% of threshold by default."""
        items = [
            InventoryItem(
                name="Critical Low",
                quantity=3,
                low_stock_threshold=10,
                user_id=test_user.id,
            ),
            InventoryItem(
                name="Critical Edge",
                quantity=5,
                low_stock_threshold=10,
                user_id=test_user.id,
            ),
            InventoryItem(
                name="Low Only",
                quantity=7,
                low_stock_threshold=10,
                user_id=test_user.id,
            ),
        ]
        db.add_all(items)
        db.commit()

        response = client.get("/api/v1/inventory/critical-stock", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert [item["name"] for item in data] == ["Critical Low", "Critical Edge"]

    def test_get_critical_stock_items_custom_percentage(
        self, client, auth_headers, db, test_user
    ):
        """Allow custom critical threshold percentages."""
        items = [
            InventoryItem(
                name="Critical Low",
                quantity=3,
                low_stock_threshold=10,
                user_id=test_user.id,
            ),
            InventoryItem(
                name="Now Critical",
                quantity=7,
                low_stock_threshold=10,
                user_id=test_user.id,
            ),
        ]
        db.add_all(items)
        db.commit()

        response = client.get(
            "/api/v1/inventory/critical-stock?threshold_percentage=0.7",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert [item["name"] for item in data] == ["Critical Low", "Now Critical"]

    def test_get_critical_stock_items_unauthenticated(self, client):
        """Authentication is required."""
        response = client.get("/api/v1/inventory/critical-stock")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestStockSummaryAPI:
    """Tests for the stock summary endpoint."""

    def test_get_stock_summary_counts(self, client, auth_headers, db, test_user):
        """Return counts for each stock status bucket."""
        items = [
            InventoryItem(
                name="Out",
                quantity=0,
                low_stock_threshold=10,
                user_id=test_user.id,
            ),
            InventoryItem(
                name="Critical",
                quantity=5,
                low_stock_threshold=10,
                user_id=test_user.id,
            ),
            InventoryItem(
                name="Low",
                quantity=7,
                low_stock_threshold=10,
                user_id=test_user.id,
            ),
            InventoryItem(
                name="Healthy",
                quantity=20,
                low_stock_threshold=10,
                user_id=test_user.id,
            ),
            InventoryItem(
                name="No Threshold",
                quantity=1,
                low_stock_threshold=None,
                user_id=test_user.id,
            ),
        ]
        db.add_all(items)
        db.commit()

        response = client.get("/api/v1/inventory/stock-summary", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_items"] == 5
        assert data["out_of_stock"] == 1
        assert data["critical_stock"] == 1
        assert data["low_stock"] == 1
        assert data["healthy_stock"] == 2

    def test_get_stock_summary_unauthenticated(self, client):
        """Authentication is required."""
        response = client.get("/api/v1/inventory/stock-summary")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestAlertCheckAPI:
    """Tests for the alert check endpoint."""

    def test_check_alerts_success(self, client, auth_headers):
        """Return alert check results on success."""
        result = {
            "success": True,
            "low_stock_sent": True,
            "critical_stock_sent": False,
            "low_stock_count": 1,
            "critical_stock_count": 0,
            "message": "Sent",
        }

        with patch(
            "app.api.v1.inventory.alert_service.check_and_notify_low_stock",
            new_callable=AsyncMock,
            return_value=result,
        ):
            response = client.post(
                "/api/v1/inventory/alerts/check", headers=auth_headers
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data == result

    def test_check_alerts_failure(self, client, auth_headers):
        """Return 500 when the service reports failure."""
        result = {"success": False, "error": "boom"}

        with patch(
            "app.api.v1.inventory.alert_service.check_and_notify_low_stock",
            new_callable=AsyncMock,
            return_value=result,
        ):
            response = client.post(
                "/api/v1/inventory/alerts/check", headers=auth_headers
            )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json()["detail"] == "boom"

    def test_check_alerts_unauthenticated(self, client):
        """Authentication is required."""
        response = client.post("/api/v1/inventory/alerts/check")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
