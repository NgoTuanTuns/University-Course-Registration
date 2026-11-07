"""Dữ liệu vào/ra của API tiên quyết (M2). Chỉ dùng mã + tên môn, không lộ id nội bộ."""

from typing import Literal

from pydantic import BaseModel, Field


class OrGroupOut(BaseModel):
    group_no: int
    options: list[str]  # mã môn


class PrerequisiteCheckResponse(BaseModel):
    course_id: int
    course_code: str
    eligible: bool
    missing_courses: list[str]  # mã môn, ví dụ "INT131"
    unmet_or_groups: list[OrGroupOut]


class PrerequisiteExplainRequest(BaseModel):
    course_id: int = Field(gt=0, description="Môn cần giải thích")
    student_id: int | None = Field(
        default=None, gt=0, description="Chỉ admin được hỏi cho sinh viên khác"
    )


class MissingCourseOut(BaseModel):
    course_code: str
    course_name: str
    kind: Literal["DIRECT", "TRANSITIVE"] = Field(
        description="DIRECT: môn đang xét đòi trực tiếp; TRANSITIVE: đòi gián tiếp"
    )
    required_by: str = Field(description="Mã môn trực tiếp đòi hỏi môn này")
    path: list[str] = Field(
        description="Chuỗi mã môn từ môn đang xét tới môn còn thiếu (đường ngắn nhất)"
    )


class OrOptionOut(BaseModel):
    course_code: str
    course_name: str
    can_take_now: bool = Field(description="Đã đủ điều kiện học lựa chọn này ngay")
    missing_courses: list[str] = Field(
        description="Mã các môn còn thiếu để học được lựa chọn này"
    )


class OrGroupExplainOut(BaseModel):
    group_no: int
    required_by: str = Field(description="Mã môn có nhóm 'hoặc' này")
    options: list[OrOptionOut]


class PrerequisiteExplainResponse(BaseModel):
    course_id: int
    course_code: str
    course_name: str
    eligible: bool
    missing: list[MissingCourseOut]
    unmet_or_groups: list[OrGroupExplainOut]
    suggested_order: list[str] = Field(
        description="Thứ tự học gợi ý cho các môn bắt buộc còn thiếu"
    )
    total_missing: int = Field(description="Tổng số môn bắt buộc còn thiếu")
    truncated: bool = Field(
        description="True nếu danh sách bị cắt bớt theo PREREQ_EXPLAIN_MAX_ITEMS"
    )
