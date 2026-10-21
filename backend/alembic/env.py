"""Alembic chạy bất đồng bộ (asyncpg), đọc URL database từ môi trường.

Thứ tự ưu tiên chọn URL:
  1. tham số dòng lệnh:  alembic -x dburl=postgresql+asyncpg://... upgrade head
  2. biến ALEMBIC_DATABASE_URL (dùng cho test/tải nếu cần)
  3. biến DATABASE_URL (mặc định, lấy từ .env)
"""
import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    url = (
        context.get_x_argument(as_dictionary=True).get("dburl")
        or os.environ.get("ALEMBIC_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
    )
    if not url:
        raise RuntimeError("Chưa có URL database: đặt DATABASE_URL (hoặc dùng -x dburl=...)")
    return url


def run_migrations_offline() -> None:
    """Chế độ offline: chỉ in SQL (alembic upgrade head --sql), không cần kết nối DB."""
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        {"sqlalchemy.url": get_url()},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
