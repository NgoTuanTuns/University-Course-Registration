"""Router /auth (M4, Tuần 3): Đăng nhập thật, làm mới token xoay vòng và đăng xuất.

Quy ước chung của nhóm:
- /auth/login: Rate-limit chống dò mật khẩu, kiểm tra mật khẩu (bcrypt), cấp JWT access/refresh.
- /auth/refresh: Xoay vòng refresh token (Single-use) + Phát hiện dùng lại (Token Reuse Detection qua Redis).
- /auth/logout: Thu hồi refresh token khỏi Redis.
- Dạng phản hồi: schemas/auth.py.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import tokens
from app.core.db import get_session
from app.core.errors import api_error
from app.core.rate_limit import check_rate_limit, get_client_ip
from app.core.redis import (
    consume_refresh_token,
    revoke_all_user_tokens,
    revoke_single_token,
    store_refresh_token,
)
from app.models import Student
from app.schemas.auth import (
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    TokenResponse,
    UserOut,
)
from app.services.auth_service import authenticate, get_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


async def _issue_token_response(user: Student) -> TokenResponse:
    """Cấp cặp token mới và lưu jti của refresh token vào Redis."""
    access_token = tokens.create_access_token(user.id, user.role, user.email)
    refresh_token = tokens.create_refresh_token(user.id, user.role, user.email)

    claims = tokens.decode_token(refresh_token, expected_type=tokens.REFRESH)
    await store_refresh_token(user.id, claims.jti, tokens.refresh_ttl_seconds())

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=tokens.access_ttl_seconds(),
        user=UserOut(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            mssv=user.mssv,
            max_credits=user.max_credits,
        ),
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    body: LoginRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TokenResponse:
    # Rate limit: chống dò mật khẩu theo (IP, email)
    client_ip = get_client_ip(request)
    limit_id = f"{client_ip}:{body.email.strip().lower()}"
    await check_rate_limit(
        scope="login", identifier=limit_id, limit=5, window_seconds=60
    )

    user = await authenticate(session, body.email, body.password)
    if user is None:
        raise api_error(401, "UNAUTHENTICATED", "Sai email hoặc mật khẩu")

    return await _issue_token_response(user)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TokenResponse:
    expired_err = api_error(
        401, "UNAUTHENTICATED", "Phiên đăng nhập đã hết hạn hoặc không hợp lệ"
    )

    try:
        claims = tokens.decode_token(body.refresh_token, expected_type=tokens.REFRESH)
    except (tokens.TokenExpiredError, tokens.InvalidTokenError):
        raise expired_err from None

    # Cơ chế xoay vòng & phát hiện dùng lại (Token Reuse Detection)
    valid_use = await consume_refresh_token(claims.user_id, claims.jti)
    if not valid_use:
        # Nếu token đã bị dùng hoặc không tồn tại: nghi ngờ bị đánh cắp -> thu hồi TOÀN BỘ phiên
        logger.warning(
            "CẢNH BÁO BẢO MẬT: Phát hiện tái sử dụng refresh token của user_id=%s, jti=%s. Tiến hành thu hồi toàn bộ phiên.",
            claims.user_id,
            claims.jti,
        )
        await revoke_all_user_tokens(claims.user_id)
        raise expired_err

    user = await get_user(session, claims.user_id)
    if user is None:
        raise expired_err

    # Cấp cặp token mới (xoay vòng)
    return await _issue_token_response(user)


@router.post("/logout", response_model=MessageResponse)
async def logout(body: RefreshRequest) -> MessageResponse:
    """Thu hồi refresh token khi đăng xuất."""
    try:
        claims = tokens.decode_token(body.refresh_token, expected_type=tokens.REFRESH)
        await revoke_single_token(claims.user_id, claims.jti)
    except Exception:
        # Không lộ lỗi kỹ thuật khi token không giải mã được
        pass
    return MessageResponse(message="Đăng xuất thành công")
