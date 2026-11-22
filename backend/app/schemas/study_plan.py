"""Pydantic schemas cho quy trình Đăng ký Kế hoạch Học tập (ĐKKHHT) & Mở lớp."""

from typing import Literal

from pydantic import BaseModel, Field


class StudyPlanCreateRequest(BaseModel):
    course_id: int = Field(gt=0)
    term: str | None = Field(default=None, pattern=r"^\d{4}-[1-3]$")


class StudyPlanItemOut(BaseModel):
    id: int
    course_id: int
    code: str
    name: str
    credits: int
    min_accumulated_credits: int = 0
    term: str
    planned_count: int
    min_required: int
    opening_status: Literal["PENDING", "OPENED", "NOT_OPENED"]
    offerings_count: int
    enrollment_status: Literal["ENROLLED", "WAITLISTED", "NOT_ENROLLED"]


class StudyPlanResponse(BaseModel):
    term: str
    is_editable: bool
    phase_message: str
    total_planned_credits: int
    max_credits: int
    opened_count: int
    not_opened_count: int
    items: list[StudyPlanItemOut]


class AdminStudyPlanCourseSummary(BaseModel):
    course_id: int
    code: str
    name: str
    credits: int
    faculty: str | None = None
    planned_count: int
    min_required: int
    status: Literal["PENDING", "OPENED", "NOT_OPENED"]
    offerings_count: int
    recommended_sections: int


class AdminStudyPlanSummaryResponse(BaseModel):
    term: str
    is_editable: bool
    min_required: int
    total_plans: int
    opened_courses: int
    not_opened_courses: int
    pending_courses: int
    total_offerings: int
    items: list[AdminStudyPlanCourseSummary]


class AdminFinalizeStudyPlansRequest(BaseModel):
    term: str | None = Field(default=None, pattern=r"^\d{4}-[1-3]$")
    min_students_to_open: int = Field(default=15, ge=1, le=200)


class AdminFinalizeStudyPlansResponse(BaseModel):
    term: str
    min_students_to_open: int
    opened_courses: int
    not_opened_courses: int
    created_offerings: int
