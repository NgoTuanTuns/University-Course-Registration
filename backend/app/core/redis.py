"""Shared asynchronous Redis client."""

from __future__ import annotations

import logging
import os

import redis.asyncio as aioredis
from redis.asyncio import Redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)
_redis_client: Redis | None = None


def get_redis_url() -> str:
    """Use Redis database 1 during tests and database 0 during normal runs."""
    settings = get_settings()
    if os.environ.get("APP_ENV") == "test" or "PYTEST_CURRENT_TEST" in os.environ:
        return settings.test_redis_url
    url = settings.redis_url
    if os.path.exists("/.dockerenv"):
        url = url.replace("@localhost:6380", "@redis:6379").replace(
            "@127.0.0.1:6380", "@redis:6379"
        )
    return url


def get_redis() -> Redis:
    """Create the shared client on first use."""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            get_redis_url(),
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


async def close_redis() -> None:
    """Close the shared client when the application stops."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None


def refresh_token_key(student_id: int, jti: str) -> str:
    return f"refresh:{student_id}:{jti}"


async def store_refresh_token(student_id: int, jti: str, ttl_seconds: int) -> bool:
    try:
        await get_redis().set(
            refresh_token_key(student_id, jti),
            "active",
            ex=ttl_seconds,
        )
        return True
    except Exception as exc:
        logger.warning("Unable to store refresh token in Redis: %s", exc)
        return False


async def consume_refresh_token(student_id: int, jti: str) -> bool:
    try:
        return await get_redis().delete(refresh_token_key(student_id, jti)) > 0
    except Exception as exc:
        logger.warning("Unable to consume refresh token in Redis: %s", exc)
        return False


async def revoke_all_user_tokens(student_id: int) -> int:
    try:
        client = get_redis()
        keys = [key async for key in client.scan_iter(match=f"refresh:{student_id}:*")]
        if keys:
            return await client.delete(*keys)
        return 0
    except Exception as exc:
        logger.warning("Unable to revoke user tokens in Redis: %s", exc)
        return 0


async def revoke_single_token(student_id: int, jti: str) -> bool:
    try:
        return await get_redis().delete(refresh_token_key(student_id, jti)) > 0
    except Exception as exc:
        logger.warning("Unable to revoke refresh token in Redis: %s", exc)
        return False
