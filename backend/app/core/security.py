"""Xác thực và phân quyền (M4).

  get_current_user : dependency FastAPI đọc `Authorization: Bearer <access_token>`
                     - không có / sai định dạng / sai chữ ký / sai loại token -> 401 UNAUTHENTICATED
                     - đúng chữ ký nhưng hết hạn                              -> 401 TOKEN_EXPIRED
                       (frontend dùng refresh token để lấy token mới)
  require_role     : dependency factory, sai vai trò -> 403 FORBIDDEN (chỉ có 2 vai trò: student, admin)
  hash_password / verify_password : bcrypt; verify chạy trong thread pool để không chặn vòng lặp sự kiện

Cách bắt buộc đăng nhập cho một router (M2, M3 thêm vào router của mình):
    router = APIRouter(prefix="/enroll", dependencies=[Depends(get_current_user)])
Nếu endpoint cần biết là ai:  user: CurrentUser = Depends(get_current_user)

Token trong test: xem tests/auth_helpers.py (auth_headers).
Lưu ý: vai trò và email lấy từ token (hết hạn sau ACCESS_TOKEN_TTL_MIN phút), không tra lại DB mỗi request.
"""

from dataclasses import dataclass
from typing import Annotated, Literal

import bcrypt
from fastapi import Depends, Header
from starlette.concurrency import run_in_threadpool

from app.core import tokens
from app.core.errors import api_error

Role = Literal["student", "admin"]
BCRYPT_ROUNDS = (
    12  # độ chậm cố ý của bcrypt (tham số thuật toán, không phải cấu hình triển khai)
)


@dataclass(frozen=True)
class CurrentUser:
    id: int
    role: Role
    email: str


async def get_current_user(
    authorization: str | None = Header(default=None),
) -> CurrentUser:
    """Trả người dùng hiện tại từ access token, hoặc ném 401."""
    if not authorization:
        raise api_error(401, "UNAUTHENTICATED", "Vui lòng đăng nhập")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise api_error(401, "UNAUTHENTICATED", "Vui lòng đăng nhập")
    try:
        claims = tokens.decode_token(token.strip(), expected_type=tokens.ACCESS)
    except tokens.TokenExpiredError:
        raise api_error(401, "TOKEN_EXPIRED", "Phiên đăng nhập đã hết hạn") from None
    except tokens.InvalidTokenError:
        raise api_error(401, "UNAUTHENTICATED", "Vui lòng đăng nhập") from None
    return CurrentUser(id=claims.user_id, role=claims.role, email=claims.email)


def require_role(role: Role):
    """Dependency factory: `Depends(require_role("admin"))`. Sai quyền -> 403 FORBIDDEN."""

    async def checker(
        user: Annotated[CurrentUser, Depends(get_current_user)],
    ) -> CurrentUser:
        if user.role != role:
            raise api_error(
                403, "FORBIDDEN", "Bạn không có quyền thực hiện thao tác này"
            )
        return user

    return checker


def hash_password(plain: str) -> str:
    """Băm bcrypt (chậm có chủ đích)."""
    return bcrypt.hashpw(
        plain.encode("utf-8"), bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    ).decode("utf-8")


async def verify_password(plain: str, hashed: str) -> bool:
    """So sánh mật khẩu trong thread pool để không chặn vòng lặp sự kiện."""

    def _check() -> bool:
        try:
            return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
        except ValueError:  # hash hỏng
            return False

    return await run_in_threadpool(_check)
