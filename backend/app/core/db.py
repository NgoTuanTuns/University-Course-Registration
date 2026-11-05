"""Cơ sở dữ liệu (SQLAlchemy async) — session dependency."""
from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Tạo engine và session factory ở lần dùng đầu tiên."""
    global _engine, _session_factory

    if _session_factory is not None:
        return _session_factory

    settings = get_settings()
    database_url = settings.database_url
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace(
            "postgresql://", "postgresql+asyncpg://", 1
        )

    _engine = create_async_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
    )
    _session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return _session_factory


# Alias tương thích ngược
_get_maker = _get_session_factory


async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield một session; quyền commit/rollback thuộc về service."""
    factory = _get_session_factory()
    async with factory() as session:
        yield session
