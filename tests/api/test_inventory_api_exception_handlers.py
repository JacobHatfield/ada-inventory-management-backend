"""
Tests for exception handlers in inventory API endpoints.
These tests mock the service layer to trigger exception handling in the API layer.
"""

from unittest.mock import patch

from fastapi import status
from fastapi.testclient import TestClient

from app.models.user import User


class TestInventoryAPIExceptionHandlers:
    """Test exception handlers in inventory API layer."""

    @patch("app.api.v1.inventory.inventory_service.create_inventory_item")
    def test_create_item_service_raises_value_error(
        self, mock_create, client: TestClient, test_user: User, auth_headers: dict
    ):
        """Test that ValueError from service is caught and returns 400."""
        # Mock the service to raise ValueError
        mock_create.side_effect = ValueError("Service validation failed")

        response = client.post(
            "/api/v1/inventory/",
            json={
                "name": "Test Item",
                "sku": "TEST123",
                "quantity": 10,
                "unit_price": 50.00,
            },
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Service validation failed" in response.json()["detail"]

    @patch("app.api.v1.inventory.inventory_service.update_inventory_item")
    def test_update_item_service_raises_value_error(
        self, mock_update, client: TestClient, test_user: User, auth_headers: dict
    ):
        """Test that ValueError from service is caught and returns 400."""
        # Mock the service to raise ValueError
        mock_update.side_effect = ValueError("Service validation failed")

        response = client.put(
            "/api/v1/inventory/999",
            json={"quantity": 10},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Service validation failed" in response.json()["detail"]
