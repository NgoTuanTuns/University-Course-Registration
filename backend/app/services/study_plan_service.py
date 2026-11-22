"""Nghiệp vụ Đăng ký Kế hoạch Học tập (ĐKKHHT) và chốt mở lớp theo nhu cầu."""

from __future__ import annotations

import math
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import api_error
from app.core.faculty import PREFIX_TO_FACULTY, course_allowed_for_faculty
from app.models import (
    CompletedCourse,
    Course,
    CourseOffering,
    Enrollment,
    Student,
    StudyPlan,
    TermCourseOpening,
    Waitlist,
)
from app.services.prerequisite_engine import check_eligibility

_DEFAULT_SLOTS = [
    [{"day": 1, "start": "06:50", "end": "09:20"}],  # Ca 1
    [{"day": 2, "start": "09:30", "end": "12:00"}],  # Ca 2
    [{"day": 3, "start": "12:45", "end": "15:15"}],  # Ca 3
    [{"day": 4, "start": "15:25", "end": "17:55"}],  # Ca 4
    [{"day": 5, "start": "06:50", "end": "09:20"}],  # Ca 1
    [{"day": 6, "start": "09:30", "end": "12:00"}],  # Ca 2
]


def _faculty_label(code: str) -> str:
    prefix = "".join(ch for ch in code if ch.isalpha())[:3].upper()
    return PREFIX_TO_FACULTY.get(prefix, "Đại cương / Chung")


def _ensure_study_plan_open() -> None:
    settings = get_settings()
    if not settings.study_plan_editable:
        raise api_error(
            403,
            "STUDY_PLAN_PERIOD_CLOSED",
            f"Đợt Đăng ký Kế hoạch học tập học kỳ {settings.study_plan_term} đã kết thúc. "
            "Sinh viên không thể thêm hoặc xóa học phần trong KHHT.",
        )


