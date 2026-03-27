"""
Application configuration
- Settings class using pydantic-settings
- Environment variables
- Database configuration
- JWT configuration
- CORS configuration
- Rate limiting configuration
- Email configuration (optional)
"""

from typing import Union

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Database Configuration
    DATABASE_URL: str = (
        "postgresql+psycopg://inventory_user:inventory_password@localhost:5432/inventory_db"
    )

    # JWT Configuration
    SECRET_KEY: str = "dev-secret-key-placeholder-for-cicd"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS Configuration
    BACKEND_CORS_ORIGINS: Union[str, list[str]] = (
        "http://localhost:5173,http://127.0.0.1:5173"
    )

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    # Email Configuration (Optional)
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_FROM_NAME: str = "Inventory Management System"
    SENDGRID_API_KEY: str = ""

    # Frontend Configuration (for password reset links)
    FRONTEND_URL: str = "http://localhost:3000"

    # Application Settings
    PROJECT_NAME: str = "Inventory Management API"
    VERSION: str = "1.0.0"
    DEBUG: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",  # Ignore extra environment variables to prevent validation errors
    )

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(
        cls, v: Union[str, list[str], None]
    ) -> Union[str, list[str]]:
        """Validate and parse CORS origins from string, list, or JSON string"""
        if v is None:
            return []
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        if isinstance(v, list):
            return v
        if isinstance(v, str) and v.startswith("["):
            import json

            try:
                return json.loads(v)
            except Exception:
                # Fallback to single string if JSON parsing fails
                return [v]
        return v

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_url(cls, v: str) -> str:
        """Ensure DATABASE_URL uses the +psycopg driver for SQLAlchemy 2.0/psycopg3 compatibility"""
        if isinstance(v, str):
            # Handle both postgres:// (legacy) and postgresql:// prefixes
            if v.startswith("postgres://"):
                v = v.replace("postgres://", "postgresql+psycopg://", 1)
            elif v.startswith("postgresql://"):
                v = v.replace("postgresql://", "postgresql+psycopg://", 1)
            # Ensure it has +psycopg if it's already postgresql:// but without driver
            elif v.startswith("postgresql") and "+psycopg" not in v:
                v = v.replace("postgresql", "postgresql+psycopg", 1)
        return v

    @property
    def cors_origins_list(self) -> list[str]:
        """Convert BACKEND_CORS_ORIGINS to a clean list of strings (stripping trailing slashes)"""
        origins = self.BACKEND_CORS_ORIGINS
        if isinstance(origins, str):
            if origins == "*":
                return ["*"]
            return [origins.strip().rstrip("/")]

        # Handle case where list elements might be Pydantic URL objects or strings
        return [str(origin).strip().rstrip("/") for origin in origins]


# Create global settings instance
settings = Settings()
