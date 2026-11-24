"""Router hồ sơ học tập sinh viên (/students/me/academic-record)."""

from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_session
from app.core.errors import api_error
from app.core.security import CurrentUser, get_current_user
from app.core.tuition import calculate_tuition_estimate
from app.models import (
    CompletedCourse,
    Course,
    CourseOffering,
    Enrollment,
    Student,
    StudyPlan,
    TermCourseOpening,
)
from app.services.phase_service import get_registration_phase

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


class TuitionItemOut(BaseModel):
    enrollment_id: int
    course_code: str
    course_name: str
    section: str
    credits: int
    category: str
    unit_price: int
    lab_fee: int
    subtotal: int


class TuitionEstimateResponse(BaseModel):
    term: str
    currency: str
    status: str
    payment_deadline: str
    total_courses: int
    total_credits: int
    tuition_subtotal: int
    lab_fee_total: int
    total_amount: int
    items: list[TuitionItemOut]


@router.get("/me/tuition", response_model=TuitionEstimateResponse)
async def get_my_tuition_estimate(
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[CurrentUser, Depends(get_current_user)],
    term: Annotated[str | None, Query(pattern=r"^\d{4}-[1-3]$")] = None,
) -> dict:
    """Tính bảng kê học phí tạm tính theo tín chỉ cho các lớp học phần đang ACTIVE."""
    target_term = term or get_settings().study_plan_term
    rows = (
        await session.execute(
            select(
                Enrollment.id,
                Course.code,
                Course.name,
                CourseOffering.section,
                Course.credits,
            )
            .join(CourseOffering, CourseOffering.id == Enrollment.offering_id)
            .join(Course, Course.id == CourseOffering.course_id)
            .where(
                Enrollment.student_id == user.id,
                Enrollment.status == "ACTIVE",
                CourseOffering.term == target_term,
            )
            .order_by(Course.code, CourseOffering.section)
        )
    ).all()

    enrolled_rows = [
        {
            "enrollment_id": int(enr_id),
            "course_code": str(code),
            "course_name": str(name),
            "section": str(section),
            "credits": int(credits),
        }
        for enr_id, code, name, section, credits in rows
    ]
    return calculate_tuition_estimate(target_term, enrolled_rows)


class StudentNotificationOut(BaseModel):
    id: str
    kind: Literal[
        "WAITLIST_PROMOTED",
        "COURSE_NOT_OPENED",
        "NEW_SECTIONS_OPENED",
        "PHASE_UPDATE",
    ]
    title: str
    message: str
    link: str | None = None
    created_at: datetime | None = None


class StudentNotificationListResponse(BaseModel):
    items: list[StudentNotificationOut]


@router.get("/me/notifications", response_model=StudentNotificationListResponse)
async def get_my_notifications(
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[CurrentUser, Depends(get_current_user)],
    term: Annotated[str | None, Query(pattern=r"^\d{4}-[1-3]$")] = None,
) -> dict:
    """Tổng hợp thông báo học vụ cá nhân hóa cho sinh viên (hủy mở lớp, mở thêm lớp, pha đợt ĐK)."""
    target_term = term or get_settings().study_plan_term
    items: list[dict] = []

    # 1. Các môn trong KHHT không đủ sĩ số nên hủy mở lớp
    not_opened_rows = (
        await session.execute(
            select(
                Course.code,
                Course.name,
                TermCourseOpening.planned_count,
                TermCourseOpening.min_required,
                TermCourseOpening.decided_at,
            )
            .join(StudyPlan, StudyPlan.course_id == Course.id)
            .join(
                TermCourseOpening,
                (TermCourseOpening.course_id == Course.id)
                & (TermCourseOpening.term == target_term),
            )
            .where(
                StudyPlan.student_id == user.id,
                StudyPlan.term == target_term,
                TermCourseOpening.status == "NOT_OPENED",
            )
            .order_by(Course.code)
        )
    ).all()
    not_opened_codes: set[str] = set()
    for code, name, planned, min_req, decided_at in not_opened_rows:
        not_opened_codes.add(str(code))
        items.append(
            {
                "id": f"not-opened-{target_term}-{code}",
                "kind": "COURSE_NOT_OPENED",
                "title": f"Môn {code} không mở lớp kỳ {target_term}",
                "message": (
                    f"{code} — {name} chỉ có {planned}/{min_req} sinh viên ĐKKHHT "
                    "nên Phòng Đào tạo tạm hủy mở lớp học kỳ này."
                ),
                "link": "/study-plan",
                "created_at": decided_at,
            }
        )

    # 2. Các môn trong KHHT đã mở nhiều lớp (>= 2 lớp) mà sinh viên chưa đăng ký
    enrolled_cids = set(
        (
            await session.scalars(
                select(CourseOffering.course_id)
                .join(Enrollment, Enrollment.offering_id == CourseOffering.id)
                .where(
                    Enrollment.student_id == user.id,
                    Enrollment.status == "ACTIVE",
                    CourseOffering.term == target_term,
                )
            )
        ).all()
    )
    opened_multi_rows = (
        await session.execute(
            select(
                Course.id,
                Course.code,
                Course.name,
                func.count(CourseOffering.id).label("sec_count"),
            )
            .join(StudyPlan, StudyPlan.course_id == Course.id)
            .join(
                CourseOffering,
                (CourseOffering.course_id == Course.id)
                & (CourseOffering.term == target_term),
            )
            .where(
                StudyPlan.student_id == user.id,
                StudyPlan.term == target_term,
            )
            .group_by(Course.id, Course.code, Course.name)
            .having(func.count(CourseOffering.id) >= 2)
            .order_by(func.count(CourseOffering.id).desc(), Course.code)
            .limit(4)
        )
    ).all()
    for cid, code, name, sec_count in opened_multi_rows:
        if cid in enrolled_cids or str(code) in not_opened_codes:
            continue
        items.append(
            {
                "id": f"multi-open-{target_term}-{code}-{sec_count}",
                "kind": "NEW_SECTIONS_OPENED",
                "title": f"{code} đã mở {sec_count} lớp học phần",
                "message": (
                    f"Học phần {code} — {name} trong KHHT của bạn đã được mở {sec_count} lớp. "
                    "Hãy chọn ca học phù hợp trước khi đầy chỗ."
                ),
                "link": f"/courses?q={code}",
                "created_at": None,
            }
        )

    # 3. Thông báo trạng thái giai đoạn đợt đăng ký hiện tại
    phase_info = await get_registration_phase(session, term=target_term)
    items.append(
        {
            "id": f"phase-{target_term}-{phase_info['phase']}",
            "kind": "PHASE_UPDATE",
            "title": f"Trạng thái đợt đăng ký: {phase_info['phase_label']}",
            "message": phase_info["note"] or phase_info["phase_description"],
            "link": "/courses" if phase_info["can_enroll"] else "/study-plan",
            "created_at": phase_info["updated_at"],
        }
    )

    return {"items": items}
