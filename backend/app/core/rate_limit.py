"""Rate-limiting module bằng Redis (M4, Tuần 3).

Quy ước chung của nhóm (QUY_UOC_DU_AN.md, Mục 7 và kế hoạch M4 Mục 3.2):
- Cơ chế: Bộ đếm nguyên tử trong Redis (INCR + EXPIRE).
- Khóa dạng: ratelimit:{phạm vi}:{định danh}
- Vượt ngưỡng: trả 429 mã RATE_LIMITED kèm header Retry-After.
- Khi APP_ENV=loadtest hoặc RATE_LIMIT_ENABLED=false: tự động bỏ qua để phục vụ kiểm thử tải.
- Khi Redis gặp sự cố: cho qua và ghi log cảnh báo (ưu tiên tính khả dụng).
"""

from __future__ import annotations

import logging
import os

from fastapi import HTTPException, Request

from app.core.errors import api_error
from app.core.redis import get_redis

logger = logging.getLogger(__name__)

# Script Lua nguyên tử: tăng biến đếm, đặt TTL lần đầu, trả về [allowed (1/0), retry_after/remaining]
RATE_LIMIT_LUA = """
local key = KEYS[1]
local limit = tonumber(ARGV[1])
local window = tonumber(ARGV[2])

local current = redis.call('INCR', key)
if current == 1 then
    redis.call('EXPIRE', key, window)
end
local ttl = redis.call('TTL', key)
if ttl < 0 then
    ttl = window
    redis.call('EXPIRE', key, window)
end

if current > limit then
    return {0, ttl}
else
    return {1, limit - current}
end
"""


def is_rate_limit_disabled() -> bool:
    """Kiểm tra có đang ở môi trường kiểm thử tải không."""
    if os.environ.get("APP_ENV") == "loadtest":
        return True
    if os.environ.get("RATE_LIMIT_ENABLED", "true").lower() in ("false", "0", "no"):
        return True
    return False


def get_client_ip(request: Request) -> str:
    """Lấy IP của client, ưu tiên header do Nginx của dự án chuyển tiếp."""
    forwarded = request.headers.get("X-Forwarded-For") or request.headers.get(
        "x-forwarded-for"
    )
    if forwarded:
        # Lấy IP đầu tiên trong chuỗi
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP") or request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"


async def check_rate_limit(
    scope: str,
    identifier: str,
    limit: int = 60,
    window_seconds: int = 60,
) -> None:
    """Kiểm tra rate-limit. Nếu vượt ngưỡng -> ném HTTPException 429 RATE_LIMITED."""
    if is_rate_limit_disabled():
        return

    key = f"ratelimit:{scope}:{identifier}"
    try:
        r = get_redis()
        # eval script Lua
        res = await r.eval(RATE_LIMIT_LUA, 1, key, limit, window_seconds)
        allowed, val = res[0], res[1]
        if allowed == 0:
            retry_after = max(1, int(val))
            raise api_error(
                status_code=429,
                code="RATE_LIMITED",
                message="Quá nhiều yêu cầu, vui lòng thử lại sau",
                headers={"Retry-After": str(retry_after)},
                retry_after=retry_after,
            )
    except HTTPException:
        raise
    except Exception as exc:
        # Khi Redis lỗi: ưu tiên tính khả dụng, cho phép request đi qua và ghi log
        logger.warning("Lỗi Redis trong check_rate_limit (%s): %s", key, exc)
