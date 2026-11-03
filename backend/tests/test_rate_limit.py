"""Kiểm thử tính năng Giới hạn tần suất - Rate Limiting (M4, Tuần 3).

Các trường hợp:
1. Yêu cầu trong ngưỡng cho phép: bình thường.
2. Yêu cầu vượt ngưỡng: ném 429 RATE_LIMITED kèm Retry-After header.
3. Bỏ qua rate limit khi APP_ENV=loadtest hoặc RATE_LIMIT_ENABLED=false.
4. Nhận diện IP máy khách chính xác (X-Forwarded-For, X-Real-IP).
5. Redis gặp sự cố: ghi log cảnh báo và cho qua (ưu tiên khả dụng).
"""
import os
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi import HTTPException, Request

from app.core.rate_limit import (
    check_rate_limit,
    get_client_ip,
    is_rate_limit_disabled,
)


@pytest.mark.asyncio
async def test_rate_limit_allowed():
    mock_redis = AsyncMock()
    mock_redis.eval.return_value = [1, 4]
    with patch("app.core.rate_limit.get_redis", return_value=mock_redis):
        await check_rate_limit("login", "127.0.0.1:test@uni.edu.vn", limit=5, window_seconds=60)
        assert mock_redis.eval.called


@pytest.mark.asyncio
async def test_rate_limit_exceeded_raises_429():
    mock_redis = AsyncMock()
    mock_redis.eval.return_value = [0, 45]
    with patch("app.core.rate_limit.get_redis", return_value=mock_redis):
        with pytest.raises(HTTPException) as exc_info:
            await check_rate_limit("login", "127.0.0.1:test@uni.edu.vn", limit=5, window_seconds=60)

        assert exc_info.value.status_code == 429
        assert exc_info.value.detail["code"] == "RATE_LIMITED"
        assert exc_info.value.headers["Retry-After"] == "45"


@pytest.mark.asyncio
async def test_rate_limit_disabled_in_loadtest():
    with patch.dict(os.environ, {"APP_ENV": "loadtest"}):
        assert is_rate_limit_disabled() is True
        mock_redis = AsyncMock()
        with patch("app.core.rate_limit.get_redis", return_value=mock_redis):
            await check_rate_limit("api", "user:1", limit=1, window_seconds=60)
            assert not mock_redis.eval.called


def test_rate_limit_disabled_via_flag():
    with patch.dict(os.environ, {"RATE_LIMIT_ENABLED": "false"}):
        assert is_rate_limit_disabled() is True


def test_get_client_ip():
    # 1. X-Forwarded-For (chọn IP đầu tiên)
    req1 = MagicMock(spec=Request)
    req1.headers = {"x-forwarded-for": "203.0.113.195, 70.41.3.18, 150.172.238.178"}
    assert get_client_ip(req1) == "203.0.113.195"

    # 2. X-Real-IP
    req2 = MagicMock(spec=Request)
    req2.headers = {"x-real-ip": "198.51.100.1"}
    assert get_client_ip(req2) == "198.51.100.1"

    # 3. Client host fallback
    req3 = MagicMock(spec=Request)
    req3.headers = {}
    req3.client.host = "192.168.1.50"
    assert get_client_ip(req3) == "192.168.1.50"


@pytest.mark.asyncio
async def test_rate_limit_redis_failure_fails_open():
    with patch("app.core.rate_limit.get_redis", side_effect=Exception("Redis down")):
        # Không ném lỗi khi Redis gặp sự cố
        await check_rate_limit("login", "127.0.0.1:sv@uni.edu.vn", limit=5, window_seconds=60)
