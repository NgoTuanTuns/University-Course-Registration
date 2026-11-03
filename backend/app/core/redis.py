"""Kết nối và tiện ích Redis (M4, Tuần 3).

Quy ước chung của nhóm (QUY_UOC_DU_AN.md, Mục 7 và kế hoạch M4):
- Biến môi trường REDIS_URL (mặc định redis://redis:6379/0 hoặc redis://localhost:6379/0).
- Khóa refresh token: refresh:{student_id}:{jti} (TTL = 7 ngày).
- Khóa rate-limit: ratelimit:{phạm vi}:{định danh} (TTL theo cửa sổ trượt).
"""
from __future__ import annotations

import logging
import os
from typing import Any

import redis.asyncio as aioredis
from redis.asyncio import Redis

logger = logging.getLogger(__name__)

_redis_client: Redis | None = None


def get_redis_url() -> str:
    return os.environ.get("REDIS_URL", "redis://localhost:6379/0")


def get_redis() -> Redis:
    """Khởi tạo Redis client lười (lazy initialization)."""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            get_redis_url(),
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


async def close_redis() -> None:
    """Đóng kết nối Redis (dùng khi shutdown app hoặc cleanup test)."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None


# --- Tiện ích quản lý Refresh Token (Xoay vòng & Phát hiện dùng lại) ---


def refresh_token_key(student_id: int, jti: str) -> str:
    return f"refresh:{student_id}:{jti}"


async def store_refresh_token(student_id: int, jti: str, ttl_seconds: int) -> bool:
    """Lưu jti của refresh token vào Redis. Trả về False nếu Redis không khả dụng."""
    try:
        r = get_redis()
        await r.set(refresh_token_key(student_id, jti), "active", ex=ttl_seconds)
        return True
    except Exception as exc:
        logger.warning("Không thể kết nối Redis để lưu refresh token: %s", exc)
        return False


async def consume_refresh_token(student_id: int, jti: str) -> bool:
    """Kiểm tra và thu hồi (xoay vòng) refresh token.

    Chỉ cho phép dùng 1 LẦN duy nhất:
    - Nếu key tồn tại: xóa key và trả về True.
    - Nếu key KHÔNG tồn tại: trả về False (token đã dùng hoặc đã bị thu hồi -> PHÁT HIỆN DÙNG LẠI).
    """
    try:
        r = get_redis()
        key = refresh_token_key(student_id, jti)
        # GETDEL trong Redis >= 6.2 hoặc script xóa nguyên tử
        deleted = await r.delete(key)
        return deleted > 0
    except Exception as exc:
        logger.warning("Không thể kết nối Redis để kiểm tra refresh token: %s", exc)
        return False


async def revoke_all_user_tokens(student_id: int) -> int:
    """Thu hồi TOÀN BỘ phiên của một sinh viên khi phát hiện dùng lại refresh token."""
    try:
        r = get_redis()
        pattern = f"refresh:{student_id}:*"
        keys = []
        async for key in r.scan_iter(match=pattern):
            keys.append(key)
        if keys:
            return await r.delete(*keys)
        return 0
    except Exception as exc:
        logger.warning("Không thể kết nối Redis để thu hồi toàn bộ token: %s", exc)
        return 0


async def revoke_single_token(student_id: int, jti: str) -> bool:
    """Thu hồi một refresh token cụ thể (dùng khi đăng xuất)."""
    try:
        r = get_redis()
        deleted = await r.delete(refresh_token_key(student_id, jti))
        return deleted > 0
    except Exception as exc:
        logger.warning("Không thể kết nối Redis để thu hồi token: %s", exc)
        return False