async def get_student_study_plan(
    session: AsyncSession, student_id: int, term: str | None = None
) -> dict:
    settings = get_settings()
    target_term = term or settings.study_plan_term
    student = await session.get(Student, student_id)
    if student is None:
        raise api_error(404, "NOT_FOUND", "Không tìm thấy sinh viên")

    plan_rows = (
        await session.execute(
            select(StudyPlan, Course)
            .join(Course, Course.id == StudyPlan.course_id)
            .where(StudyPlan.student_id == student_id, StudyPlan.term == target_term)
            .order_by(Course.code)
        )
    ).all()

    course_ids = [c.id for _, c in plan_rows]
    openings_by_cid: dict[int, TermCourseOpening] = {}
    offerings_count_by_cid: dict[int, int] = {}
    enrolled_cids: set[int] = set()
    waitlisted_cids: set[int] = set()

    if course_ids:
        opening_rows = (
            await session.scalars(
                select(TermCourseOpening).where(
                    TermCourseOpening.term == target_term,
                    TermCourseOpening.course_id.in_(course_ids),
                )
            )
        ).all()
        openings_by_cid = {op.course_id: op for op in opening_rows}

        off_counts = (
            await session.execute(
                select(CourseOffering.course_id, func.count(CourseOffering.id))
                .where(
                    CourseOffering.term == target_term,
                    CourseOffering.course_id.in_(course_ids),
                )
                .group_by(CourseOffering.course_id)
            )
        ).all()
        offerings_count_by_cid = {cid: int(cnt) for cid, cnt in off_counts}

        enrolled_cids = set(
            (
                await session.scalars(
                    select(CourseOffering.course_id)
                    .join(Enrollment, Enrollment.offering_id == CourseOffering.id)
                    .where(
                        Enrollment.student_id == student_id,
                        Enrollment.status == "ACTIVE",
                        CourseOffering.term == target_term,
                        CourseOffering.course_id.in_(course_ids),
                    )
                )
            ).all()
        )
        waitlisted_cids = set(
            (
                await session.scalars(
                    select(CourseOffering.course_id)
                    .join(Waitlist, Waitlist.offering_id == CourseOffering.id)
                    .where(
                        Waitlist.student_id == student_id,
                        CourseOffering.term == target_term,
                        CourseOffering.course_id.in_(course_ids),
                    )
                )
            ).all()
        )

    items = []
    opened_count = 0
    not_opened_count = 0
    for sp, course in plan_rows:
        op = openings_by_cid.get(course.id)
        status = op.status if op else "PENDING"
        if status == "OPENED":
            opened_count += 1
        elif status == "NOT_OPENED":
            not_opened_count += 1
        if course.id in enrolled_cids:
            enr_status = "ENROLLED"
        elif course.id in waitlisted_cids:
            enr_status = "WAITLISTED"
        else:
            enr_status = "NOT_ENROLLED"
        items.append(
            {
                "id": sp.id,
                "course_id": course.id,
                "code": course.code,
                "name": course.name,
                "credits": course.credits,
                "min_accumulated_credits": course.min_accumulated_credits,
                "term": sp.term,
                "planned_count": op.planned_count if op else 1,
                "min_required": op.min_required
                if op
                else settings.min_plan_students_to_open,
                "opening_status": status,
                "offerings_count": offerings_count_by_cid.get(course.id, 0),
                "enrollment_status": enr_status,
            }
        )

    # Sắp xếp môn đã mở lớp lên trước, môn bị hủy mở lớp xuống dưới
    order = {"OPENED": 0, "PENDING": 1, "NOT_OPENED": 2}
    items.sort(key=lambda x: (order[x["opening_status"]], x["code"]))

    phase_message = (
        f"Cổng Đăng ký Kế hoạch học tập học kỳ {target_term} đang mở."
        if settings.study_plan_editable
        else f"Đợt Đăng ký Kế hoạch học tập học kỳ {target_term} đã kết thúc. "
        "Danh sách được khóa ở chế độ chỉ xem; vui lòng đăng ký lớp cho các môn đã mở lớp."
    )

    return {
        "term": target_term,
        "is_editable": settings.study_plan_editable,
        "phase_message": phase_message,
        "total_planned_credits": sum(i["credits"] for i in items),
        "max_credits": student.max_credits,
        "opened_count": opened_count,
        "not_opened_count": not_opened_count,
        "items": items,
    }


