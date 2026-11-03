"""Kiểm thử tính năng Xoay vòng Refresh Token & Phát hiện dùng lại (M4, Tuần 3).

Các trường hợp:
1. Cấp và lưu refresh token vào Redis.
2. Xoay vòng thành công: dùng refresh token 1 lần lấy cặp token mới.
3. Phát hiện dùng lại (Token Reuse): trình lại refresh token đã dùng -> từ chối (401) và thu hồi TOÀN BỘ phiên của sinh viên.
4. Đăng xuất: thu hồi refresh token -> không dùng để refresh được nữa.
5. Sự cố Redis: từ chối refresh an toàn, không gây crash ứng dụng.
"""
from unittest.mock import AsyncMock, patch
import pytest
from fastapi import HTTPException

from app.api.v1.auth import logout, refresh
from app.core import tokens
from app.core.redis import (
    consume_refresh_token,
    refresh_token_key,
    revoke_all_user_tokens,
    store_refresh_token,
)
from app.schemas.auth import RefreshRequest


class FakeRedis:
    """Mock Redis in-memory phục vụ unit test."""

    def __init__(self):
        self.store = {}

    async def set(self, key, value, ex=None):
        self.store[key] = value
        return True

    async def delete(self, *keys):
        count = 0
        for k in keys:
            if k in self.store:
                del self.store[k]
                count += 1
        return count

    async def scan_iter(self, match="*"):
        prefix = match.rstrip("*")
        for k in list(self.store.keys()):
            if k.startswith(prefix):
                yield k


@pytest.mark.asyncio
async def test_store_and_consume_refresh_token():
    fake_redis = FakeRedis()
    with patch("app.core.redis.get_redis", return_value=fake_redis):
        user_id = 10
        jti = "test-jti-123"
        ttl = 3600

        # Lưu token
        ok = await store_refresh_token(user_id, jti, ttl)
        assert ok is True
        assert fake_redis.store[refresh_token_key(user_id, jti)] == "active"

        # Dùng lần 1: thành công
        consumed = await consume_refresh_token(user_id, jti)
        assert consumed is True
        assert refresh_token_key(user_id, jti) not in fake_redis.store

        # Dùng lần 2 (tái sử dụng): thất bại!
        reused = await consume_refresh_token(user_id, jti)
        assert reused is False


@pytest.mark.asyncio
async def test_revoke_all_user_tokens_on_reuse():
    fake_redis = FakeRedis()
    with patch("app.core.redis.get_redis", return_value=fake_redis):
        user_id = 42
        # Giả lập người dùng có 3 phiên đăng nhập khác nhau
        await store_refresh_token(user_id, "jti-1", 3600)
        await store_refresh_token(user_id, "jti-2", 3600)
        await store_refresh_token(user_id, "jti-3", 3600)
        # Phiên của người dùng khác
        await store_refresh_token(99, "jti-other", 3600)

        assert len(fake_redis.store) == 4

        # Thu hồi toàn bộ phiên của user 42
        revoked = await revoke_all_user_tokens(user_id)
        assert revoked == 3

        # Chỉ còn phiên của user 99
        assert len(fake_redis.store) == 1
        assert refresh_token_key(99, "jti-other") in fake_redis.store


@pytest.mark.asyncio
async def test_logout_revokes_token():
    fake_redis = FakeRedis()
    with patch("app.core.redis.get_redis", return_value=fake_redis):
        user_id = 5
        token = tokens.create_refresh_token(user_id, "student", "sv@uni.edu.vn")
        claims = tokens.decode_token(token, expected_type=tokens.REFRESH)

        # Lưu token
        await store_refresh_token(user_id, claims.jti, 3600)
        assert refresh_token_key(user_id, claims.jti) in fake_redis.store

        # Đăng xuất
        resp = await logout(RefreshRequest(refresh_token=token))
        assert resp.message == "Đăng xuất thành công"
        assert refresh_token_key(user_id, claims.jti) not in fake_redis.store


@pytest.mark.asyncio
async def test_refresh_token_reuse_detection_in_api():
    fake_redis = FakeRedis()
    with patch("app.core.redis.get_redis", return_value=fake_redis):
        user_id = 1
        token = tokens.create_refresh_token(user_id, "student", "sv0001@uni.edu.vn")

        mock_session = AsyncMock()

        # Gọi refresh khi token không tồn tại trong Redis -> ném 401 UNAUTHENTICATED
        with pytest.raises(HTTPException) as exc_info:
            await refresh(RefreshRequest(refresh_token=token), session=mock_session)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail["code"] == "UNAUTHENTICATED"


@pytest.mark.asyncio
async def test_redis_failure_fails_safe():
    with patch("app.core.redis.get_redis", side_effect=Exception("Redis connection error")):
        # Gặp sự cố kết nối: trả về False, không gây unhandled exception
        consumed = await consume_refresh_token(1, "jti-any")
        assert consumed is False
