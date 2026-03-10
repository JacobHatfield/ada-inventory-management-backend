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
        assert len(data) == 1
        assert data[0]["name"] == "Red Widget"

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
        assert len(data) == 2
        names = [item["name"] for item in data]
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
        assert len(data) == 0

    def test_search_empty_string(self, client, auth_headers, search_filter_items):
        """Test searching with empty string returns all items."""
        response = client.get(
            "/api/v1/inventory/",
            params={"search": ""},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 8


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
        assert len(data) == 2
        names = [item["name"] for item in data]
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
        assert len(data) == 2
        names = [item["name"] for item in data]
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
        assert len(data) == 4
        names = [item["name"] for item in data]
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
        names = [item["name"] for item in data]
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
        names = [item["name"] for item in data]
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
        quantities = [item["quantity"] for item in data]
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
        quantities = [item["quantity"] for item in data]
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
        assert len(data) == 8
        created_dates = [item["created_at"] for item in data]
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
        assert len(data) == 1
        assert data[0]["name"] == "Red Widget"
        assert data[0]["category_id"] == test_category.id

    def test_search_and_stock_filter(self, client, auth_headers, search_filter_items):
        """Test combining search with stock status filter."""
        response = client.get(
            "/api/v1/inventory/",
            params={"search": "widget", "stock_status": "out_of_stock"},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Red Widget"
        assert data[0]["quantity"] == 0

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
        assert len(data) == 2
        assert data[0]["name"] == "Orange Supply"
        assert data[0]["quantity"] == 200
        assert data[1]["name"] == "Green Tool"
        assert data[1]["quantity"] == 50

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
        assert len(data) == 3
        names = [item["name"] for item in data]
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

    def test_decrement_stock_success(self, client, auth_headers, test_inventory_item, db):
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