async def add_course_to_study_plan(
    session: AsyncSession,
    student_id: int,
    course_id: int,
    term: str | None = None,
) -> dict:
    _ensure_study_plan_open()
    settings = get_settings()
    target_term = term or settings.study_plan_term

    student = await session.get(Student, student_id)
    if student is None:
        raise api_error(404, "NOT_FOUND", "Không tìm thấy sinh viên")
    course = await session.get(Course, course_id)
    if course is None:
        raise api_error(404, "COURSE_NOT_FOUND", "Không tìm thấy học phần")

    if student.role == "student" and not course_allowed_for_faculty(
        course.code, student.faculty
    ):
        raise api_error(
            422,
            "FACULTY_MISMATCH",
            f"Học phần {course.code} không thuộc chương trình đào tạo của {student.faculty}.",
        )

    completed = await session.get(CompletedCourse, (student_id, course_id))
    if completed is not None:
        raise api_error(
            409, "ALREADY_COMPLETED", f"Bạn đã hoàn thành học phần {course.code}."
        )

    existing = await session.scalar(
        select(StudyPlan).where(
            StudyPlan.student_id == student_id,
            StudyPlan.course_id == course_id,
            StudyPlan.term == target_term,
        )
    )
    if existing is not None:
        raise api_error(
            409,
            "ALREADY_IN_STUDY_PLAN",
            f"Học phần {course.code} đã có trong Kế hoạch học tập kỳ {target_term}.",
        )

    if student.accumulated_credits < course.min_accumulated_credits:
        raise api_error(
            422,
            "MIN_ACCUMULATED_CREDITS_NOT_MET",
            f"Môn {course.code} yêu cầu tối thiểu {course.min_accumulated_credits} tín chỉ tích lũy.",
        )

    prereq = await check_eligibility(session, student_id, course_id)
    if not prereq.eligible:
        raise api_error(
            422,
            "PREREQ_NOT_MET",
            f"Bạn chưa đáp ứng điều kiện tiên quyết cho học phần {course.code}.",
        )

    current_credits = (
        await session.scalar(
            select(func.coalesce(func.sum(Course.credits), 0))
            .join(StudyPlan, StudyPlan.course_id == Course.id)
            .where(StudyPlan.student_id == student_id, StudyPlan.term == target_term)
        )
        or 0
    )
    if int(current_credits) + course.credits > student.max_credits:
        raise api_error(
            422,
            "MAX_CREDITS_EXCEEDED",
            f"Tổng tín chỉ KHHT vượt quá hạn mức {student.max_credits} tín chỉ.",
        )

    sp = StudyPlan(student_id=student_id, course_id=course_id, term=target_term)
    session.add(sp)
    await session.flush()

    opening = await session.get(TermCourseOpening, (target_term, course_id))
    if opening is None:
        opening = TermCourseOpening(
            term=target_term,
            course_id=course_id,
            planned_count=1,
            min_required=settings.min_plan_students_to_open,
            status="PENDING",
        )
        session.add(opening)
    else:
        opening.planned_count += 1
    await session.commit()
    return await get_student_study_plan(session, student_id, target_term)


async def remove_course_from_study_plan(
    session: AsyncSession, student_id: int, plan_id: int
) -> dict:
    _ensure_study_plan_open()
    sp = await session.get(StudyPlan, plan_id)
    if sp is None or sp.student_id != student_id:
        raise api_error(404, "NOT_FOUND", "Không tìm thấy mục Kế hoạch học tập")

    target_term = sp.term
    opening = await session.get(TermCourseOpening, (sp.term, sp.course_id))
    if opening is not None and opening.planned_count > 0:
        opening.planned_count -= 1

    await session.delete(sp)
    await session.commit()
    return await get_student_study_plan(session, student_id, target_term)


async def get_admin_study_plan_summary(
    session: AsyncSession,
    term: str | None = None,
    status_filter: str | None = None,
) -> dict:
    settings = get_settings()
    target_term = term or settings.study_plan_term

    courses = (await session.scalars(select(Course).order_by(Course.code))).all()
    opening_rows = (
        await session.scalars(
            select(TermCourseOpening).where(TermCourseOpening.term == target_term)
        )
    ).all()
    openings_by_cid = {op.course_id: op for op in opening_rows}

    live_counts_rows = (
        await session.execute(
            select(StudyPlan.course_id, func.count(StudyPlan.id))
            .where(StudyPlan.term == target_term)
            .group_by(StudyPlan.course_id)
        )
    ).all()
    live_counts = {cid: int(cnt) for cid, cnt in live_counts_rows}

    off_counts_rows = (
        await session.execute(
            select(CourseOffering.course_id, func.count(CourseOffering.id))
            .where(CourseOffering.term == target_term)
            .group_by(CourseOffering.course_id)
        )
    ).all()
    off_counts = {cid: int(cnt) for cid, cnt in off_counts_rows}

    items = []
    opened_courses = 0
    not_opened_courses = 0
    pending_courses = 0
    total_plans = 0
    total_offerings = 0

    for c in courses:
        op = openings_by_cid.get(c.id)
        planned = live_counts.get(c.id, op.planned_count if op else 0)
        min_req = op.min_required if op else settings.min_plan_students_to_open
        status = op.status if op else "PENDING"
        o_count = off_counts.get(c.id, 0)

        total_plans += planned
        total_offerings += o_count
        if status == "OPENED":
            opened_courses += 1
        elif status == "NOT_OPENED":
            not_opened_courses += 1
        else:
            pending_courses += 1

        if status_filter and status_filter != "ALL" and status != status_filter:
            continue

        rec_sections = (
            math.ceil(planned / settings.default_section_capacity)
            if planned >= min_req
            else 0
        )
        items.append(
            {
                "course_id": c.id,
                "code": c.code,
                "name": c.name,
                "credits": c.credits,
                "faculty": _faculty_label(c.code),
                "planned_count": planned,
                "min_required": min_req,
                "status": status,
                "offerings_count": o_count,
                "recommended_sections": rec_sections,
            }
        )

    items.sort(key=lambda x: (-x["planned_count"], x["code"]))

    return {
        "term": target_term,
        "is_editable": settings.study_plan_editable,
        "min_required": settings.min_plan_students_to_open,
        "total_plans": total_plans,
        "opened_courses": opened_courses,
        "not_opened_courses": not_opened_courses,
        "pending_courses": pending_courses,
        "total_offerings": total_offerings,
        "items": items,
    }


