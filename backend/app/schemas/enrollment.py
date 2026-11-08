"""Public contracts owned by M3."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class EnrollRequest(BaseModel):
    offering_id: int = Field(gt=0)


class EnrollmentResult(BaseModel):
    id: int
    offering_id: int
    status: Literal["ACTIVE", "WAITLISTED", "CANCELLED"]
    version: int | None = None
    position: int | None = None


class OfferingItem(BaseModel):
    id: int
    course_id: int
    code: str
    name: str
    credits: int
    term: str
    section: str
    instructor: str | None
    room: str | None
    schedule: list[dict]
    capacity: int
    enrolled_count: int
    my_status: Literal["ENROLLED", "WAITLISTED"] | None = None


class CoursePage(BaseModel):
    items: list[OfferingItem]
    total: int
    page: int
    page_size: int


class TimetableItem(OfferingItem):
    enrollment_id: int
    version: int


class Timetable(BaseModel):
    term: str | None
    items: list[TimetableItem]
    total_credits: int
    max_credits: int


class WaitlistItem(OfferingItem):
    waitlist_id: int
    position: int
    enqueued_at: datetime
    blocked_reason: str | None


class WaitlistPage(BaseModel):
    items: list[WaitlistItem]
    total: int
    page: int
    page_size: int
