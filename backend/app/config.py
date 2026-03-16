"""App configuration from environment variables."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    # Database
    database_url: str = "postgresql://localhost:5432/finflow"

    # JWT
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_expires_in: str = "1h"
    jwt_refresh_expires_in: str = "7d"

    # Server
    port: int = 8001
    env: str = "development"

    # CORS
    cors_origin: str = "http://localhost:8080"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()
