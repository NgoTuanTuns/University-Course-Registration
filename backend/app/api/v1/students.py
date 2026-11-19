"""Router hồ sơ học tập sinh viên (/students/me/academic-record)."""

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import api_error
from app.core.security import CurrentUser, get_current_user
from app.models import CompletedCourse, Course, Student

router = APIRouter(prefix="/students", tags=["students"])


class CompletedCourseOut(BaseModel):
    course_id: int
    code: str
    name: str
    credits: int
    grade: float | None
    term: str | None


class AcademicRecordResponse(BaseModel):
    student_id: int
    mssv: str | None
    full_name: str
    program: str | None
    faculty: str | None = None
    accumulated_credits: int
    max_credits: int
    gpa: float
    completed_count: int
    completed_courses: list[CompletedCourseOut]


@router.get("/me/academic-record", response_model=AcademicRecordResponse)
async def get_my_academic_record(
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> AcademicRecordResponse:
    """Trả về tổng tín chỉ tích lũy, GPA và danh sách các môn sinh viên đã hoàn thành."""
    student = await session.get(Student, user.id)
    if student is None:
        raise api_error(404, "NOT_FOUND", "Không tìm thấy sinh viên.")

    rows = (
        await session.execute(
            select(CompletedCourse, Course)
            .join(Course, Course.id == CompletedCourse.course_id)
            .where(CompletedCourse.student_id == user.id)
            .order_by(CompletedCourse.term, Course.code)
        )
    ).all()

    completed_list: list[CompletedCourseOut] = []
    weighted_sum = 0.0
    graded_credits = 0
    for cc, c in rows:
        grade_val = float(cc.grade) if cc.grade is not None else None
        if grade_val is not None:
            weighted_sum += grade_val * c.credits
            graded_credits += c.credits
        completed_list.append(
            CompletedCourseOut(
                course_id=c.id,
                code=c.code,
                name=c.name,
                credits=c.credits,
                grade=grade_val,
                term=cc.term,
            )
        )

    gpa = round(weighted_sum / graded_credits, 2) if graded_credits > 0 else 0.0
    return AcademicRecordResponse(
        student_id=student.id,
        mssv=student.mssv,
        full_name=student.full_name,
        program=student.program,
        faculty=getattr(student, "faculty", None),
        accumulated_credits=int(getattr(student, "accumulated_credits", 0) or 0),
        max_credits=student.max_credits,
        gpa=gpa,
        completed_count=len(completed_list),
        completed_courses=completed_list,
    )
