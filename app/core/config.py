"""Application configuration loaded from the environment.

All settings are prefixed with ``GRIT_`` (see ``.env.example``). A single cached
``Settings`` instance is exposed via :func:`get_settings`.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="GRIT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    env: str = "development"
    secret_key: str = "change-me"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14
    default_timezone: str = "Europe/Berlin"
    jwt_algorithm: str = "HS256"

    # Database
    database_url: str = "postgresql+asyncpg://grit:grit@localhost:5432/grit"
    sync_database_url: str | None = None

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # CORS — NoDecode stops pydantic-settings from JSON-decoding the env value so
    # our comma-split validator can handle plain "a,b,c" strings.
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def effective_sync_database_url(self) -> str:
        """Sync SQLAlchemy URL for Alembic and Celery workers.

        Falls back to deriving a psycopg URL from the async ``database_url``.
        """
        if self.sync_database_url:
            return self.sync_database_url
        return self.database_url.replace("+asyncpg", "+psycopg")


@lru_cache
def get_settings() -> Settings:
    return Settings()
