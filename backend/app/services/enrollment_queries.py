"""Read models shared by course search, timetable and enrollment rules."""

from sqlalchemy import case, cast, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import api_error
from app.models import Course, CourseOffering, Enrollment, Student, Waitlist


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
    } | {field: getattr(course, field) for field in ("code", "name", "credits")}


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
    rows = await session.execute(
        base.add_columns(
            case((active, "ENROLLED"), (waiting, "WAITLISTED"), else_=None)
        )
        .order_by(Course.code, CourseOffering.section, CourseOffering.id)
        .offset((page - 1) * size)
        .limit(size)
    )
    return {
        "items": [offering_dict(o, c) | {"my_status": s} for o, c, s in rows],
        "total": total,
        "page": page,
        "page_size": size,
    }
