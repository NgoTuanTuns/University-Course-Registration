"""Safely reset only the dedicated load-test database and export its users."""

from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path
from urllib.parse import urlsplit

from alembic.config import Config

from alembic import command
from app.core.config import get_settings
from app.seed import main_async

LOADTEST_DATABASE = "course_reg_loadtest"
LOADTEST_REDIS_DB = "2"


def validate_loadtest_target(app_env: str, database_url: str, redis_url: str) -> None:
    """Refuse destructive seeding unless every target is the isolated profile."""
    db = urlsplit(database_url)
    redis = urlsplit(redis_url)
    if app_env != "loadtest":
        raise ValueError("Refusing reset: APP_ENV must be exactly 'loadtest'.")
    if db.scheme not in {"postgresql", "postgresql+asyncpg"}:
        raise ValueError("Refusing reset: DATABASE_URL must use PostgreSQL.")
    if (
        db.hostname != "db"
        or db.port not in (None, 5432)
        or not db.username
        or db.path.lstrip("/") != LOADTEST_DATABASE
        or db.query
        or db.fragment
    ):
        raise ValueError(
            f"Refusing reset: DATABASE_URL must target db/{LOADTEST_DATABASE}."
        )
    if (
        redis.scheme != "redis"
        or redis.hostname != "redis"
        or redis.port not in (None, 6379)
        or redis.path != f"/{LOADTEST_REDIS_DB}"
        or redis.query
        or redis.fragment
    ):
        raise ValueError("Refusing reset: REDIS_URL must target Redis database 2.")


def main() -> None:
    settings = get_settings()
    database_url = os.environ.get("DATABASE_URL", settings.database_url)
    validate_loadtest_target(
        os.environ.get("APP_ENV", settings.app_env),
        database_url,
        os.environ.get("REDIS_URL", settings.redis_url),
    )

    data_dir = Path(os.environ.get("LOADTEST_DATA_DIR", "/data"))
    data_dir.mkdir(parents=True, exist_ok=True)
    # Invalidate old credentials before any reset step can fail or truncate data.
    (data_dir / "tokens.csv").unlink(missing_ok=True)
    (data_dir / "users.csv").unlink(missing_ok=True)

    # Migrations are non-destructive and must succeed before seed --reset truncates.
    os.environ["ALEMBIC_DATABASE_URL"] = database_url
    command.upgrade(Config("alembic.ini"), "head")

    args = argparse.Namespace(
        database_url=None,
        profile="loadtest",
        export_users=str(data_dir / "users.csv"),
        reset=True,
    )
    raise SystemExit(asyncio.run(main_async(args)))


if __name__ == "__main__":
    main()
