from pydantic import BaseModel


class OrGroupOut(BaseModel):
    group_no: int
    options: list[str]  # mã môn


class PrerequisiteCheckResponse(BaseModel):
    course_id: int
    course_code: str
    eligible: bool
    missing_courses: list[str]  # mã môn, ví dụ "INT131"
    unmet_or_groups: list[OrGroupOut]
