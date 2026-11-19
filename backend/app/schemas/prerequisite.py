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


# ---------------------------------------------------------------------------
# Schemas dành cho API Quản trị Tiên quyết (M4, Tuần 4 - /admin/prereqs)
# ---------------------------------------------------------------------------


class PrereqItemOut(BaseModel):
    prereq_course_id: int
    prereq_code: str
    prereq_name: str
    credits: int
    type: Literal["AND", "OR"]
    group_no: int


class OrGroupPrereqOut(BaseModel):
    group_no: int
    options: list[PrereqItemOut]


class CoursePrereqsResponse(BaseModel):
    course_id: int
    course_code: str
    course_name: str
    and_prerequisites: list[PrereqItemOut]
    or_groups: list[OrGroupPrereqOut]
    items: list[PrereqItemOut]


class PrereqEdgeOut(BaseModel):
    course_id: int
    course_code: str
    course_name: str
    prereq_course_id: int
    prereq_code: str
    prereq_name: str
    type: Literal["AND", "OR"]
    group_no: int


class PrereqCreate(BaseModel):
    course_id: int = Field(gt=0, description="ID học phần cần điều kiện tiên quyết")
    prereq_course_id: int = Field(gt=0, description="ID học phần tiên quyết")
    type: Literal["AND", "OR"] = Field(
        default="AND", description="Loại điều kiện: AND hoặc OR"
    )
    group_no: int = Field(
        default=0,
        ge=0,
        description="Số thứ tự nhóm (0 cho AND, >= 1 cho nhóm OR)",
    )


class PrereqUpdate(BaseModel):
    type: Literal["AND", "OR"] = Field(description="Loại điều kiện: AND hoặc OR")
    group_no: int = Field(
        default=0,
        ge=0,
        description="Số thứ tự nhóm (0 cho AND, >= 1 cho nhóm OR)",
    )


class PrereqListResponse(BaseModel):
    items: list[PrereqEdgeOut]
    total: int


# ===========================================================================
# Graph Visualizer API (/prerequisites/graph)
# ===========================================================================


class PrereqGraphNodeOut(BaseModel):
    id: int
    code: str
    name: str
    credits: int
    min_accumulated_credits: int
    level: int
    status: Literal["COMPLETED", "ELIGIBLE", "LOCKED"]
    missing_credits: int = 0
    missing_courses: list[str] = Field(default_factory=list)
    and_prereqs: list[str] = Field(default_factory=list)
    or_groups: list[OrGroupOut] = Field(default_factory=list)


class PrereqGraphEdgeOut(BaseModel):
    course_id: int
    prereq_course_id: int
    type: Literal["AND", "OR"]
    group_no: int


class PrereqGraphResponse(BaseModel):
    student_accumulated_credits: int
    nodes: list[PrereqGraphNodeOut]
    edges: list[PrereqGraphEdgeOut]
