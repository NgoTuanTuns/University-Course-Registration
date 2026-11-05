"""Schemas cho học phần và API quản trị học phần (M4, Tuần 3).

Quy ước chung: Tên trường JSON dạng snake_case, phân trang {items, total, page, page_size}.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class CourseCreate(BaseModel):
    code: str = Field(
        min_length=1, max_length=20, description="Mã học phần (duy nhất, ví dụ INT131)"
    )
    name: str = Field(min_length=1, max_length=200, description="Tên học phần")
    credits: int = Field(ge=1, le=10, description="Số tín chỉ (1 - 10)")
    description: str | None = Field(default=None, description="Mô tả học phần")


class CourseUpdate(BaseModel):
    name: str | None = Field(
        default=None, min_length=1, max_length=200, description="Tên học phần"
    )
    credits: int | None = Field(
        default=None, ge=1, le=10, description="Số tín chỉ (1 - 10)"
    )
    description: str | None = Field(default=None, description="Mô tả học phần")


class CourseOut(BaseModel):
    id: int
    code: str
    name: str
    credits: int
    description: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CourseListResponse(BaseModel):
    items: list[CourseOut]
    total: int
    page: int
    page_size: int
