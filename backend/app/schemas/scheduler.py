"""Schemas cho tính năng Gợi ý xếp lịch tự động (Smart Auto-Scheduler)."""

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.enrollment import OfferingItem


class SchedulerPreferences(BaseModel):
    avoid_first_shift: bool = False
    avoid_night_shift: bool = True
    avoid_saturday: bool = False
    minimize_days: bool = True
    time_of_day: Literal["ANY", "MORNING", "AFTERNOON"] = "ANY"


class SchedulerSuggestRequest(BaseModel):
    course_ids: list[int] | None = Field(default=None, max_length=12)
    term: str | None = Field(default=None, pattern=r"^\d{4}-[1-3]$")
    preferences: SchedulerPreferences = Field(default_factory=SchedulerPreferences)
    max_results: int = Field(default=3, ge=1, le=5)


class SchedulerTargetCourse(BaseModel):
    course_id: int
    code: str
    name: str
    credits: int
    in_study_plan: bool
    selected: bool


class UnschedulableCourse(BaseModel):
    course_id: int
    code: str
    name: str
    credits: int
    reason: str
    detail: str


class SuggestedPlan(BaseModel):
    rank: int
    score: int
    total_credits: int
    added_credits: int
    study_days_count: int
    tags: list[str]
    offerings: list[OfferingItem]


class SchedulerSuggestResponse(BaseModel):
    term: str
    current_credits: int
    max_credits: int
    credit_limit_warning: str | None = None
    target_courses: list[SchedulerTargetCourse]
    plans: list[SuggestedPlan]
    unschedulable: list[UnschedulableCourse]
