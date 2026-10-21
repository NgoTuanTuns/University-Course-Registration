"""Xác thực và phân quyền (M4).

TUẦN 1 (file này): chỉ có KHUNG để M2/M3 viết code trước khi JWT thật xong.
  - get_current_user: bản TẠM đọc header `X-Debug-User: <id>:<role>` khi APP_ENV=dev.
    Ví dụ:  X-Debug-User: 1:student   hoặc   X-Debug-User: 1001:admin  (id sinh viên = số trong svNNNN)
  - Bản thật dùng JWT sẽ thay vào ở TUẦN 2. Khi đó XÓA nhánh X-Debug-User.
  - hash_password / verify_password đã là bản thật (bcrypt) vì seed cần dùng ngay.
"""
import os
from dataclasses import dataclass
from typing import Literal

import bcrypt
from fastapi import Depends, Header, HTTPException
from starlette.concurrency import run_in_threadpool

try:  # M5 dựng core/errors.py; chưa có thì dùng bản tạm cùng dạng lỗi chung của dự án
    from app.core.errors import api_error
except ImportError:  # pragma: no cover - xóa khối này khi core/errors.py đã có trên main

    def api_error(status: int, code: str, message: str, **extra) -> HTTPException:
        return HTTPException(status_code=status, detail={"code": code, "message": message, **extra})


Role = Literal["student", "admin"]
BCRYPT_ROUNDS = 12  # độ chậm cố ý của bcrypt (tham số thuật toán, không phải cấu hình triển khai)


@dataclass(frozen=True)
class CurrentUser:
    id: int
    role: Role
    email: str


async def get_current_user(
    authorization: str | None = Header(default=None),
    x_debug_user: str | None = Header(default=None),
) -> CurrentUser:
    """Dependency FastAPI: trả người dùng hiện tại hoặc 401."""
    # --- BẢN TẠM (xóa ở Tuần 2 khi JWT xong) ---
    if os.getenv("APP_ENV") == "dev" and x_debug_user:
        try:
            raw_id, raw_role = x_debug_user.split(":", 1)
            if raw_role not in ("student", "admin"):
                raise ValueError
            return CurrentUser(id=int(raw_id), role=raw_role, email=f"debug{int(raw_id)}@local")
        except ValueError:
            raise api_error(401, "UNAUTHENTICATED", "Header X-Debug-User phải có dạng <id>:<student|admin>")
    # --- hết bản tạm ---

    # TODO(M4, Tuần 2): đọc `authorization` (Bearer), giải mã JWT, phân biệt TOKEN_EXPIRED / UNAUTHENTICATED.
    raise api_error(401, "UNAUTHENTICATED", "Vui lòng đăng nhập")


def require_role(role: Role):
    """Dependency factory: `Depends(require_role("admin"))`. Sai quyền -> 403 FORBIDDEN."""

    async def checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role != role:
            raise api_error(403, "FORBIDDEN", "Bạn không có quyền thực hiện thao tác này")
        return user

    return checker


def hash_password(plain: str) -> str:
    """Băm bcrypt (chậm có chủ đích). Đừng gọi trực tiếp trong request async: dùng verify_password."""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode("utf-8")


async def verify_password(plain: str, hashed: str) -> bool:
    """So sánh mật khẩu trong thread pool để không chặn vòng lặp sự kiện."""

    def _check() -> bool:
        try:
            return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
        except ValueError:  # hash hỏng
            return False

    return await run_in_threadpool(_check)
