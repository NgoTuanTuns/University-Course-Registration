from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

RegistrationPhaseLiteral = Literal[
    "STUDY_PLAN_OPEN",
    "CLASS_OPENING_REVIEW",
    "ENROLLMENT_OPEN",
    "LOCKED",
]


class RegistrationPhaseOut(BaseModel):
    term: str
    phase: RegistrationPhaseLiteral
    phase_label: str
    phase_description: str
    phase_ends_at: datetime | None = None
    note: str | None = None
    can_edit_study_plan: bool
    can_enroll: bool
    updated_at: datetime | None = None


class RegistrationPhaseUpdateRequest(BaseModel):
    term: str = Field(default="2026-2", pattern=r"^\d{4}-[1-3]$")
    phase: RegistrationPhaseLiteral
    phase_ends_at: datetime | None = None
    note: str | None = Field(default=None, max_length=300)