async def finalize_study_plan_openings(
    session: AsyncSession,
    term: str | None = None,
    min_students_to_open: int | None = None,
) -> dict:
    settings = get_settings()
    target_term = term or settings.study_plan_term
    threshold = min_students_to_open or settings.min_plan_students_to_open
    now = datetime.now(UTC)

    courses = (await session.scalars(select(Course).order_by(Course.id))).all()
    live_counts_rows = (
        await session.execute(
            select(StudyPlan.course_id, func.count(StudyPlan.id))
            .where(StudyPlan.term == target_term)
            .group_by(StudyPlan.course_id)
        )
    ).all()
    live_counts = {cid: int(cnt) for cid, cnt in live_counts_rows}

    existing_sec_rows = (
        await session.execute(
            select(CourseOffering.course_id, CourseOffering.section).where(
                CourseOffering.term == target_term
            )
        )
    ).all()
    existing_sections_by_cid: dict[int, set[str]] = {}
    for cid, sec in existing_sec_rows:
        existing_sections_by_cid.setdefault(cid, set()).add(sec)

    opened = 0
    not_opened = 0
    created_offerings = 0

    for idx, c in enumerate(courses):
        planned = live_counts.get(c.id, 0)
        status = "OPENED" if planned >= threshold else "NOT_OPENED"
        opening = await session.get(TermCourseOpening, (target_term, c.id))
        if opening is None:
            opening = TermCourseOpening(
                term=target_term,
                course_id=c.id,
                planned_count=planned,
                min_required=threshold,
                status=status,
                decided_at=now,
            )
            session.add(opening)
        else:
            opening.planned_count = planned
            opening.min_required = threshold
            opening.status = status
            opening.decided_at = now

        if status == "OPENED":
            opened += 1
            needed = max(1, math.ceil(planned / settings.default_section_capacity))
            used_secs = existing_sections_by_cid.setdefault(c.id, set())
            sec_num = 1
            while len(used_secs) < needed:
                sec_label = f"{sec_num:02d}"
                sec_num += 1
                if sec_label in used_secs:
                    continue
                used_secs.add(sec_label)
                session.add(
                    CourseOffering(
                        course_id=c.id,
                        term=target_term,
                        section=sec_label,
                        instructor="Giảng viên phân công",
                        capacity=settings.default_section_capacity,
                        enrolled_count=0,
                        schedule=_DEFAULT_SLOTS[(idx + sec_num) % len(_DEFAULT_SLOTS)],
                        room=f"B{(idx % 3) + 1}-{101 + ((idx + sec_num) % 12)}",
                    )
                )
                created_offerings += 1
        else:
            not_opened += 1

    await session.commit()
    return {
        "term": target_term,
        "min_students_to_open": threshold,
        "opened_courses": opened,
        "not_opened_courses": not_opened,
        "created_offerings": created_offerings,
    }
