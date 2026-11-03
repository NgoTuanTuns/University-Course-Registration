"""Tạo và kiểm tra JWT (M4, Tuần 2).

Module THUẦN: chỉ cần PyJWT, không phụ thuộc FastAPI hay database, nên test được độc lập.
Cấu hình lấy từ .env (đúng tên biến trong .env.example của quy ước):
    JWT_SECRET, ACCESS_TOKEN_TTL_MIN (30), REFRESH_TOKEN_TTL_DAYS (7), APP_ENV

Hai loại token, không dùng thay nhau được (claim `type`):
    access  - gửi kèm mỗi request:  Authorization: Bearer <access_token>
    refresh - chỉ dùng để xin access token mới ở POST /auth/refresh
"""
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt

ALGORITHM = "HS256"
ACCESS = "access"
REFRESH = "refresh"
VALID_ROLES = ("student", "admin")
MIN_SECRET_LENGTH = 32
_PLACEHOLDER_SECRET = "doi_thanh_chuoi_bat_ky_dai_mot_chut"  # giá trị mẫu trong .env.example


class TokenExpiredError(Exception):
    """Token đúng chữ ký nhưng đã hết hạn  ->  API trả TOKEN_EXPIRED."""


class InvalidTokenError(Exception):
    """Token sai định dạng / sai chữ ký / sai loại  ->  API trả UNAUTHENTICATED."""


@dataclass(frozen=True)
class TokenClaims:
    user_id: int
    role: str
    email: str
    token_type: str
    jti: str


def get_secret() -> str:
    """Đọc JWT_SECRET. Ở APP_ENV=prod từ chối giá trị mẫu hoặc quá ngắn (dưới 32 ký tự)."""
    secret = os.environ.get("JWT_SECRET", "")
    if not secret:
        raise RuntimeError("Chưa đặt JWT_SECRET trong .env")
    if os.environ.get("APP_ENV") == "prod" and (secret == _PLACEHOLDER_SECRET or len(secret) < MIN_SECRET_LENGTH):
        raise RuntimeError(f"JWT_SECRET quá yếu cho môi trường prod: cần chuỗi riêng dài ít nhất {MIN_SECRET_LENGTH} ký tự")
    return secret


def access_ttl_seconds() -> int:
    return int(os.environ.get("ACCESS_TOKEN_TTL_MIN", "30")) * 60


def refresh_ttl_seconds() -> int:
    return int(os.environ.get("REFRESH_TOKEN_TTL_DAYS", "7")) * 86400


def _encode(user_id: int, role: str, email: str, token_type: str, ttl_seconds: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),  # chuẩn JWT yêu cầu `sub` là chuỗi
        "role": role,
        "email": email,
        "type": token_type,
        "jti": uuid.uuid4().hex,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ttl_seconds)).timestamp()),
    }
    return jwt.encode(payload, get_secret(), algorithm=ALGORITHM)


def create_access_token(user_id: int, role: str, email: str) -> str:
    return _encode(user_id, role, email, ACCESS, access_ttl_seconds())


def create_refresh_token(user_id: int, role: str, email: str) -> str:
    return _encode(user_id, role, email, REFRESH, refresh_ttl_seconds())


def decode_token(token: str, expected_type: str) -> TokenClaims:
    """Giải mã và kiểm tra. Hết hạn -> TokenExpiredError; mọi lỗi khác -> InvalidTokenError."""
    try:
        payload = jwt.decode(
            token,
            get_secret(),
            algorithms=[ALGORITHM],  # chỉ nhận HS256, chặn kiểu tấn công đổi thuật toán (alg=none)
            options={"require": ["exp", "iat", "sub", "type"]},
        )
    except jwt.ExpiredSignatureError as exc:  # phải bắt trước PyJWTError vì nó là lớp con
        raise TokenExpiredError from exc
    except jwt.PyJWTError as exc:
        raise InvalidTokenError from exc

    if payload.get("type") != expected_type:
        raise InvalidTokenError(f"cần token loại {expected_type}")
    role = payload.get("role")
    if role not in VALID_ROLES:
        raise InvalidTokenError("vai trò không hợp lệ")
    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError) as exc:
        raise InvalidTokenError("sub không hợp lệ") from exc
    return TokenClaims(
        user_id=user_id,
        role=role,
        email=str(payload.get("email", "")),
        token_type=expected_type,
        jti=str(payload.get("jti", "")),
    )
