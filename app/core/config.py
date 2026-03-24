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

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Database Configuration
    DATABASE_URL: str = "postgresql+psycopg://inventory_user:inventory_password@localhost:5432/inventory_db"

    # JWT Configuration
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS Configuration
    BACKEND_CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

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

    class Config:
        env_file = ".env"
        case_sensitive = True

    @property
    def cors_origins_list(self) -> list[str]:
        """Convert BACKEND_CORS_ORIGINS string to list"""
        return [
            origin.strip()
            for origin in self.BACKEND_CORS_ORIGINS.split(",")
            if origin.strip()
        ]


# Create global settings instance
settings = Settings()
