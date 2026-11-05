"""Tiện ích tạo header xác thực cho kiểm thử (M4, dùng cho M1, M2, M3, M5)."""

import os

from app.core import tokens

if not os.environ.get("JWT_SECRET"):
    os.environ["JWT_SECRET"] = "doi_thanh_chuoi_bat_ky_dai_mot_chut"


def auth_headers(
    user_id: int = 1, role: str = "student", email: str | None = None
) -> dict[str, str]:
    """Tạo header Authorization: Bearer <token> cho request kiểm thử."""
    if email is None:
        email = f"user{user_id}@uni.edu.vn" if role == "student" else "admin@uni.edu.vn"
    token = tokens.create_access_token(user_id, role, email)
    return {"Authorization": f"Bearer {token}"}
