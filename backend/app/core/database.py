"""Async SQLAlchemy session dependency.

Set DATABASE_URL to an async SQLAlchemy URL, for example:
postgresql+asyncpg://user:password@localhost:5432/university
The engine is initialized lazily so importing routers does not require DB configuration.
"""
from __future__ import annotations

import os
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _engine, _session_factory

    if _session_factory is not None:
        return _session_factory

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured")

    # Accept the common PostgreSQL URL form and use the async driver.
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace(
            "postgresql://", "postgresql+asyncpg://", 1
        )

    _engine = create_async_engine(database_url, pool_pre_ping=True)
    _session_factory = async_sessionmaker(
        bind=_engine, class_=AsyncSession, expire_on_commit=False
    )
    return _session_factory


async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield one request-scoped session; transaction ownership stays with the caller."""
    factory = _get_session_factory()
    async with factory() as session:
        yield session
