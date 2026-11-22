"""Read models shared by course search, timetable and enrollment rules."""

from collections import defaultdict

from sqlalchemy import case, cast, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import api_error
from app.core.faculty import allowed_prefixes_for_faculty
from app.models import (
    CompletedCourse,
    Course,
    CourseOffering,
    Enrollment,
    Prerequisite,
    Student,
    StudyPlan,
    TermCourseOpening,
    Waitlist,
)


def student_academic_year(accumulated_credits: int) -> int:
    """Suy ra năm học hiện tại (1..4) dựa trên số tín chỉ tích lũy."""
    if accumulated_credits < 20:
        return 1
    if accumulated_credits < 40:
        return 2
    if accumulated_credits < 60:
        return 3
    return 4


def course_target_year(code: str, min_accumulated_credits: int) -> int:
    """Suy ra năm học mục tiêu (1..4) của học phần từ mã môn và ngưỡng tín chỉ."""
    digits = "".join(ch for ch in code if ch.isdigit())
    if digits and digits[0] in ("1", "2", "3", "4"):
        return int(digits[0])
    if min_accumulated_credits >= 36:
        return 4
    if min_accumulated_credits >= 15:
        return 3
    if min_accumulated_credits >= 3:
        return 2
    return 1


def rank_courses_for_student(
    courses: list[tuple[int, str, int]],
    accumulated_credits: int,
    completed_ids: set[int],
    prereq_rows: list[tuple[int, int, str, int]],
    planned_ids: set[int] | None = None,
) -> tuple[dict[int, int], dict[int, str]]:
    """Tính thứ tự ưu tiên & trạng thái đủ điều kiện cho từng học phần của sinh viên.

    Thứ tự ưu tiên:
      0 (RECOMMENDED): Đủ tín chỉ + đủ tiên quyết + (nằm trong KHHT hoặc đúng tiến độ năm học).
      1 (ELIGIBLE):    Đủ tín chỉ + đủ tiên quyết (các năm khác / đại cương còn lại).
      2 (LOCKED):      Chưa đủ tín chỉ tích lũy hoặc thiếu môn tiên quyết.
      3 (COMPLETED):   Đã hoàn thành (đẩy xuống cuối danh sách).
    """
    planned = planned_ids or set()
    student_year = student_academic_year(accumulated_credits)
    and_map: dict[int, list[int]] = defaultdict(list)
    or_map: dict[int, dict[int, list[int]]] = defaultdict(lambda: defaultdict(list))
    for course_id, prereq_id, ptype, group_no in prereq_rows:
        if ptype == "AND" or group_no == 0:
            and_map[course_id].append(prereq_id)
        else:
            or_map[course_id][group_no].append(prereq_id)

    scored: list[tuple[tuple, int, str]] = []
    for cid, code, min_tc in courses:
        target_year = course_target_year(code, min_tc)
        in_plan = cid in planned
        if cid in completed_ids:
            status = "COMPLETED"
            key = (3, 1, 0, 0, code)
        else:
            and_ok = all(p in completed_ids for p in and_map.get(cid, ()))
            or_ok = all(
                any(p in completed_ids for p in opts)
                for opts in or_map.get(cid, {}).values()
            )
            tc_ok = accumulated_credits >= min_tc
            if and_ok and or_ok and tc_ok:
                if in_plan or target_year == student_year:
                    status = "RECOMMENDED"
                    key = (0, 0 if in_plan else 1, 0, -min_tc, code)
                else:
                    status = "ELIGIBLE"
                    key = (1, 1, abs(target_year - student_year), -min_tc, code)
            else:
                status = "LOCKED"
                key = (2, 1, abs(target_year - student_year), min_tc, code)
        scored.append((key, cid, status))

    scored.sort(key=lambda item: item[0])
    rank_map = {cid: idx for idx, (_, cid, _) in enumerate(scored)}
    status_map = {cid: status for _, cid, status in scored}
    return rank_map, status_map


def offering_dict(offering: CourseOffering, course: Course) -> dict:
    return {
        field: getattr(offering, field)
        for field in (
            "id",
            "course_id",
            "term",
            "section",
            "instructor",
            "room",
            "schedule",
            "capacity",
            "enrolled_count",
        )
    } | {
        field: getattr(course, field)
        for field in ("code", "name", "credits", "min_accumulated_credits")
    }


async def latest_term(session: AsyncSession, term: str | None) -> str | None:
    return term or await session.scalar(select(func.max(CourseOffering.term)))


async def active_items(session: AsyncSession, student_id: int, term: str) -> list[dict]:
    rows = await session.execute(
        select(CourseOffering, Course, Enrollment)
        .join(Course, Course.id == CourseOffering.course_id)
        .join(Enrollment, Enrollment.offering_id == CourseOffering.id)
        .where(
            Enrollment.student_id == student_id,
            Enrollment.status == "ACTIVE",
            CourseOffering.term == term,
        )
        .order_by(Course.code, CourseOffering.section, CourseOffering.id)
    )
    return [
        offering_dict(o, c)
        | {"enrollment_id": e.id, "version": e.version, "my_status": "ENROLLED"}
        for o, c, e in rows
    ]


