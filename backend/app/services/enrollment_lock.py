"""Optional admission lock. PostgreSQL remains authoritative if Redis fails."""

import asyncio
import logging
import random
from contextlib import asynccontextmanager
from time import monotonic
from uuid import uuid4

from redis.exceptions import RedisError

from app.core.config import get_settings
from app.core.errors import api_error
from app.core.redis import get_redis

logger = logging.getLogger(__name__)
RELEASE = "if redis.call('get',KEYS[1]) == ARGV[1] then return redis.call('del',KEYS[1]) else return 0 end"


@asynccontextmanager
async def acquire_offering_lock(offering_id: int, enabled: bool = True):
    settings = get_settings()
    acquired = False
    key, token = f"lock:offering:{offering_id}", uuid4().hex
    if enabled and settings.enrollment_redis_lock_enabled:
        deadline = monotonic() + settings.enrollment_lock_wait_sec
        try:
            async with asyncio.timeout(settings.enrollment_lock_wait_sec + 0.1):
                while True:
                    acquired = bool(
                        await get_redis().set(
                            key, token, nx=True, px=settings.enrollment_lock_ttl_ms
                        )
                    )
                    if acquired:
                        break
                    if monotonic() >= deadline:
                        raise api_error(
                            409, "CONCURRENT_UPDATE", "Lớp đang bận, hãy thử lại"
                        )
                    await asyncio.sleep(random.uniform(0.01, 0.04))
        except (RedisError, OSError, TimeoutError):
            logger.warning("Redis admission lock unavailable; using DB locks")
    try:
        yield
    finally:
        if acquired:
            try:
                async with asyncio.timeout(0.5):
                    await get_redis().eval(RELEASE, 1, key, token)
            except (RedisError, OSError, TimeoutError):
                logger.warning("Redis lock release failed; TTL will release it")
