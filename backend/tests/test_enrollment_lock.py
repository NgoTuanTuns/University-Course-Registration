import asyncio

import pytest
from fastapi import HTTPException

from app.core import redis as core_redis
from app.core.config import get_settings
from app.services.enrollment_lock import acquire_offering_lock

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
async def fresh_redis(clean_test_data):
    core_redis._redis_client = None
    yield
    await core_redis.close_redis()


async def test_expired_lock_does_not_release_new_owner(monkeypatch):
    monkeypatch.setattr(get_settings(), "enrollment_redis_lock_enabled", True)
    monkeypatch.setattr(get_settings(), "enrollment_lock_ttl_ms", 10)
    redis = core_redis.get_redis()
    async with acquire_offering_lock(123):
        assert await redis.get("lock:offering:123")
        await asyncio.sleep(0.03)
        assert await redis.set("lock:offering:123", "new-owner", nx=True, px=5000)
    assert await redis.get("lock:offering:123") == "new-owner"


async def test_gate_has_bounded_wait(monkeypatch):
    monkeypatch.setattr(get_settings(), "enrollment_redis_lock_enabled", True)
    monkeypatch.setattr(get_settings(), "enrollment_lock_wait_sec", 0.05)
    await core_redis.get_redis().set("lock:offering:456", "other-owner", px=5000)
    with pytest.raises(HTTPException) as caught:
        async with acquire_offering_lock(456):
            pytest.fail("must not enter held gate")
    assert caught.value.detail["code"] == "CONCURRENT_UPDATE"
