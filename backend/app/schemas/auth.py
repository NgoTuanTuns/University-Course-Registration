"""Schema xác thực (bản nháp cho M1 làm mock; /auth không có mẫu trong quy ước)."""
from typing import Literal

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: Literal["student", "admin"]
    mssv: str | None
    max_credits: int


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int  # giây (ACCESS_TOKEN_TTL_MIN * 60)
    user: UserOut
