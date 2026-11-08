"""Application settings loaded from environment variables or the local .env file."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "dev"
    cors_origins: str = "http://localhost:5173,http://localhost:8080"

    database_url: str = (
        "postgresql+asyncpg://course_user:local_dev_password@localhost:5433/course_reg"
    )
    test_database_url: str = "postgresql+asyncpg://course_user:local_dev_password@localhost:5433/course_reg_test"
    redis_url: str = "redis://redis:6379/0"
    test_redis_url: str = "redis://redis:6379/1"

    # Example placeholder for local development; not a real secret.
    jwt_secret: str = "dev-only-secret-change-before-any-shared-deployment"
    access_token_ttl_min: int = 30
    refresh_token_ttl_days: int = 7

    default_max_credits: int = 25
    waitlist_max_ratio: float = 0.2
    prereq_cache_ttl_sec: int = 600
    prereq_graph_cache_ttl_sec: int = 3600
    prereq_graph_lock_ttl_sec: int = 5
    prereq_rate_limit_per_min: int = 120
    prereq_explain_max_items: int = 50
    db_pool_size: int = 5
    db_max_overflow: int = 10

    model_config = SettingsConfigDict(
        env_file=(
            ".env",
            "../.env",
            str(Path(__file__).resolve().parents[3] / ".env"),
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [
            origin.strip() for origin in self.cors_origins.split(",") if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
