"""Cơ sở dữ liệu (SQLAlchemy async) — session dependency.

Quy ước chung của nhóm (QUY_UOC_DU_AN.md, Mục 3 & Mục 6):
- core/db.py cung cấp get_session (FastAPI dependency trả AsyncSession).
- Khởi tạo engine/session_maker lười (lazy initialization) để việc import router
  hoặc chạy unit test không bắt buộc cấu hình DATABASE_URL.
- get_session KHÔNG tự commit; service quyết định commit/rollback transaction.
- Hỗ trợ định dạng PostgreSQL tiêu chuẩn (tự động chuyển postgresql:// thành postgresql+asyncpg://).
"""
from __future__ import annotations

import os
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Tạo engine và session factory ở lần dùng đầu tiên."""
    global _engine, _session_factory

    if _session_factory is not None:
        return _session_factory

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured")

    # Chấp nhận định dạng URL postgresql:// phổ biến và chuyển sang driver asyncpg
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace(
            "postgresql://", "postgresql+asyncpg://", 1
        )

    _engine = create_async_engine(database_url, pool_pre_ping=True)
    _session_factory = async_sessionmaker(
        bind=_engine, class_=AsyncSession, expire_on_commit=False
    )
    return _session_factory


# Alias tương thích ngược
_get_maker = _get_session_factory


async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield một session cho mỗi request; quyền commit/rollback thuộc về caller (service)."""
    factory = _get_session_factory()
    async with factory() as session:
        yield session
