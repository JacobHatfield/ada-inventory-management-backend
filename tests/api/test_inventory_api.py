"""Inventory API endpoint tests."""

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


class TestGetInventoryItems:
    """Test listing inventory items."""

    def test_get_items_success(self, client, auth_headers, db, test_user):
        """Test successful retrieval of inventory list."""
        # Create 3 items for test_user
        from app.models.inventory import InventoryItem

        items = [
            InventoryItem(
                name=f"Item {i}",
                description=f"Description {i}",
                quantity=i * 10,
                user_id=test_user.id,
            )
            for i in range(1, 4)
        ]
        for item in items:
            db.add(item)
        db.commit()

        response = client.get("/api/v1/inventory/", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 3
        assert all(item["user_id"] == test_user.id for item in data)

    def test_get_items_empty_list(self, client, auth_headers):
        """Test retrieving empty inventory list."""
        response = client.get("/api/v1/inventory/", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data == []

    def test_get_items_only_own_items(
        self, client, auth_headers, db, test_user, other_user
    ):
        """Test user can only see their own items."""
        from app.models.inventory import InventoryItem

        # Create 2 items for test_user
        for i in range(2):
            item = InventoryItem(
                name=f"Test User Item {i}",
                quantity=10,
                user_id=test_user.id,
            )
            db.add(item)

        # Create 2 items for other_user
        for i in range(2):
            item = InventoryItem(
                name=f"Other User Item {i}",
                quantity=20,
                user_id=other_user.id,
            )
            db.add(item)
        db.commit()

        response = client.get("/api/v1/inventory/", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        assert all(item["user_id"] == test_user.id for item in data)
        assert all("Test User Item" in item["name"] for item in data)

    def test_filter_items_by_category(
        self, client, auth_headers, db, test_user
    ):
        """Test filtering inventory items by category."""
        from app.models.category import Category
        from app.models.inventory import InventoryItem

        # Create two categories
        category1 = Category(
            name="Electronics", description="Electronic items", user_id=test_user.id
        )
        category2 = Category(
            name="Books", description="Book items", user_id=test_user.id
        )
        db.add(category1)
        db.add(category2)
        db.commit()
        db.refresh(category1)
        db.refresh(category2)

        # Create items in different categories
        for i in range(3):
            item = InventoryItem(
                name=f"Electronics Item {i}",
                quantity=10,
                category_id=category1.id,
                user_id=test_user.id,
            )
            db.add(item)

        for i in range(2):
            item = InventoryItem(
                name=f"Book Item {i}",
                quantity=5,
                category_id=category2.id,
                user_id=test_user.id,
            )
            db.add(item)

        # Create item without category
        item = InventoryItem(
            name="Uncategorized Item",
            quantity=15,
            user_id=test_user.id,
        )
        db.add(item)
        db.commit()

        # Filter by category1 (Electronics)
        response = client.get(
            f"/api/v1/inventory/?category_id={category1.id}",
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 3
        assert all(item["category_id"] == category1.id for item in data)
        assert all("Electronics Item" in item["name"] for item in data)

        # Filter by category2 (Books)
        response = client.get(
            f"/api/v1/inventory/?category_id={category2.id}",
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        assert all(item["category_id"] == category2.id for item in data)
        assert all("Book Item" in item["name"] for item in data)

    def test_filter_items_by_nonexistent_category(
        self, client, auth_headers, db, test_user
    ):
        """Test filtering by non-existent category returns empty list."""
        from app.models.inventory import InventoryItem

        # Create some items
        for i in range(2):
            item = InventoryItem(
                name=f"Test Item {i}",
                quantity=10,
                user_id=test_user.id,
            )
            db.add(item)
        db.commit()

        # Filter by non-existent category ID
        response = client.get(
            "/api/v1/inventory/?category_id=99999",
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data == []

    def test_get_items_unauthenticated(self, client):
        """Test that authentication is required."""
        response = client.get("/api/v1/inventory/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestGetInventoryItemById:
    """Test getting single inventory item by ID."""

    def test_get_item_success(self, client, auth_headers, test_inventory_item):
        """Test successful retrieval of single item."""
        response = client.get(
            f"/api/v1/inventory/{test_inventory_item.id}", headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == test_inventory_item.id
        assert data["name"] == test_inventory_item.name
        assert data["quantity"] == test_inventory_item.quantity

    def test_get_item_not_found(self, client, auth_headers):
        """Test getting non-existent item returns 404."""
        response = client.get("/api/v1/inventory/99999", headers=auth_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    def test_get_item_wrong_user(self, client, auth_headers, other_user_inventory_item):
        """Test user cannot access another user's item."""
        response = client.get(
            f"/api/v1/inventory/{other_user_inventory_item.id}", headers=auth_headers
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_item_unauthenticated(self, client, test_inventory_item):
        """Test that authentication is required."""
        response = client.get(f"/api/v1/inventory/{test_inventory_item.id}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestUpdateInventoryItem:
    """Test updating inventory items."""

    def test_update_item_success(self, client, auth_headers, test_inventory_item, db):
        """Test successful full update of inventory item."""
        update_data = {
            "name": "Updated Widget",
            "description": "Updated description",
            "quantity": 200,
            "low_stock_threshold": 20,
        }
        response = client.put(
            f"/api/v1/inventory/{test_inventory_item.id}",
            json=update_data,
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Widget"
        assert data["description"] == "Updated description"
        assert data["quantity"] == 200
        assert data["low_stock_threshold"] == 20

        # Verify changes persisted in database
        db.refresh(test_inventory_item)
        assert test_inventory_item.name == "Updated Widget"
        assert test_inventory_item.quantity == 200

    def test_update_item_partial(self, client, auth_headers, test_inventory_item, db):
        """Test partial update (only some fields)."""
        original_name = test_inventory_item.name
        original_description = test_inventory_item.description

        response = client.put(
            f"/api/v1/inventory/{test_inventory_item.id}",
            json={"quantity": 150},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["quantity"] == 150
        # Other fields unchanged
        assert data["name"] == original_name
        assert data["description"] == original_description

    def test_update_item_negative_quantity(
        self, client, auth_headers, test_inventory_item
    ):
        """Test that negative quantity update is rejected."""
        response = client.put(
            f"/api/v1/inventory/{test_inventory_item.id}",
            json={"quantity": -10},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_update_item_not_found(self, client, auth_headers):
        """Test updating non-existent item returns 404."""
        response = client.put(
            "/api/v1/inventory/99999",
            json={"name": "Does Not Exist"},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_item_wrong_user(
        self, client, auth_headers, other_user_inventory_item
    ):
        """Test user cannot update another user's item."""
        response = client.put(
            f"/api/v1/inventory/{other_user_inventory_item.id}",
            json={"name": "Trying to Update"},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_item_unauthenticated(self, client, test_inventory_item):
        """Test that authentication is required."""
        response = client.put(
            f"/api/v1/inventory/{test_inventory_item.id}",
            json={"name": "No Auth"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestDeleteInventoryItem:
    """Test deleting inventory items."""

    def test_delete_item_success(self, client, auth_headers, test_inventory_item, db):
        """Test successful deletion of inventory item."""
        item_id = test_inventory_item.id

        response = client.delete(f"/api/v1/inventory/{item_id}", headers=auth_headers)
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify item is removed from database
        from app.models.inventory import InventoryItem

        deleted_item = (
            db.query(InventoryItem).filter(InventoryItem.id == item_id).first()
        )
        assert deleted_item is None

        # Verify subsequent GET returns 404
        get_response = client.get(f"/api/v1/inventory/{item_id}", headers=auth_headers)
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_item_not_found(self, client, auth_headers):
        """Test deleting non-existent item returns 404."""
        response = client.delete("/api/v1/inventory/99999", headers=auth_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_item_wrong_user(
        self, client, auth_headers, other_user_inventory_item
    ):
        """Test user cannot delete another user's item."""
        response = client.delete(
            f"/api/v1/inventory/{other_user_inventory_item.id}", headers=auth_headers
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_item_unauthenticated(self, client, test_inventory_item):
        """Test that authentication is required."""
        response = client.delete(f"/api/v1/inventory/{test_inventory_item.id}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