async def timetable(session: AsyncSession, student_id: int, term: str | None) -> dict:
    student = await session.get(Student, student_id)
    if student is None:
        raise api_error(404, "NOT_FOUND", "Không tìm thấy sinh viên")
    term = await latest_term(session, term)
    items = await active_items(session, student_id, term) if term else []
    return {
        "term": term,
        "items": items,
        "total_credits": sum(i["credits"] for i in items),
        "max_credits": student.max_credits,
    }


def escaped(value: str) -> str:
    return (
        "%" + value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
    )


async def search_courses(session: AsyncSession, student_id: int, **filters) -> dict:
    term = await latest_term(session, filters.get("term"))
    conditions = [CourseOffering.term == term]
    student = await session.get(Student, student_id)
    faculty = (
        getattr(student, "faculty", None)
        if student and student.role == "student"
        else None
    )
    allowed_prefixes = allowed_prefixes_for_faculty(faculty)
    if allowed_prefixes:
        conditions.append(or_(*[Course.code.like(f"{p}%") for p in allowed_prefixes]))
    # Ẩn các học phần bị hủy mở lớp (NOT_OPENED) trong học kỳ đang tra cứu
    conditions.append(
        ~exists(
            select(1).where(
                TermCourseOpening.term == CourseOffering.term,
                TermCourseOpening.course_id == Course.id,
                TermCourseOpening.status == "NOT_OPENED",
            )
        )
    )
    for key, column in (
        ("section", CourseOffering.section),
        ("instructor", CourseOffering.instructor),
    ):
        if filters.get(key):
            conditions.append(column.ilike(escaped(filters[key]), escape="\\"))
    if filters.get("q"):
        pattern = escaped(filters["q"])
        conditions.append(
            or_(
                Course.code.ilike(pattern, escape="\\"),
                Course.name.ilike(pattern, escape="\\"),
            )
        )
    if filters.get("credits") is not None:
        conditions.append(Course.credits == filters["credits"])
    meetings = func.jsonb_array_elements(CourseOffering.schedule).table_valued("value")
    from sqlalchemy.dialects.postgresql import JSONB

    meeting = cast(meetings.c.value, JSONB)
    time_conditions = []
    for key, op, field in (
        ("day", "eq", "day"),
        ("from_time", "ge", "start"),
        ("to_time", "le", "end"),
    ):
        value = filters.get(key)
        if value is not None:
            expr = meeting[field].astext
            time_conditions.append(
                {
                    "eq": expr == str(value),
                    "ge": expr >= str(value),
                    "le": expr <= str(value),
                }[op]
            )
    if time_conditions:
        conditions.append(
            exists(select(1).select_from(meetings).where(*time_conditions))
        )
    base = select(CourseOffering, Course).join(Course).where(*conditions)
    total = await session.scalar(select(func.count()).select_from(base.subquery()))
    active = exists(
        select(1).where(
            Enrollment.student_id == student_id,
            Enrollment.offering_id == CourseOffering.id,
            Enrollment.status == "ACTIVE",
        )
    )
    waiting = exists(
        select(1).where(
            Waitlist.student_id == student_id, Waitlist.offering_id == CourseOffering.id
        )
    )
    page, size = filters["page"], filters["page_size"]

    status_map: dict[int, str] = {}
    planned_ids: set[int] = set()
    order_clauses: list = []
    if student is not None and student.role == "student":
        course_rows = (
            await session.execute(
                select(
                    Course.id, Course.code, Course.min_accumulated_credits
                ).distinct()
            )
        ).all()
        completed_ids = set(
            (
                await session.scalars(
                    select(CompletedCourse.course_id).where(
                        CompletedCourse.student_id == student_id
                    )
                )
            ).all()
        )
        planned_ids = set(
            (
                await session.scalars(
                    select(StudyPlan.course_id).where(
                        StudyPlan.student_id == student_id,
                        StudyPlan.term == term,
                    )
                )
            ).all()
        )
        prereq_rows = (
            await session.execute(
                select(
                    Prerequisite.course_id,
                    Prerequisite.prereq_course_id,
                    Prerequisite.type,
                    Prerequisite.group_no,
                )
            )
        ).all()
        rank_map, status_map = rank_courses_for_student(
            [(r[0], r[1], r[2]) for r in course_rows],
            student.accumulated_credits,
            completed_ids,
            [(r[0], r[1], r[2], r[3]) for r in prereq_rows],
            planned_ids=planned_ids,
        )
        if rank_map:
            order_clauses.append(case(rank_map, value=Course.id, else_=999999))

    order_clauses.extend([Course.code, CourseOffering.section, CourseOffering.id])

    rows = await session.execute(
        base.add_columns(
            case((active, "ENROLLED"), (waiting, "WAITLISTED"), else_=None)
        )
        .order_by(*order_clauses)
        .offset((page - 1) * size)
        .limit(size)
    )
    return {
        "items": [
            offering_dict(o, c)
            | {
                "my_status": s,
                "eligibility_status": status_map.get(c.id),
                "in_study_plan": c.id in planned_ids,
            }
            for o, c, s in rows
        ],
        "total": total,
        "page": page,
        "page_size": size,
    }
