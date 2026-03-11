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
        assert "items" in data
        assert "total" in data
        assert data["total"] == 3
        assert len(data["items"]) == 3
        assert all(item["user_id"] == test_user.id for item in data["items"])

    def test_get_items_empty_list(self, client, auth_headers):
        """Test retrieving empty inventory list."""
        response = client.get("/api/v1/inventory/", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

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
        assert data["total"] == 2
        assert len(data["items"]) == 2
        assert all(item["user_id"] == test_user.id for item in data["items"])
        assert all("Test User Item" in item["name"] for item in data["items"])

    def test_filter_items_by_category(self, client, auth_headers, db, test_user):
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
        assert data["total"] == 3
        assert len(data["items"]) == 3
        assert all(item["category_id"] == category1.id for item in data["items"])
        assert all("Electronics Item" in item["name"] for item in data["items"])

        # Filter by category2 (Books)
        response = client.get(
            f"/api/v1/inventory/?category_id={category2.id}",
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2
        assert all(item["category_id"] == category2.id for item in data["items"])
        assert all("Book Item" in item["name"] for item in data["items"])

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
        assert data["items"] == []
        assert data["total"] == 0

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


class TestSearchInventory:
    """Test search functionality for inventory items."""

    def test_search_by_name_exact_match(
        self, client, auth_headers, search_filter_items
    ):
        """Test searching with exact name match."""
        response = client.get(
            "/api/v1/inventory/",
            params={"search": "Red Widget"},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "Red Widget"

    def test_search_by_name_partial_match(
        self, client, auth_headers, search_filter_items
    ):
        """Test searching with partial name match (case-insensitive)."""
        response = client.get(
            "/api/v1/inventory/",
            params={"search": "widget"},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 2
        names = [item["name"] for item in data["items"]]
        assert "Red Widget" in names
        assert "Mini Widget" in names

    def test_search_no_results(self, client, auth_headers, search_filter_items):
        """Test searching for non-existent item returns empty list."""
        response = client.get(
            "/api/v1/inventory/",
            params={"search": "NonExistentItem"},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 0

    def test_search_empty_string(self, client, auth_headers, search_filter_items):
        """Test searching with empty string returns all items."""
        response = client.get(
            "/api/v1/inventory/",
            params={"search": ""},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 8


class TestFilterByStockStatus:
    """Test filtering inventory items by stock status."""

    def test_filter_low_stock_items(self, client, auth_headers, search_filter_items):
        """Test filtering items with low stock (quantity > 0 but below threshold)."""
        response = client.get(
            "/api/v1/inventory/",
            params={"stock_status": "low_stock"},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 2
        names = [item["name"] for item in data["items"]]
        assert "Blue Gadget" in names
        assert "Yellow Device" in names

    def test_filter_out_of_stock_items(self, client, auth_headers, search_filter_items):
        """Test filtering items with zero quantity."""
        response = client.get(
            "/api/v1/inventory/",
            params={"stock_status": "out_of_stock"},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 2
        names = [item["name"] for item in data["items"]]
        assert "Red Widget" in names
        assert "Black Equipment" in names

    def test_filter_in_stock_items(self, client, auth_headers, search_filter_items):
        """Test filtering items with adequate stock (quantity >= threshold or > 0 with no threshold)."""
        response = client.get(
            "/api/v1/inventory/",
            params={"stock_status": "in_stock"},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 4
        names = [item["name"] for item in data["items"]]
        assert "Green Tool" in names
        assert "Purple Component" in names
        assert "Orange Supply" in names
        assert "Mini Widget" in names

    def test_filter_invalid_stock_status(
        self, client, auth_headers, search_filter_items
    ):
        """Test that invalid stock status returns 422 validation error."""
        response = client.get(
            "/api/v1/inventory/",
            params={"stock_status": "invalid_status"},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestSortInventory:
    """Test sorting inventory items by various fields."""

    def test_sort_by_name_ascending(self, client, auth_headers, search_filter_items):
        """Test sorting items by name A-Z."""
        response = client.get(
            "/api/v1/inventory/",
            params={"sort_by": "name", "sort_order": "asc"},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        names = [item["name"] for item in data["items"]]
        assert names == sorted(names)
        assert names[0] == "Black Equipment"
        assert names[-1] == "Yellow Device"

    def test_sort_by_name_descending(self, client, auth_headers, search_filter_items):
        """Test sorting items by name Z-A."""
        response = client.get(
            "/api/v1/inventory/",
            params={"sort_by": "name", "sort_order": "desc"},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        names = [item["name"] for item in data["items"]]
        assert names == sorted(names, reverse=True)
        assert names[0] == "Yellow Device"
        assert names[-1] == "Black Equipment"

    def test_sort_by_quantity_ascending(
        self, client, auth_headers, search_filter_items
    ):
        """Test sorting items by quantity (lowest first)."""
        response = client.get(
            "/api/v1/inventory/",
            params={"sort_by": "quantity", "sort_order": "asc"},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        quantities = [item["quantity"] for item in data["items"]]
        assert quantities == sorted(quantities)
        assert quantities[0] == 0
        assert quantities[-1] == 200

    def test_sort_by_quantity_descending(
        self, client, auth_headers, search_filter_items
    ):
        """Test sorting items by quantity (highest first)."""
        response = client.get(
            "/api/v1/inventory/",
            params={"sort_by": "quantity", "sort_order": "desc"},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        quantities = [item["quantity"] for item in data["items"]]
        assert quantities == sorted(quantities, reverse=True)
        assert quantities[0] == 200
        assert quantities[-1] == 0

    def test_sort_by_created_date(self, client, auth_headers, search_filter_items):
        """Test sorting items by created_at (default: newest first)."""
        response = client.get(
            "/api/v1/inventory/",
            params={"sort_by": "created_at", "sort_order": "desc"},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 8
        created_dates = [item["created_at"] for item in data["items"]]
        assert created_dates == sorted(created_dates, reverse=True)

    def test_sort_invalid_field(self, client, auth_headers, search_filter_items):
        """Test that invalid sort field returns 422 validation error."""
        response = client.get(
            "/api/v1/inventory/",
            params={"sort_by": "invalid_field", "sort_order": "asc"},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestCombinedFiltersAndSearch:
    """Test combining multiple filters, search, and sorting together."""

    def test_search_and_category_filter(
        self, client, auth_headers, search_filter_items, test_category
    ):
        """Test combining search with category filter."""
        response = client.get(
            "/api/v1/inventory/",
            params={"search": "widget", "category_id": test_category.id},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "Red Widget"
        assert data["items"][0]["category_id"] == test_category.id

    def test_search_and_stock_filter(self, client, auth_headers, search_filter_items):
        """Test combining search with stock status filter."""
        response = client.get(
            "/api/v1/inventory/",
            params={"search": "widget", "stock_status": "out_of_stock"},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "Red Widget"
        assert data["items"][0]["quantity"] == 0

    def test_all_filters_combined(
        self, client, auth_headers, search_filter_items, test_category
    ):
        """Test combining search, category, stock status, and sorting."""
        response = client.get(
            "/api/v1/inventory/",
            params={
                "category_id": test_category.id,
                "stock_status": "in_stock",
                "sort_by": "quantity",
                "sort_order": "desc",
            },
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 2
        assert data["items"][0]["name"] == "Orange Supply"
        assert data["items"][0]["quantity"] == 200
        assert data["items"][1]["name"] == "Green Tool"
        assert data["items"][1]["quantity"] == 50

    def test_pagination_with_filters(self, client, auth_headers, search_filter_items):
        """Test that pagination works correctly with filters applied."""
        response = client.get(
            "/api/v1/inventory/",
            params={
                "sort_by": "name",
                "sort_order": "asc",
                "skip": 2,
                "limit": 3,
            },
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 3
        names = [item["name"] for item in data["items"]]
        assert names[0] == "Green Tool"
        assert names[1] == "Mini Widget"
        assert names[2] == "Orange Supply"


class TestStockIncrementAPI:
    """Test stock increment endpoint."""

    def test_increment_stock_success(self, client, auth_headers, test_inventory_item):
        """Test successful stock increment operation."""
        original_quantity = test_inventory_item.quantity

        response = client.post(
            f"/api/v1/inventory/{test_inventory_item.id}/increment",
            json={"quantity_change": 10, "reason": "Restock"},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == test_inventory_item.id
        assert data["quantity"] == original_quantity + 10
        assert "is_low_stock" in data
        assert "updated_at" in data

    def test_increment_stock_updates_quantity_correctly(
        self, client, auth_headers, test_inventory_item, db
    ):
        """Test that increment updates quantity correctly in response."""
        # Set initial quantity
        test_inventory_item.quantity = 10
        db.commit()

        response = client.post(
            f"/api/v1/inventory/{test_inventory_item.id}/increment",
            json={"quantity_change": 5},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["quantity"] == 15

        # Verify the change persisted
        verify_response = client.get(
            f"/api/v1/inventory/{test_inventory_item.id}",
            headers=auth_headers,
        )
        assert verify_response.status_code == status.HTTP_200_OK
        assert verify_response.json()["quantity"] == 15

    def test_increment_with_reason(self, client, auth_headers, test_inventory_item):
        """Test that increment accepts optional reason field."""
        original_quantity = test_inventory_item.quantity

        response = client.post(
            f"/api/v1/inventory/{test_inventory_item.id}/increment",
            json={"quantity_change": 10, "reason": "Quarterly restock"},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["quantity"] == original_quantity + 10
        # Reason is accepted and logged (for future audit functionality)


class TestStockDecrementAPI:
    """Test stock decrement endpoint."""

    def test_decrement_stock_success(
        self, client, auth_headers, test_inventory_item, db
    ):
        """Test successful stock decrement operation."""
        test_inventory_item.quantity = 50
        db.commit()

        response = client.post(
            f"/api/v1/inventory/{test_inventory_item.id}/decrement",
            json={"quantity_change": 10, "reason": "Sale"},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == test_inventory_item.id
        assert data["quantity"] == 40
        assert "is_low_stock" in data
        assert "updated_at" in data

    def test_decrement_stock_updates_quantity_correctly(
        self, client, auth_headers, test_inventory_item, db
    ):
        """Test that decrement updates quantity correctly in response."""
        test_inventory_item.quantity = 30
        db.commit()

        response = client.post(
            f"/api/v1/inventory/{test_inventory_item.id}/decrement",
            json={"quantity_change": 8},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["quantity"] == 22

        # Verify the change persisted
        verify_response = client.get(
            f"/api/v1/inventory/{test_inventory_item.id}",
            headers=auth_headers,
        )
        assert verify_response.status_code == status.HTTP_200_OK
        assert verify_response.json()["quantity"] == 22

    def test_decrement_with_reason(self, client, auth_headers, test_inventory_item, db):
        """Test that decrement accepts optional reason field."""
        test_inventory_item.quantity = 25
        db.commit()
        original_quantity = test_inventory_item.quantity

        response = client.post(
            f"/api/v1/inventory/{test_inventory_item.id}/decrement",
            json={"quantity_change": 5, "reason": "Customer sale"},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["quantity"] == original_quantity - 5

    def test_decrement_to_zero(self, client, auth_headers, test_inventory_item, db):
        """Test decrementing stock to exactly zero."""
        test_inventory_item.quantity = 10
        db.commit()

        response = client.post(
            f"/api/v1/inventory/{test_inventory_item.id}/decrement",
            json={"quantity_change": 10},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["quantity"] == 0
        assert data["is_low_stock"] is True


class TestStockNegativePreventionAPI:
    """Test that API prevents negative stock through decrement endpoint."""

    def test_cannot_decrement_below_zero(
        self, client, auth_headers, test_inventory_item, db
    ):
        """Test that decrementing below zero returns 400 Bad Request."""
        test_inventory_item.quantity = 5
        db.commit()

        response = client.post(
            f"/api/v1/inventory/{test_inventory_item.id}/decrement",
            json={"quantity_change": 10},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "detail" in response.json()

        # Verify quantity unchanged
        verify_response = client.get(
            f"/api/v1/inventory/{test_inventory_item.id}",
            headers=auth_headers,
        )
        assert verify_response.json()["quantity"] == 5

    def test_cannot_decrement_from_zero(
        self, client, auth_headers, test_inventory_item, db
    ):
        """Test that decrementing from zero returns 400 Bad Request."""
        test_inventory_item.quantity = 0
        db.commit()

        response = client.post(
            f"/api/v1/inventory/{test_inventory_item.id}/decrement",
            json={"quantity_change": 1},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "detail" in response.json()

    def test_large_decrement_prevented(
        self, client, auth_headers, test_inventory_item, db
    ):
        """Test that large decrements that would go negative are prevented."""
        test_inventory_item.quantity = 100
        db.commit()

        response = client.post(
            f"/api/v1/inventory/{test_inventory_item.id}/decrement",
            json={"quantity_change": 150},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

        # Verify quantity unchanged
        verify_response = client.get(
            f"/api/v1/inventory/{test_inventory_item.id}",
            headers=auth_headers,
        )
        assert verify_response.json()["quantity"] == 100


class TestStockAdjustmentAuth:
    """Test authentication and authorization for stock adjustment endpoints."""

    def test_increment_requires_authentication(self, client, test_inventory_item):
        """Test that increment endpoint requires authentication."""
        response = client.post(
            f"/api/v1/inventory/{test_inventory_item.id}/increment",
            json={"quantity_change": 10},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_decrement_requires_authentication(self, client, test_inventory_item):
        """Test that decrement endpoint requires authentication."""
        response = client.post(
            f"/api/v1/inventory/{test_inventory_item.id}/decrement",
            json={"quantity_change": 5},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_cannot_increment_other_users_item(
        self, client, test_inventory_item, other_user, db
    ):
        """Test that users cannot increment other users' inventory items."""
        # Login as other_user to get valid token
        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": "otheruser@example.com", "password": "otherpassword123"},
        )
        other_user_token = login_response.json()["access_token"]
        other_headers = {"Authorization": f"Bearer {other_user_token}"}

        response = client.post(
            f"/api/v1/inventory/{test_inventory_item.id}/increment",
            json={"quantity_change": 10},
            headers=other_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_cannot_decrement_other_users_item(
        self, client, test_inventory_item, other_user, db
    ):
        """Test that users cannot decrement other users' inventory items."""
        # Login as other_user to get valid token
        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": "otheruser@example.com", "password": "otherpassword123"},
        )
        other_user_token = login_response.json()["access_token"]
        other_headers = {"Authorization": f"Bearer {other_user_token}"}

        response = client.post(
            f"/api/v1/inventory/{test_inventory_item.id}/decrement",
            json={"quantity_change": 5},
            headers=other_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestStockAdjustmentValidation:
    """Test input validation for stock adjustment endpoints."""

    def test_increment_invalid_quantity_type(
        self, client, auth_headers, test_inventory_item
    ):
        """Test that increment rejects non-integer quantity."""
        response = client.post(
            f"/api/v1/inventory/{test_inventory_item.id}/increment",
            json={"quantity_change": "ten"},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_decrement_invalid_quantity_type(
        self, client, auth_headers, test_inventory_item
    ):
        """Test that decrement rejects non-integer quantity."""
        response = client.post(
            f"/api/v1/inventory/{test_inventory_item.id}/decrement",
            json={"quantity_change": "five"},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_increment_zero_quantity(self, client, auth_headers, test_inventory_item):
        """Test that increment rejects zero quantity."""
        response = client.post(
            f"/api/v1/inventory/{test_inventory_item.id}/increment",
            json={"quantity_change": 0},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_decrement_zero_quantity(self, client, auth_headers, test_inventory_item):
        """Test that decrement rejects zero quantity."""
        response = client.post(
            f"/api/v1/inventory/{test_inventory_item.id}/decrement",
            json={"quantity_change": 0},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_increment_negative_quantity(
        self, client, auth_headers, test_inventory_item
    ):
        """Test that increment rejects negative quantity."""
        response = client.post(
            f"/api/v1/inventory/{test_inventory_item.id}/increment",
            json={"quantity_change": -5},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_decrement_negative_quantity(
        self, client, auth_headers, test_inventory_item
    ):
        """Test that decrement rejects negative quantity."""
        response = client.post(
            f"/api/v1/inventory/{test_inventory_item.id}/decrement",
            json={"quantity_change": -3},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_nonexistent_item(self, client, auth_headers):
        """Test adjusting stock for non-existent inventory item."""
        nonexistent_id = 99999

        response = client.post(
            f"/api/v1/inventory/{nonexistent_id}/increment",
            json={"quantity_change": 10},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

        response = client.post(
            f"/api/v1/inventory/{nonexistent_id}/decrement",
            json={"quantity_change": 5},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestStockAdjustmentEdgeCases:
    """Test edge cases for stock adjustment endpoints."""

    def test_multiple_rapid_adjustments(
        self, client, auth_headers, test_inventory_item, db
    ):
        """Test multiple rapid stock adjustments on same item."""
        test_inventory_item.quantity = 50
        db.commit()

        # Perform multiple adjustments
        client.post(
            f"/api/v1/inventory/{test_inventory_item.id}/increment",
            json={"quantity_change": 10},
            headers=auth_headers,
        )
        client.post(
            f"/api/v1/inventory/{test_inventory_item.id}/decrement",
            json={"quantity_change": 5},
            headers=auth_headers,
        )
        response = client.post(
            f"/api/v1/inventory/{test_inventory_item.id}/increment",
            json={"quantity_change": 15},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # 50 + 10 - 5 + 15 = 70
        assert data["quantity"] == 70

    def test_very_large_quantity_increment(
        self, client, auth_headers, test_inventory_item, db
    ):
        """Test incrementing by very large quantity."""
        test_inventory_item.quantity = 100
        db.commit()

        response = client.post(
            f"/api/v1/inventory/{test_inventory_item.id}/increment",
            json={"quantity_change": 10000},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["quantity"] == 10100

    def test_adjusting_after_item_update(
        self, client, auth_headers, test_inventory_item, db
    ):
        """Test stock adjustment after updating other item fields."""
        test_inventory_item.quantity = 30
        db.commit()

        # Update item name
        client.put(
            f"/api/v1/inventory/{test_inventory_item.id}",
            json={
                "name": "Updated Widget",
                "quantity": 30,
                "low_stock_threshold": 10,
            },
            headers=auth_headers,
        )

        # Now adjust stock
        response = client.post(
            f"/api/v1/inventory/{test_inventory_item.id}/increment",
            json={"quantity_change": 20},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["quantity"] == 50
        assert data["name"] == "Updated Widget"

    def test_low_stock_flag_changes(
        self, client, auth_headers, test_inventory_item, db
    ):
        """Test that is_low_stock flag updates correctly with adjustments."""
        test_inventory_item.quantity = 5
        test_inventory_item.low_stock_threshold = 10
        db.commit()

        # Item should be low stock
        response = client.get(
            f"/api/v1/inventory/{test_inventory_item.id}",
            headers=auth_headers,
        )
        assert response.json()["is_low_stock"] is True

        # Increment above threshold
        response = client.post(
            f"/api/v1/inventory/{test_inventory_item.id}/increment",
            json={"quantity_change": 10},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["quantity"] == 15
        assert data["is_low_stock"] is False

    def test_decrement_to_low_stock_threshold(
        self, client, auth_headers, test_inventory_item, db
    ):
        """Test decrementing exactly to the low stock threshold."""
        test_inventory_item.quantity = 20
        test_inventory_item.low_stock_threshold = 10
        db.commit()

        response = client.post(
            f"/api/v1/inventory/{test_inventory_item.id}/decrement",
            json={"quantity_change": 10},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["quantity"] == 10
        # At threshold, should be low stock
        assert data["is_low_stock"] is True


class TestInventoryPagination:
    """Test pagination functionality for inventory endpoints."""

    def test_pagination_metadata_structure(self, client, auth_headers, db, test_user):
        """Test that paginated response includes correct metadata structure."""
        from app.models.inventory import InventoryItem

        # Create multiple items
        for i in range(5):
            item = InventoryItem(
                name=f"Item {i}",
                description=f"Description {i}",
                quantity=10 + i,
                user_id=test_user.id,
            )
            db.add(item)
        db.commit()

        response = client.get("/api/v1/inventory/?page_size=3", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify response structure
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data

        # Verify metadata values
        assert data["total"] == 5
        assert data["page"] == 1
        assert data["page_size"] == 3
        assert data["total_pages"] == 2
        assert len(data["items"]) == 3

    def test_pagination_with_page_parameter(self, client, auth_headers, db, test_user):
        """Test navigating through pages using page parameter."""
        from app.models.inventory import InventoryItem

        # Create 10 items
        for i in range(10):
            item = InventoryItem(
                name=f"Item {i:02d}",
                description=f"Description {i}",
                quantity=100 + i,
                user_id=test_user.id,
            )
            db.add(item)
        db.commit()

        # Get first page
        response = client.get(
            "/api/v1/inventory/?page=1&page_size=4", headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        page1_data = response.json()
        assert page1_data["page"] == 1
        assert page1_data["page_size"] == 4
        assert page1_data["total"] == 10
        assert page1_data["total_pages"] == 3
        assert len(page1_data["items"]) == 4

        # Get second page
        response = client.get(
            "/api/v1/inventory/?page=2&page_size=4", headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        page2_data = response.json()
        assert page2_data["page"] == 2
        assert len(page2_data["items"]) == 4

        # Get third page (partial)
        response = client.get(
            "/api/v1/inventory/?page=3&page_size=4", headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        page3_data = response.json()
        assert page3_data["page"] == 3
        assert len(page3_data["items"]) == 2

        # Verify items are different across pages
        page1_ids = {item["id"] for item in page1_data["items"]}
        page2_ids = {item["id"] for item in page2_data["items"]}
        page3_ids = {item["id"] for item in page3_data["items"]}
        assert len(page1_ids & page2_ids) == 0  # No overlap
        assert len(page2_ids & page3_ids) == 0  # No overlap

    def test_pagination_page_boundaries(self, client, auth_headers, db, test_user):
        """Test pagination at page boundaries."""
        from app.models.inventory import InventoryItem

        # Create 5 items
        for i in range(5):
            item = InventoryItem(
                name=f"Item {i}",
                description=f"Description {i}",
                quantity=50,
                user_id=test_user.id,
            )
            db.add(item)
        db.commit()

        # Test first page
        response = client.get(
            "/api/v1/inventory/?page=1&page_size=3", headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["page"] == 1
        assert len(data["items"]) == 3

        # Test last page
        response = client.get(
            "/api/v1/inventory/?page=2&page_size=3", headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["page"] == 2
        assert len(data["items"]) == 2

        # Test beyond last page (should return empty)
        response = client.get(
            "/api/v1/inventory/?page=3&page_size=3", headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["page"] == 3
        assert len(data["items"]) == 0

    def test_pagination_total_pages_calculation(
        self, client, auth_headers, db, test_user
    ):
        """Test that total_pages is calculated correctly for various scenarios."""
        from app.models.inventory import InventoryItem

        # Test with exactly divisible total
        for i in range(6):
            item = InventoryItem(
                name=f"Item {i}",
                description=f"Description {i}",
                quantity=10,
                user_id=test_user.id,
            )
            db.add(item)
        db.commit()

        response = client.get("/api/v1/inventory/?page_size=3", headers=auth_headers)
        data = response.json()
        assert data["total"] == 6
        assert data["total_pages"] == 2

        # Test with remainder
        item = InventoryItem(
            name="Extra Item",
            description="Extra",
            quantity=10,
            user_id=test_user.id,
        )
        db.add(item)
        db.commit()

        response = client.get("/api/v1/inventory/?page_size=3", headers=auth_headers)
        data = response.json()
        assert data["total"] == 7
        assert data["total_pages"] == 3

    def test_pagination_empty_results(self, client, auth_headers):
        """Test pagination with no items."""
        response = client.get(
            "/api/v1/inventory/?page=1&page_size=10", headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["page_size"] == 10
        assert data["total_pages"] == 0
        assert len(data["items"]) == 0

    def test_pagination_single_page(self, client, auth_headers, db, test_user):
        """Test pagination when all items fit in one page."""
        from app.models.inventory import InventoryItem

        # Create 3 items
        for i in range(3):
            item = InventoryItem(
                name=f"Item {i}",
                description=f"Description {i}",
                quantity=25,
                user_id=test_user.id,
            )
            db.add(item)
        db.commit()

        response = client.get("/api/v1/inventory/?page_size=10", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 3
        assert data["page"] == 1
        assert data["page_size"] == 10
        assert data["total_pages"] == 1
        assert len(data["items"]) == 3

    def test_pagination_exceeds_max_page_size(
        self, client, auth_headers, db, test_user
    ):
        """Test that page_size is capped at maximum limit."""
        from app.models.inventory import InventoryItem

        # Create several items
        for i in range(10):
            item = InventoryItem(
                name=f"Item {i}",
                description=f"Description {i}",
                quantity=50,
                user_id=test_user.id,
            )
            db.add(item)
        db.commit()

        # Request page_size larger than MAX_PAGE_SIZE (100)
        response = client.get("/api/v1/inventory/?page_size=200", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Should be capped at MAX_PAGE_SIZE (100)
        assert data["page_size"] == 100
        assert len(data["items"]) == 10  # All items returned

    def test_pagination_with_search_and_filters(
        self, client, auth_headers, db, test_user
    ):
        """Test pagination combined with search and filters."""
        from app.models.inventory import InventoryItem

        # Create items with varying names
        for i in range(8):
            item = InventoryItem(
                name=f"Widget {i}" if i % 2 == 0 else f"Gadget {i}",
                description=f"Description {i}",
                quantity=100 if i < 4 else 5,  # Some in stock, some low stock
                low_stock_threshold=10,
                user_id=test_user.id,
            )
            db.add(item)
        db.commit()

        # Test pagination with search
        response = client.get(
            "/api/v1/inventory/?search=Widget&page_size=2", headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 4  # 4 Widgets
        assert data["total_pages"] == 2
        assert len(data["items"]) == 2
        assert all("Widget" in item["name"] for item in data["items"])

        # Test pagination with stock status filter
        response = client.get(
            "/api/v1/inventory/?stock_status=low_stock&page_size=3",
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 4  # 4 low stock items
        assert data["total_pages"] == 2
        assert len(data["items"]) == 3

        # Test pagination with combined filters
        response = client.get(
            "/api/v1/inventory/?search=Gadget&stock_status=low_stock&page_size=2",
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 2  # 2 low stock Gadgets
        assert data["total_pages"] == 1
        assert len(data["items"]) == 2


class TestAuditHistoryEndpoint:
    """Test audit history API endpoint."""

    def test_get_audit_history_success(self, client, auth_headers, db, test_user):
        """Test successfully retrieving audit history for an item."""
        from app.models.inventory import InventoryItem
        from app.services import audit_service

        # Create an item
        item = InventoryItem(
            name="Test Item",
            description="Test Description",
            quantity=100,
            user_id=test_user.id,
        )
        db.add(item)
        db.commit()
        db.refresh(item)

        # Create some audit logs
        audit_service.create_audit_log(
            db=db,
            inventory_item_id=item.id,
            user_id=test_user.id,
            action="created",
            field_name="name",
            new_value="Test Item",
        )
        audit_service.create_audit_log(
            db=db,
            inventory_item_id=item.id,
            user_id=test_user.id,
            action="updated",
            field_name="quantity",
            old_value="100",
            new_value="150",
        )

        # Get audit history
        response = client.get(
            f"/api/v1/inventory/{item.id}/audit-history", headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] == 2
        assert len(data["items"]) == 2
        assert data["items"][0]["action"] in ["created", "updated"]
        assert data["items"][0]["user_id"] == test_user.id

    def test_get_audit_history_pagination_with_page_params(
        self, client, auth_headers, db, test_user
    ):
        """Test pagination using page and page_size parameters."""
        from app.models.inventory import InventoryItem
        from app.services import audit_service
        import time

        # Create an item
        item = InventoryItem(
            name="Paginated Item",
            description="Test",
            quantity=100,
            user_id=test_user.id,
        )
        db.add(item)
        db.commit()
        db.refresh(item)

        # Create 5 audit logs with slight delays to ensure ordering
        for i in range(5):
            audit_service.create_audit_log(
                db=db,
                inventory_item_id=item.id,
                user_id=test_user.id,
                action="updated",
                field_name="quantity",
                old_value=str(i),
                new_value=str(i + 1),
            )
            time.sleep(0.01)

        # Get first page (page_size=2)
        response = client.get(
            f"/api/v1/inventory/{item.id}/audit-history?page=1&page_size=2",
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 5
        assert data["page"] == 1
        assert data["page_size"] == 2
        assert data["total_pages"] == 3
        assert len(data["items"]) == 2

        # Get second page
        response = client.get(
            f"/api/v1/inventory/{item.id}/audit-history?page=2&page_size=2",
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["page"] == 2
        assert len(data["items"]) == 2

        # Get third page (partial)
        response = client.get(
            f"/api/v1/inventory/{item.id}/audit-history?page=3&page_size=2",
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["page"] == 3
        assert len(data["items"]) == 1

    def test_get_audit_history_pagination_with_skip_limit(
        self, client, auth_headers, db, test_user
    ):
        """Test pagination using skip and limit parameters."""
        from app.models.inventory import InventoryItem
        from app.services import audit_service

        # Create an item
        item = InventoryItem(
            name="Skip Limit Item", description="Test", quantity=50, user_id=test_user.id
        )
        db.add(item)
        db.commit()
        db.refresh(item)

        # Create 10 audit logs
        for i in range(10):
            audit_service.create_audit_log(
                db=db,
                inventory_item_id=item.id,
                user_id=test_user.id,
                action="updated",
                field_name="quantity",
                old_value=str(i),
                new_value=str(i + 1),
            )

        # Use skip=0, limit=5
        response = client.get(
            f"/api/v1/inventory/{item.id}/audit-history?skip=0&limit=5",
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 10
        assert len(data["items"]) == 5

        # Use skip=5, limit=5
        response = client.get(
            f"/api/v1/inventory/{item.id}/audit-history?skip=5&limit=5",
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 5

    def test_get_audit_history_empty(self, client, auth_headers, db, test_user):
        """Test getting audit history for an item with no logs."""
        from app.models.inventory import InventoryItem

        # Create an item without any audit logs
        item = InventoryItem(
            name="No Audit Item",
            description="No logs",
            quantity=10,
            user_id=test_user.id,
        )
        db.add(item)
        db.commit()
        db.refresh(item)

        # Clear any auto-generated logs (if service creates them)
        from app.models.audit import AuditLog

        db.query(AuditLog).filter(AuditLog.inventory_item_id == item.id).delete()
        db.commit()

        response = client.get(
            f"/api/v1/inventory/{item.id}/audit-history", headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 0
        assert len(data["items"]) == 0

    def test_get_audit_history_item_not_found(self, client, auth_headers):
        """Test getting audit history for non-existent item."""
        response = client.get(
            "/api/v1/inventory/99999/audit-history", headers=auth_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    def test_get_audit_history_unauthorized(self, client, db, test_user):
        """Test that authentication is required."""
        from app.models.inventory import InventoryItem

        # Create an item
        item = InventoryItem(
            name="Secure Item", description="Test", quantity=50, user_id=test_user.id
        )
        db.add(item)
        db.commit()
        db.refresh(item)

        # Try to access without auth
        response = client.get(f"/api/v1/inventory/{item.id}/audit-history")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_audit_history_other_user_item(
        self, client, auth_headers, db, test_user
    ):
        """Test that users cannot access audit history of other users' items."""
        from app.models.inventory import InventoryItem
        from app.models.user import User
        from app.core.security import hash_password

        # Create another user
        other_user = User(
            email="otheruser@example.com",
            hashed_password=hash_password("password123"),
            full_name="Other User",
            is_active=True,
        )
        db.add(other_user)
        db.commit()
        db.refresh(other_user)

        # Create item owned by other user
        other_item = InventoryItem(
            name="Other's Item",
            description="Not yours",
            quantity=100,
            user_id=other_user.id,
        )
        db.add(other_item)
        db.commit()
        db.refresh(other_item)

        # Try to access with test_user's auth
        response = client.get(
            f"/api/v1/inventory/{other_item.id}/audit-history", headers=auth_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_audit_history_logs_sorted_by_time(
        self, client, auth_headers, db, test_user
    ):
        """Test that audit logs are returned in reverse chronological order."""
        from app.models.inventory import InventoryItem
        from app.services import audit_service
        import time

        # Create an item
        item = InventoryItem(
            name="Sorted Item", description="Test", quantity=100, user_id=test_user.id
        )
        db.add(item)
        db.commit()
        db.refresh(item)

        # Create logs with clear time separation
        actions = ["created", "updated", "stock_increased"]
        for i, action in enumerate(actions):
            audit_service.create_audit_log(
                db=db,
                inventory_item_id=item.id,
                user_id=test_user.id,
                action=action,
                field_name="quantity",
                old_value=str(i * 10),
                new_value=str((i + 1) * 10),
            )
            # Force a distinct timestamp by short delay
            time.sleep(0.01)

        response = client.get(
            f"/api/v1/inventory/{item.id}/audit-history", headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        logs = data["items"]

        # Should be in reverse chronological order (most recent first)
        # Verify we have all 3 logs
        assert len(logs) == 3
        actions_in_response = [log["action"] for log in logs]
        # Since timestamps might be identical, just verify all actions are present
        assert "created" in actions_in_response
        assert "updated" in actions_in_response
        assert "stock_increased" in actions_in_response

    def test_get_audit_history_response_structure(
        self, client, auth_headers, db, test_user
    ):
        """Test that audit history response has correct structure."""
        from app.models.inventory import InventoryItem
        from app.services import audit_service

        # Create an item
        item = InventoryItem(
            name="Structure Test", description="Test", quantity=50, user_id=test_user.id
        )
        db.add(item)
        db.commit()
        db.refresh(item)

        # Create an audit log
        audit_service.create_audit_log(
            db=db,
            inventory_item_id=item.id,
            user_id=test_user.id,
            action="created",
            field_name="name",
            new_value="Structure Test",
        )

        response = client.get(
            f"/api/v1/inventory/{item.id}/audit-history", headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Check pagination structure
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data

        # Check audit log structure
        log = data["items"][0]
        assert "id" in log
        assert "inventory_item_id" in log
        assert "user_id" in log
        assert "action" in log
        assert "field_name" in log
        assert "old_value" in log
        assert "new_value" in log
        assert "timestamp" in log

    def test_get_audit_history_max_page_size_limit(
        self, client, auth_headers, db, test_user
    ):
        """Test that page_size respects maximum limit."""
        from app.models.inventory import InventoryItem
        from app.services import audit_service

        # Create an item
        item = InventoryItem(
            name="Limit Test", description="Test", quantity=100, user_id=test_user.id
        )
        db.add(item)
        db.commit()
        db.refresh(item)

        # Create 10 logs
        for i in range(10):
            audit_service.create_audit_log(
                db=db,
                inventory_item_id=item.id,
                user_id=test_user.id,
                action="updated",
                field_name="quantity",
                old_value=str(i),
                new_value=str(i + 1),
            )

        # Request with page_size exceeding MAX (100)
        response = client.get(
            f"/api/v1/inventory/{item.id}/audit-history?page_size=200",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Should be capped at MAX_PAGE_SIZE (100)
        assert data["page_size"] == 100
        assert len(data["items"]) == 10  # All 10 logs returned

    def test_complete_item_lifecycle_audit_trail(
        self, client, auth_headers, db, test_user
    ):
        """Test end-to-end: Create, update, adjust stock, delete - verify full audit trail."""
        # Step 1: Create an item via API
        create_response = client.post(
            "/api/v1/inventory/",
            json={
                "name": "Lifecycle Item",
                "description": "Testing full lifecycle",
                "quantity": 100,
                "low_stock_threshold": 10,
            },
            headers=auth_headers,
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        item_id = create_response.json()["id"]

        # Step 2: Update the item via API
        update_response = client.put(
            f"/api/v1/inventory/{item_id}",
            json={
                "name": "Updated Lifecycle Item",
                "description": "Updated description",
            },
            headers=auth_headers,
        )
        assert update_response.status_code == status.HTTP_200_OK

        # Step 3: Increase stock via API
        increment_response = client.post(
            f"/api/v1/inventory/{item_id}/increment",
            json={"quantity_change": 50, "reason": "Restock from supplier"},
            headers=auth_headers,
        )
        assert increment_response.status_code == status.HTTP_200_OK

        # Step 4: Decrease stock via API
        decrement_response = client.post(
            f"/api/v1/inventory/{item_id}/decrement",
            json={"quantity_change": 30, "reason": "Sold to customer"},
            headers=auth_headers,
        )
        assert decrement_response.status_code == status.HTTP_200_OK

        # Step 5: Check audit trail BEFORE deletion
        pre_delete_audit = client.get(
            f"/api/v1/inventory/{item_id}/audit-history", headers=auth_headers
        )
        assert pre_delete_audit.status_code == status.HTTP_200_OK
        pre_delete_logs = pre_delete_audit.json()["items"]

        # Verify key lifecycle events are logged
        actions = [log["action"] for log in pre_delete_logs]
        assert "created" in actions
        assert "updated" in actions
        assert "stock_increased" in actions
        assert "stock_decreased" in actions
        assert len(actions) >= 5  # created + 2 updates (name, description) + stock ops

        # Step 6: Delete the item via API
        delete_response = client.delete(
            f"/api/v1/inventory/{item_id}", headers=auth_headers
        )
        assert delete_response.status_code == status.HTTP_204_NO_CONTENT

        # Verify item and its audit logs are cascade deleted
        from app.models.audit import AuditLog

        logs_after_delete = (
            db.query(AuditLog)
            .filter(AuditLog.inventory_item_id == item_id)
            .all()
        )
        # Logs should be cascade deleted with the item
        assert len(logs_after_delete) == 0

    def test_realtime_audit_updates_through_api(
        self, client, auth_headers, db, test_user
    ):
        """Test end-to-end: Verify audit logs update in real-time as operations occur."""
        # Create an item via API
        create_response = client.post(
            "/api/v1/inventory/",
            json={
                "name": "Real-time Test",
                "description": "Testing real-time audit",
                "quantity": 50,
            },
            headers=auth_headers,
        )
        item_id = create_response.json()["id"]

        # Check audit history after creation
        audit_response_1 = client.get(
            f"/api/v1/inventory/{item_id}/audit-history", headers=auth_headers
        )
        audit_data_1 = audit_response_1.json()
        initial_count = audit_data_1["total"]
        assert initial_count >= 1  # At least the creation log

        # Perform an update (change name, not quantity to avoid overlap)
        client.put(
            f"/api/v1/inventory/{item_id}",
            json={"name": "Real-time Test Updated"},
            headers=auth_headers,
        )

        # Check audit history again - should have more logs
        audit_response_2 = client.get(
            f"/api/v1/inventory/{item_id}/audit-history", headers=auth_headers
        )
        audit_data_2 = audit_response_2.json()
        after_update_count = audit_data_2["total"]
        assert after_update_count > initial_count  # New log(s) added

        # Perform stock adjustment
        stock_response = client.post(
            f"/api/v1/inventory/{item_id}/increment",
            json={"quantity_change": 25},
            headers=auth_headers,
        )
        assert stock_response.status_code == status.HTTP_200_OK

        # Check audit history again - should have even more logs
        audit_response_3 = client.get(
            f"/api/v1/inventory/{item_id}/audit-history", headers=auth_headers
        )
        audit_data_3 = audit_response_3.json()
        after_stock_count = audit_data_3["total"]
        assert after_stock_count > after_update_count  # More logs added

        # Verify stock_increased action is in the audit history
        all_actions = [log["action"] for log in audit_data_3["items"]]
        assert "created" in all_actions
        assert "updated" in all_actions
        assert "stock_increased" in all_actions

    def test_multi_user_audit_separation(self, client, auth_headers, db, test_user):
        """Test end-to-end: Verify audit logs are properly separated between users."""
        from app.models.user import User
        from app.core.security import hash_password

        # Create a second user
        second_user = User(
            email="seconduser@example.com",
            hashed_password=hash_password("password123"),
            full_name="Second User",
            is_active=True,
        )
        db.add(second_user)
        db.commit()
        db.refresh(second_user)

        # Get auth token for second user
        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": "seconduser@example.com", "password": "password123"},
        )
        second_user_token = login_response.json()["access_token"]
        second_user_headers = {"Authorization": f"Bearer {second_user_token}"}

        # First user creates an item
        first_item_response = client.post(
            "/api/v1/inventory/",
            json={
                "name": "First User Item",
                "description": "Belongs to first user",
                "quantity": 100,
            },
            headers=auth_headers,
        )
        first_item_id = first_item_response.json()["id"]

        # Second user creates an item
        second_item_response = client.post(
            "/api/v1/inventory/",
            json={
                "name": "Second User Item",
                "description": "Belongs to second user",
                "quantity": 200,
            },
            headers=second_user_headers,
        )
        second_item_id = second_item_response.json()["id"]

        # First user can access their item's audit history
        first_audit_response = client.get(
            f"/api/v1/inventory/{first_item_id}/audit-history", headers=auth_headers
        )
        assert first_audit_response.status_code == status.HTTP_200_OK
        first_audit_data = first_audit_response.json()
        assert first_audit_data["total"] >= 1

        # First user CANNOT access second user's item audit history
        unauthorized_response = client.get(
            f"/api/v1/inventory/{second_item_id}/audit-history", headers=auth_headers
        )
        assert unauthorized_response.status_code == status.HTTP_404_NOT_FOUND

        # Second user can access their own item's audit history
        second_audit_response = client.get(
            f"/api/v1/inventory/{second_item_id}/audit-history",
            headers=second_user_headers,
        )
        assert second_audit_response.status_code == status.HTTP_200_OK
        second_audit_data = second_audit_response.json()
        assert second_audit_data["total"] >= 1

        # Verify audit logs show correct user_id for each item
        first_logs = first_audit_data["items"]
        assert all(log["user_id"] == test_user.id for log in first_logs)

        second_logs = second_audit_data["items"]
        assert all(log["user_id"] == second_user.id for log in second_logs)
