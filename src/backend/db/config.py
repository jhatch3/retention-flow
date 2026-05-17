"""Database configuration, loaded from environment variables / ``.env``."""

from __future__ import annotations

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Connection and pool settings for the Postgres database.

    Values are read from environment variables (case-insensitive) or a local
    ``.env`` file. See ``.env.example`` for the supported keys.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = (
        "postgresql+psycopg2://postgres:postgres@localhost:5432/retention_flow"
    )
    db_echo: bool = False
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_pre_ping: bool = True

    @field_validator("database_url")
    @classmethod
    def _ensure_driver(cls, value: str) -> str:
        """Pin the psycopg2 driver.

        Supabase and many hosted providers hand out bare ``postgresql://`` (or
        ``postgres://``) URLs. Normalising here keeps the engine on a known,
        installed driver regardless of what gets pasted into ``.env``.
        """
        if value.startswith("postgresql+"):
            return value
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg2://", 1)
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+psycopg2://", 1)
        return value


@lru_cache
def get_settings() -> DatabaseSettings:
    """Return the cached database settings instance."""
    return DatabaseSettings()
