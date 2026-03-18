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

    # LLM (Groq - OpenAI compatible)
    groq_api_key: str = ""
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_model: str = "llama3-8b-8192"

    # Stock price update
    # - used by background updater for investment price refresh
    stock_price_provider: str = "stooq"  # stooq (default)
    stock_price_update_interval_seconds: int = 600  # 10 minutes
    stock_price_prune_days: int = 7  # daily history retention (prune)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()
