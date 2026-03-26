"""API tests for user profile management endpoints."""

from fastapi import status


class TestGetProfileAPI:
    """Tests for GET /api/v1/users/me/profile endpoint."""

    def test_get_profile_success(self, client, auth_headers):
        """Return current user's profile with all fields."""
        response = client.get("/api/v1/users/me/profile", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == "testuser@example.com"
        assert data["full_name"] == "Test User"
        assert data["is_active"] is True
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_get_profile_unauthenticated(self, client):
        """Return 401 when not authenticated."""
        response = client.get("/api/v1/users/me/profile")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_profile_returns_full_schema(self, client, auth_headers, db, test_user):
        """Include profile_image_url in response."""
        test_user.profile_image_url = "https://example.com/avatar.jpg"
        db.commit()

        response = client.get("/api/v1/users/me/profile", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["profile_image_url"] == "https://example.com/avatar.jpg"


class TestUpdateProfileAPI:
    """Tests for PUT /api/v1/users/me/profile endpoint."""

    def test_update_profile_email_success(self, client, auth_headers, db, test_user):
        """Update only email field."""
        new_email = "newemail@example.com"
        response = client.put(
            "/api/v1/users/me/profile",
            json={"email": new_email},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == new_email
        assert data["full_name"] == "Test User"

        # Verify persisted in DB
        db.refresh(test_user)
        assert test_user.email == new_email

    def test_update_profile_full_name_success(
        self, client, auth_headers, db, test_user
    ):
        """Update only full_name field."""
        new_name = "Updated Name"
        response = client.put(
            "/api/v1/users/me/profile",
            json={"full_name": new_name},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["full_name"] == new_name
        assert data["email"] == "testuser@example.com"

    def test_update_profile_combined_fields(self, client, auth_headers):
        """Update multiple fields at once."""
        response = client.put(
            "/api/v1/users/me/profile",
            json={
                "email": "combined@example.com",
                "full_name": "Combined Update",
                "profile_image_url": "https://example.com/new.jpg",
            },
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == "combined@example.com"
        assert data["full_name"] == "Combined Update"
        assert data["profile_image_url"] == "https://example.com/new.jpg"

    def test_update_profile_email_already_exists(
        self, client, auth_headers, other_user
    ):
        """Return 400 when email is already taken."""
        response = client.put(
            "/api/v1/users/me/profile",
            json={"email": other_user.email},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already registered" in response.json()["detail"]

    def test_update_profile_invalid_email_format(self, client, auth_headers):
        """Return 422 for invalid email format."""
        response = client.put(
            "/api/v1/users/me/profile",
            json={"email": "not-an-email"},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_update_profile_partial_update(self, client, auth_headers, db, test_user):
        """Only update specified fields."""
        original_name = test_user.full_name
        response = client.put(
            "/api/v1/users/me/profile",
            json={"email": "partial@example.com"},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == "partial@example.com"
        assert data["full_name"] == original_name

    def test_update_profile_unauthenticated(self, client):
        """Return 401 when not authenticated."""
        response = client.put(
            "/api/v1/users/me/profile",
            json={"full_name": "Unauthorized"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_update_profile_only_own_profile(
        self, client, auth_headers, other_user, db
    ):
        """User can only update their own profile."""
        original_email = other_user.email
        response = client.put(
            "/api/v1/users/me/profile",
            json={"email": "trying-to-change-other@example.com"},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        # Verify other_user was not modified
        db.refresh(other_user)
        assert other_user.email == original_email


class TestProfileIntegration:
    """Integration tests for profile management."""

    def test_profile_changes_reflected_get_profile(
        self, client, auth_headers, db, test_user
    ):
        """Profile changes are reflected when refetching."""
        new_name = "Changed Name"
        client.put(
            "/api/v1/users/me/profile",
            json={"full_name": new_name},
            headers=auth_headers,
        )

        response = client.get("/api/v1/users/me/profile", headers=auth_headers)
        data = response.json()
        assert data["full_name"] == new_name

    def test_profile_image_url_persistence(self, client, auth_headers, db, test_user):
        """Profile image URL persists across requests."""
        image_url = "https://cdn.example.com/avatars/user123.png"
        client.put(
            "/api/v1/users/me/profile",
            json={"profile_image_url": image_url},
            headers=auth_headers,
        )

        response = client.get("/api/v1/users/me/profile", headers=auth_headers)
        data = response.json()
        assert data["profile_image_url"] == image_url

    def test_multiple_users_cannot_share_email(
        self, client, auth_headers, db, other_user
    ):
        """Verify email uniqueness across users."""
        # Try to update to other_user's email
        response = client.put(
            "/api/v1/users/me/profile",
            json={"email": other_user.email},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "already registered" in data["detail"]
