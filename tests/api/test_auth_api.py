"""Authentication API endpoint tests."""
import pytest
from datetime import timedelta
from fastapi import status
from jose import jwt

from app.core.config import settings
from app.core.security import create_access_token
from app.models.user import User


class TestRegister:
    """Test user registration endpoint."""

    def test_register_success(self, client):
        """Test successful user registration."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "password123",
                "full_name": "New User",
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["full_name"] == "New User"
        assert data["is_active"] is True
        assert "id" in data
        assert "hashed_password" not in data  # Should not expose password

    def test_register_duplicate_email(self, client, test_user):
        """Test registration with duplicate email returns 409."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "testuser@example.com",  # Already exists
                "password": "password123",
                "full_name": "Duplicate User",
            },
        )
        assert response.status_code == status.HTTP_409_CONFLICT
        assert "already registered" in response.json()["detail"].lower()

    def test_register_invalid_email(self, client):
        """Test registration with invalid email format returns 422."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "password": "password123",
                "full_name": "Test User",
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_register_short_password(self, client):
        """Test registration with password less than 8 characters returns 422."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "short",
                "full_name": "Test User",
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_register_missing_email(self, client):
        """Test registration without email returns 422."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "password": "password123",
                "full_name": "Test User",
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_register_missing_password(self, client):
        """Test registration without password returns 422."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "full_name": "Test User",
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_register_without_full_name(self, client):
        """Test registration without full_name is allowed (optional field)."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "minimal@example.com",
                "password": "password123",
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["email"] == "minimal@example.com"
        assert data["full_name"] is None


class TestLogin:
    """Test user login endpoint."""

    def test_login_success(self, client, test_user):
        """Test successful login with valid credentials."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "testuser@example.com",
                "password": "testpassword123",
            },
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert isinstance(data["access_token"], str)
        assert len(data["access_token"]) > 0

    def test_login_wrong_password(self, client, test_user):
        """Test login with wrong password returns 401."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "testuser@example.com",
                "password": "wrongpassword",
            },
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "WWW-Authenticate" in response.headers

    def test_login_nonexistent_user(self, client):
        """Test login with non-existent user returns 401."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "password123",
            },
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_inactive_user(self, client, inactive_user):
        """Test login with inactive user returns 403."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "inactive@example.com",
                "password": "testpassword123",
            },
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "inactive" in response.json()["detail"].lower()

    def test_login_invalid_email_format(self, client):
        """Test login with invalid email format returns 422."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "not-an-email",
                "password": "password123",
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_login_missing_credentials(self, client):
        """Test login without credentials returns 422."""
        response = client.post("/api/v1/auth/login", json={})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestGetCurrentUser:
    """Test get current user endpoint."""

    def test_get_current_user_success(self, client, auth_headers):
        """Test getting current user with valid token."""
        response = client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == "testuser@example.com"
        assert data["full_name"] == "Test User"
        assert data["is_active"] is True
        assert "id" in data
        assert "hashed_password" not in data

    def test_get_current_user_no_token(self, client):
        """Test getting current user without token returns 401."""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_current_user_invalid_token(self, client):
        """Test getting current user with invalid token returns 401."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid-token-here"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_current_user_malformed_bearer(self, client):
        """Test getting current user with malformed bearer header returns 401."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "NotBearer token"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_current_user_inactive(self, client, inactive_user):
        """Test getting current user when user becomes inactive returns 403."""
        # First login to get token
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "inactive@example.com",
                "password": "testpassword123",
            },
        )
        # Should fail at login stage for inactive user
        assert login_response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_current_user_deactivated_after_login(self, client, db, test_user):
        """Test accessing endpoint when user is deactivated after getting token."""
        # Get a valid token while user is active
        token = create_access_token(test_user.id)
        
        # Deactivate the user
        test_user.is_active = False
        db.commit()
        db.refresh(test_user)
        
        # Try to access protected endpoint with valid token
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        # Should fail because user is now inactive
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "inactive" in response.json()["detail"].lower()

    def test_get_current_user_deleted_user(self, client, db, test_user):
        """Test getting current user when user is deleted from DB returns 401."""
        # Create a valid token
        token = create_access_token(test_user.id)
        
        # Delete the user from database
        db.query(User).filter(User.id == test_user.id).delete()
        db.commit()
        
        # Try to use the token
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestHealthCheck:
    """Test health check endpoint."""

    def test_health_check(self, client):
        """Test health check endpoint returns healthy status."""
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"status": "healthy"}


class TestTokenExpiration:
    """Test custom token expiration scenarios."""

    def test_create_token_with_custom_expiration(self, test_user):
        """Test creating a token with custom expiration time."""
        custom_expiration = timedelta(minutes=5)
        token = create_access_token(test_user.id, expires_delta=custom_expiration)
        
        # Decode token to verify expiration
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert "exp" in payload
        assert int(payload["sub"]) == test_user.id
