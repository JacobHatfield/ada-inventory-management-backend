"""Inventory API endpoint tests."""
import pytest
from fastapi import status


class TestCreateInventoryItem:
    """Test creating inventory items."""

    def test_create_item_success(self, client, auth_headers, db):
        """Test successful inventory item creation."""
        response = client.post(
            "/api/v1/inventory/",
            json={
                "name": "New Widget",
                "description": "A brand new widget",
                "quantity": 50,
                "low_stock_threshold": 5,
            },
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "New Widget"
        assert data["description"] == "A brand new widget"
        assert data["quantity"] == 50
        assert data["low_stock_threshold"] == 5
        assert "id" in data
        assert "user_id" in data
        assert "created_at" in data

    def test_create_item_with_category(self, client, auth_headers, db, test_user):
        """Test creating item with category association."""
        # First create a category
        from app.models.category import Category

        category = Category(
            name="Electronics", description="Electronic items", user_id=test_user.id
        )
        db.add(category)
        db.commit()
        db.refresh(category)

        # Create item with category
        response = client.post(
            "/api/v1/inventory/",
            json={
                "name": "Laptop",
                "description": "Dell laptop",
                "quantity": 10,
                "category_id": category.id,
            },
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Laptop"
        assert data["category_id"] == category.id

    def test_create_item_negative_quantity(self, client, auth_headers):
        """Test that negative quantity is rejected."""
        response = client.post(
            "/api/v1/inventory/",
            json={
                "name": "Invalid Item",
                "description": "Has negative quantity",
                "quantity": -5,
            },
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_item_unauthenticated(self, client):
        """Test that authentication is required."""
        response = client.post(
            "/api/v1/inventory/",
            json={
                "name": "Unauthorized Item",
                "description": "No auth header",
                "quantity": 10,
            },
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_item_missing_required_fields(self, client, auth_headers):
        """Test validation for missing required fields."""
        response = client.post(
            "/api/v1/inventory/",
            json={
                "description": "Missing name",
                "quantity": 10,
            },
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
