"""
FastAPI microservice configuration.
Loads all settings from environment variables via pydantic-settings.
"""
import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Google AI ────────────────────────────────────────────────
    GOOGLE_API_KEY: str = ""

    # ── Database (same MySQL as Django) ─────────────────────────
    # Django uses MYSQL_URL like: mysql://user:pass@host:3306/db
    # We convert to async: mysql+aiomysql://user:pass@host:3306/db
    MYSQL_URL: str = ""

    @property
    def async_database_url(self) -> str:
        """Convert Django's MYSQL_URL to SQLAlchemy async format."""
        url = self.MYSQL_URL
        if url.startswith("mysql://"):
            return url.replace("mysql://", "mysql+aiomysql://", 1)
        if url.startswith("mysql+aiomysql://"):
            return url
        return f"mysql+aiomysql://{url}"

    # ── Redis ───────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── JWT (same secret as Django for token validation) ────────
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"

    # ── Django API (for mutations via DRF) ──────────────────────
    DJANGO_API_URL: str = "http://localhost:8000/api/v1"
    DJANGO_ADMIN_TOKEN: str = ""  # Pre-generated JWT for service-to-service

    # ── CORS ────────────────────────────────────────────────────
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    # ── Gmail OAuth2 ────────────────────────────────────────────
    GMAIL_CREDENTIALS_PATH: str = "./credentials.json"
    GMAIL_TOKEN_PATH: str = "./token.json"

    # ── Google Calendar ─────────────────────────────────────────
    CALENDAR_ID: str = "primary"

    # ── Service ─────────────────────────────────────────────────
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8001


@lru_cache
def get_settings() -> Settings:
    return Settings()
