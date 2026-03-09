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
