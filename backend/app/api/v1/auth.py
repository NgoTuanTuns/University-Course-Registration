"""Router /auth — TUẦN 1: trả dữ liệu MẪU để M1 làm mock.

TUẦN 2 (M4) thay thân hàm bằng bản thật: kiểm tra mật khẩu (bcrypt), phát JWT, rate-limit.
Chữ ký, đường dẫn và JSON trả về KHÔNG ĐỔI. main.py (M5) gắn router này dưới tiền tố /api/v1.
"""
from fastapi import APIRouter

from app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])

_SAMPLE_USER = UserOut(
    id=1,
    email="sv0001@uni.edu.vn",
    full_name="Nguyễn Văn A",
    role="student",
    mssv="SV0001",
    max_credits=25,
)


def _sample_tokens() -> TokenResponse:
    return TokenResponse(
        access_token="stub-access-token",
        refresh_token="stub-refresh-token",
        token_type="bearer",
        expires_in=1800,
        user=_SAMPLE_USER,
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest) -> TokenResponse:
    # TODO(M4, Tuần 2): tra DB theo email, verify_password, phát access+refresh token
    return _sample_tokens()


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest) -> TokenResponse:
    # TODO(M4, Tuần 3): kiểm tra refresh token và cấp access token mới
    return _sample_tokens()

