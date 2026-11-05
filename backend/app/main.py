"""Điểm khởi tạo FastAPI và các router dùng chung."""
from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1 import admin, auth, prerequisites
from app.core.config import get_settings
from app.core.db import get_session
from app.core.errors import register_error_handlers
from app.core.redis import close_redis, get_redis

settings = get_settings()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
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


@app.get("/health", tags=["health"])
async def health(
    session: AsyncSession = Depends(get_session),
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
