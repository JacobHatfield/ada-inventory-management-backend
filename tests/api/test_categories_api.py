"""Category API endpoint tests."""

from fastapi import status


class TestCreateCategory:
    """Test creating categories."""

    def test_create_category_success(self, client, auth_headers, db):
        """Test successful category creation."""
        response = client.post(
            "/api/v1/categories/",
            json={
                "name": "Electronics",
                "description": "Electronic items and gadgets",
            },
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Electronics"
        assert data["description"] == "Electronic items and gadgets"
        assert "id" in data
        assert "user_id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_category_unauthenticated(self, client):
        """Test that authentication is required."""
        response = client.post(
            "/api/v1/categories/",
            json={
                "name": "Unauthorized Category",
                "description": "No auth header",
            },
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_category_missing_required_field(self, client, auth_headers):
        """Test validation for missing required fields."""
        response = client.post(
            "/api/v1/categories/",
            json={
                "description": "Missing name field",
            },
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_category_with_empty_name(self, client, auth_headers):
        """Test that empty name is rejected (min_length validation)."""
        response = client.post(
            "/api/v1/categories/",
            json={
                "name": "",
                "description": "Empty name should fail",
            },
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestGetCategories:
    """Test listing categories."""

    def test_get_categories_success(self, client, auth_headers, db, test_user):
        """Test successful retrieval of category list."""
        # Create 3 categories for test_user
        from app.models.category import Category

        categories = [
            Category(
                name=f"Category {chr(65 + i)}",  # A, B, C
                description=f"Description {i}",
                user_id=test_user.id,
            )
            for i in range(3)
        ]
        for cat in categories:
            db.add(cat)
        db.commit()

        response = client.get("/api/v1/categories/", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 3
        assert all(cat["user_id"] == test_user.id for cat in data)
        # Verify ordered by name (alphabetically)
        assert data[0]["name"] == "Category A"
        assert data[1]["name"] == "Category B"
        assert data[2]["name"] == "Category C"

    def test_get_categories_empty_list(self, client, auth_headers):
        """Test retrieving empty category list."""
        response = client.get("/api/v1/categories/", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data == []

    def test_get_categories_only_own_categories(
        self, client, auth_headers, db, test_user, other_user
    ):
        """Test user can only see their own categories."""
        from app.models.category import Category

        # Create 2 categories for test_user
        for i in range(2):
            cat = Category(
                name=f"Test User Category {i}",
                description=f"Test user's category {i}",
                user_id=test_user.id,
            )
            db.add(cat)

        # Create 2 categories for other_user
        for i in range(2):
            cat = Category(
                name=f"Other User Category {i}",
                description=f"Other user's category {i}",
                user_id=other_user.id,
            )
            db.add(cat)
        db.commit()

        # Request with test_user's auth
        response = client.get("/api/v1/categories/", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        # Verify all categories belong to test_user
        assert all(cat["user_id"] == test_user.id for cat in data)
        # Verify none belong to other_user
        assert all(cat["user_id"] != other_user.id for cat in data)


class TestGetCategoryById:
    """Test getting a single category by ID."""

    def test_get_category_by_id_success(self, client, auth_headers, test_category, test_user):
        """Test successful retrieval of a category by ID."""
        response = client.get(
            f"/api/v1/categories/{test_category.id}",
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == test_category.id
        assert data["name"] == test_category.name
        assert data["description"] == test_category.description
        assert data["user_id"] == test_user.id
        assert "created_at" in data
        assert "updated_at" in data

    def test_get_category_not_found(self, client, auth_headers):
        """Test getting a non-existent category returns 404."""
        response = client.get(
            "/api/v1/categories/99999",
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["detail"] == "Category not found"

    def test_get_category_not_owned(
        self, client, auth_headers, other_user_category
    ):
        """Test user cannot access another user's category."""
        response = client.get(
            f"/api/v1/categories/{other_user_category.id}",
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["detail"] == "Category not found"


class TestUpdateCategory:
    """Test updating categories."""

    def test_update_category_success(self, client, auth_headers, test_category):
        """Test successful category update."""
        response = client.put(
            f"/api/v1/categories/{test_category.id}",
            json={
                "name": "Updated Electronics",
                "description": "Updated description for electronics",
            },
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == test_category.id
        assert data["name"] == "Updated Electronics"
        assert data["description"] == "Updated description for electronics"
        assert "updated_at" in data

    def test_update_category_not_found(self, client, auth_headers):
        """Test updating a non-existent category returns 404."""
        response = client.put(
            "/api/v1/categories/99999",
            json={
                "name": "Won't Work",
                "description": "This category doesn't exist",
            },
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["detail"] == "Category not found"

    def test_update_category_not_owned(
        self, client, auth_headers, other_user_category
    ):
        """Test user cannot update another user's category."""
        response = client.put(
            f"/api/v1/categories/{other_user_category.id}",
            json={
                "name": "Hacked Category",
                "description": "Trying to hack another user's category",
            },
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["detail"] == "Category not found"


class TestDeleteCategory:
    """Test deleting categories."""

    def test_delete_category_success(self, client, auth_headers, test_category):
        """Test successful category deletion."""
        category_id = test_category.id

        # Delete the category
        response = client.delete(
            f"/api/v1/categories/{category_id}",
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify category is deleted (GET should return 404)
        verify_response = client.get(
            f"/api/v1/categories/{category_id}",
            headers=auth_headers,
        )
        assert verify_response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_category_not_found(self, client, auth_headers):
        """Test deleting a non-existent category returns 404."""
        response = client.delete(
            "/api/v1/categories/99999",
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["detail"] == "Category not found"

    def test_delete_category_not_owned(
        self, client, auth_headers, other_user_category
    ):
        """Test user cannot delete another user's category."""
        response = client.delete(
            f"/api/v1/categories/{other_user_category.id}",
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["detail"] == "Category not found"

    def test_delete_category_with_items(
        self, client, auth_headers, db, test_user
    ):
        """Test that category with items cannot be deleted."""
        from app.models.category import Category
        from app.models.inventory import InventoryItem

        # Create a category
        category = Category(
            name="Category with Items",
            description="This category has inventory items",
            user_id=test_user.id,
        )
        db.add(category)
        db.commit()
        db.refresh(category)

        # Create an inventory item in this category
        item = InventoryItem(
            name="Test Item",
            description="Item in category",
            quantity=10,
            category_id=category.id,
            user_id=test_user.id,
        )
        db.add(item)
        db.commit()

        # Try to delete the category (should fail)
        response = client.delete(
            f"/api/v1/categories/{category.id}",
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "Cannot delete category with existing inventory items" in data["detail"]
