"""FIFO queue operations; callers hold student and offering locks before writes."""

from datetime import UTC, datetime
from math import ceil

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import api_error
from app.models import Course, CourseOffering, Student, Waitlist
from app.services.enrollment_queries import offering_dict


async def queue_rows(session: AsyncSession, offering_id: int) -> list[Waitlist]:
    return list(
        await session.scalars(
            select(Waitlist)
            .where(Waitlist.offering_id == offering_id)
            .order_by(Waitlist.enqueued_at, Waitlist.id)
            .execution_options(populate_existing=True)
        )
    )


async def reindex(session: AsyncSession, offering_id: int) -> None:
    for position, row in enumerate(await queue_rows(session, offering_id), 1):
        row.position = position
    await session.flush()


async def enqueue(
    session: AsyncSession, student_id: int, offering: CourseOffering
) -> dict:
    queue = await queue_rows(session, offering.id)
    if len(queue) >= ceil(offering.capacity * get_settings().waitlist_max_ratio):
        raise api_error(409, "WAITLIST_FULL", "Hàng chờ đã đầy")
    # clock_timestamp avoids ordering by transaction start time after lock waits.
    from sqlalchemy import func

    row = Waitlist(
        student_id=student_id,
        offering_id=offering.id,
        position=len(queue) + 1,
        enqueued_at=func.clock_timestamp(),
    )
    session.add(row)
    await session.flush()
    return {
        "id": row.id,
        "offering_id": offering.id,
        "status": "WAITLISTED",
        "position": row.position,
    }


async def promote_next(
    session: AsyncSession,
    offering_id: int,
    queue: list[Waitlist],
    students: dict[int, Student],
) -> dict | None:
    from app.services.enrollment_service import (
        create_enrollment,
        ensure_eligible,
        get_offering,
        reserve_seat,
    )

    event = None
    offering = await get_offering(session, offering_id)
    for row in queue:
        try:
            await ensure_eligible(session, students[row.student_id], offering)
        except HTTPException:
            continue  # Keep blocked people in the queue, then try the next eligible one.
        if not await reserve_seat(session, offering_id):
            break
        await create_enrollment(session, row.student_id, offering_id)
        await session.delete(row)
        await session.flush()
        event = {
            "event": "waitlist_promoted",
            "offering_id": offering_id,
            "student_id": row.student_id,
            "wait_seconds": (datetime.now(UTC) - row.enqueued_at).total_seconds(),
        }
        break
    await reindex(session, offering_id)
    return event


async def leave(session: AsyncSession, student_id: int, waitlist_id: int) -> dict:
    from app.services.enrollment_service import (
        get_offering,
        lock_students,
        run_transaction,
    )

    async def operation() -> dict:
        await lock_students(session, {student_id})
        row = await session.scalar(
            select(Waitlist).where(
                Waitlist.id == waitlist_id, Waitlist.student_id == student_id
            )
        )
        if row is None:
            raise api_error(404, "NOT_FOUND", "Không tìm thấy hàng chờ")
        offering_id = row.offering_id
        await get_offering(session, offering_id, lock=True)
        await session.delete(row)
        await session.flush()
        await reindex(session, offering_id)
        return {"id": waitlist_id, "offering_id": offering_id, "status": "REMOVED"}

    return await run_transaction(session, operation)


async def list_waitlist(
    session: AsyncSession, student_id: int, page: int, page_size: int
) -> dict:
    from sqlalchemy import func

    from app.services.enrollment_service import ensure_eligible

    total = await session.scalar(
        select(func.count())
        .select_from(Waitlist)
        .where(Waitlist.student_id == student_id)
    )
    rows = await session.execute(
        select(Waitlist, CourseOffering, Course)
        .join(CourseOffering, Waitlist.offering_id == CourseOffering.id)
        .join(Course, CourseOffering.course_id == Course.id)
        .where(Waitlist.student_id == student_id)
        .order_by(Waitlist.enqueued_at, Waitlist.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    student = await session.get(Student, student_id)
    items = []
    for row, offering, course in rows:
        reason = None
        try:
            await ensure_eligible(session, student, offering)
        except HTTPException as exc:
            reason = exc.detail["code"]
        items.append(
            offering_dict(offering, course)
            | {
                "waitlist_id": row.id,
                "position": row.position,
                "enqueued_at": row.enqueued_at,
                "blocked_reason": reason,
                "my_status": "WAITLISTED",
            }
        )
    return {"items": items, "total": total, "page": page, "page_size": page_size}
