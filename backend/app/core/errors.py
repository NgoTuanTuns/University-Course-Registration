"""Chuẩn hóa lỗi API trả về theo quy ước chung của nhóm (QUY_UOC_DU_AN.md, Mục 5).

Định dạng trả về thống nhất:
{
    "detail": {
        "code": "MÃ_LỖI",
        "message": "Mô tả lỗi dễ hiểu",
        ...
    }
}
"""
from typing import Any
from fastapi import HTTPException


def api_error(status_code: int, code: str, message: str, headers: dict[str, str] | None = None, **extra: Any) -> HTTPException:
    """Tạo HTTPException với cấu trúc detail chuẩn {code, message, ...}."""
    detail: dict[str, Any] = {"code": code, "message": message}
    if extra:
        detail.update(extra)
    return HTTPException(status_code=status_code, detail=detail, headers=headers)
