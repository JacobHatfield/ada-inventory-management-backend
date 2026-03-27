"""
Unit tests for application configuration coverage.
Targets untested branches in Settings class.
"""

import json

from app.core.config import Settings


def test_cors_origins_none():
    """Test BACKEND_CORS_ORIGINS is None."""
    settings = Settings(BACKEND_CORS_ORIGINS=None)
    assert settings.cors_origins_list == []


def test_cors_origins_string_wildcard():
    """Test BACKEND_CORS_ORIGINS is wildcard."""
    settings = Settings(BACKEND_CORS_ORIGINS="*")
    assert settings.cors_origins_list == ["*"]


def test_cors_origins_single_string():
    """Test BACKEND_CORS_ORIGINS is a single string."""
    settings = Settings(BACKEND_CORS_ORIGINS="http://localhost:5173/")
    # Note: cors_origins_list handles strip and rstrip("/")
    assert settings.cors_origins_list == ["http://localhost:5173"]


def test_cors_origins_json_list_string():
    """Test BACKEND_CORS_ORIGINS is a JSON-formatted list string."""
    json_list = json.dumps(["http://test1.com", "http://test2.com/"])
    settings = Settings(BACKEND_CORS_ORIGINS=json_list)
    assert "http://test1.com" in settings.cors_origins_list
    assert "http://test2.com" in settings.cors_origins_list


def test_cors_origins_invalid_json_fallback():
    """Test BACKEND_CORS_ORIGINS fallback when JSON is invalid."""
    invalid_json = "[http://invalid-json"
    settings = Settings(BACKEND_CORS_ORIGINS=invalid_json)
    assert settings.cors_origins_list == [invalid_json]


def test_assemble_db_url_legacy_prefix():
    """Test assemble_db_url with legacy postgres:// prefix."""
    db_url = "postgres://user:pass@localhost/db"
    settings = Settings(DATABASE_URL=db_url)
    assert settings.DATABASE_URL == "postgresql+psycopg://user:pass@localhost/db"


def test_assemble_db_url_standard_prefix():
    """Test assemble_db_url with standard postgresql:// prefix."""
    db_url = "postgresql://user:pass@localhost/db"
    settings = Settings(DATABASE_URL=db_url)
    assert settings.DATABASE_URL == "postgresql+psycopg://user:pass@localhost/db"


def test_assemble_db_url_missing_driver():
    """Test assemble_db_url when +psycopg is missing."""
    db_url = "postgresql://localhost/db"
    settings = Settings(DATABASE_URL=db_url)
    assert settings.DATABASE_URL == "postgresql+psycopg://localhost/db"


def test_assemble_db_url_already_correct():
    """Test assemble_db_url when already using +psycopg."""
    db_url = "postgresql+psycopg://localhost/db"
    settings = Settings(DATABASE_URL=db_url)
    assert settings.DATABASE_URL == db_url


def test_strip_whitespace_and_quotes():
    """Test stripping whitespace and quotes from critical fields."""
    settings = Settings(
        SENDGRID_API_KEY=" 'SG.key' ",
        SMTP_FROM_EMAIL=' "test@example.com" ',
        FRONTEND_URL=" http://frontend.com/ ",
    )
    assert settings.SENDGRID_API_KEY == "SG.key"
    assert settings.SMTP_FROM_EMAIL == "test@example.com"
    assert settings.FRONTEND_URL == "http://frontend.com/"
