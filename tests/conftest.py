"""Pytest configuration and fixtures for testing."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.database import Base, get_db
from app.main import app
from app.models.category import Category
from app.models.inventory import InventoryItem
from app.models.user import User

# Use in-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    """Create a fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    """Create a test client with database override."""

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db):
    """Create a test user in the database."""
    user = User(
        email="testuser@example.com",
        hashed_password=hash_password("testpassword123"),
        full_name="Test User",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def inactive_user(db):
    """Create an inactive test user in the database."""
    user = User(
        email="inactive@example.com",
        hashed_password=hash_password("testpassword123"),
        full_name="Inactive User",
        is_active=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def auth_headers(client, test_user):
    """Generate authentication headers for test user."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "testuser@example.com", "password": "testpassword123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_inventory_item(db, test_user):
    """Create a test inventory item for test_user."""
    item = InventoryItem(
        name="Test Widget",
        description="A test inventory item",
        quantity=100,
        low_stock_threshold=10,
        user_id=test_user.id,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@pytest.fixture
def other_user(db):
    """Create another user for isolation testing."""
    user = User(
        email="otheruser@example.com",
        hashed_password=hash_password("otherpassword123"),
        full_name="Other User",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def other_user_inventory_item(db, other_user):
    """Create an inventory item for other_user (for authorization tests)."""
    item = InventoryItem(
        name="Other User's Item",
        description="An item belonging to another user",
        quantity=50,
        low_stock_threshold=5,
        user_id=other_user.id,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@pytest.fixture
def test_category(db, test_user):
    """Create a test category for test_user."""
    category = Category(
        name="Test Category",
        description="A test category",
        user_id=test_user.id,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@pytest.fixture
def other_user_category(db, other_user):
    """Create a category for other_user (for authorization tests)."""
    category = Category(
        name="Other User's Category",
        description="A category belonging to another user",
        user_id=other_user.id,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category
