"""Điểm khởi tạo FastAPI và các router dùng chung."""

from __future__ import annotations

import logging
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1 import admin, auth, courses, enroll, prerequisites, timetable, waitlist
from app.core.config import get_settings
from app.core.db import get_session
from app.core.errors import register_error_handlers
from app.core.redis import close_redis, get_redis
from app.services import prerequisite_engine

settings = get_settings()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def _warm_prerequisite_graph() -> None:
    """Nạp sẵn DAG tiên quyết vào Redis để request đầu tiên không phải dựng lại.
    Không bắt buộc: DB chưa migrate hoặc Redis tắt thì chỉ ghi cảnh báo."""
    try:
        async for session in get_session():
            await prerequisite_engine.warm_graph_cache(session)
    except Exception as exc:
        logger.warning("Bỏ qua làm nóng cache tiên quyết: %s", exc)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    await _warm_prerequisite_graph()
    yield
    await close_redis()


app = FastAPI(
    title="University Course Registration API",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
register_error_handlers(app)

api_router_prefix = "/api/v1"
app.include_router(auth.router, prefix=api_router_prefix)
app.include_router(admin.router, prefix=api_router_prefix)
app.include_router(prerequisites.router, prefix=api_router_prefix)
app.include_router(courses.router, prefix=api_router_prefix)
app.include_router(enroll.router, prefix=api_router_prefix)
app.include_router(timetable.router, prefix=api_router_prefix)
app.include_router(waitlist.router, prefix=api_router_prefix)


@app.get("/health", tags=["health"])
async def health(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, str]:
    try:
        await session.execute(text("SELECT 1"))
        await get_redis().ping()
    except Exception as exc:
        logger.warning("Health check failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail={
                "code": "DEPENDENCIES_UNAVAILABLE",
                "message": "Database or Redis is unavailable",
            },
        ) from exc
    return {"status": "ok"}
