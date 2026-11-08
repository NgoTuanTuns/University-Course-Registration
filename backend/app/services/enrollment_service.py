"""Enrollment rules and transaction boundaries owned by M3."""

import asyncio
import json
import logging
import random
from collections.abc import Awaitable, Callable

from redis.exceptions import RedisError
from sqlalchemy import func, select, update
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import api_error
from app.core.redis import get_redis
from app.models import (
    CompletedCourse,
    Course,
    CourseOffering,
    Enrollment,
    Student,
    Waitlist,
)
from app.services.enrollment_lock import acquire_offering_lock
from app.services.enrollment_queries import active_items
from app.services.prerequisite_engine import check_eligibility
from app.services.schedule_conflict import find_schedule_conflicts


class QueueChanged(Exception):
    """Retry with a fresh, sorted set of student locks."""


async def lock_students(session: AsyncSession, ids: set[int]) -> dict[int, Student]:
    rows = await session.scalars(
        select(Student)
        .where(Student.id.in_(ids))
        .order_by(Student.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    return {row.id: row for row in rows}


async def get_offering(
    session: AsyncSession, offering_id: int, lock: bool = False
) -> CourseOffering:
    stmt = select(CourseOffering).where(CourseOffering.id == offering_id)
    if lock:
        stmt = stmt.with_for_update().execution_options(populate_existing=True)
    item = await session.scalar(stmt)
    if item is None:
        raise api_error(404, "NOT_FOUND", "Không tìm thấy lớp học phần")
    return item


async def ensure_eligible(
    session: AsyncSession, student: Student, offering: CourseOffering
) -> None:
    items = await active_items(session, student.id, offering.term)
    if any(i["course_id"] == offering.course_id for i in items):
        raise api_error(409, "ALREADY_ENROLLED", "Đã đăng ký môn trong kỳ này")
    completed = await session.get(CompletedCourse, (student.id, offering.course_id))
    if completed:
        raise api_error(409, "ALREADY_COMPLETED", "Môn học đã đạt")
    eligibility = await check_eligibility(session, student.id, offering.course_id)
    if not eligibility.eligible:
        raise api_error(
            422,
            "PREREQ_NOT_MET",
            "Thiếu môn tiên quyết",
            missing_courses=eligibility.missing_courses,
        )
    conflicts = find_schedule_conflicts(
        offering.schedule, items, get_settings().min_break_minutes
    )
    if conflicts:
        raise api_error(
            409,
            "SCHEDULE_CONFLICT",
            "Trùng lịch học",
            conflicts_with=[
                {
                    "offering_id": i["id"],
                    "course_code": i["code"],
                    "section": i["section"],
                }
                for i in conflicts
            ],
        )
    current = sum(i["credits"] for i in items)
    credits = await session.scalar(
        select(Course.credits).where(Course.id == offering.course_id)
    )
    if current + credits > student.max_credits:
        raise api_error(
            422,
            "CREDIT_LIMIT_EXCEEDED",
            "Vượt giới hạn tín chỉ",
            current_credits=current,
            requested_credits=credits,
            max_credits=student.max_credits,
        )


async def reserve_seat(session: AsyncSession, offering_id: int) -> bool:
    return (
        await session.scalar(
            update(CourseOffering)
            .where(
                CourseOffering.id == offering_id,
                CourseOffering.enrolled_count < CourseOffering.capacity,
            )
            .values(enrolled_count=CourseOffering.enrolled_count + 1)
            .returning(CourseOffering.id)
        )
        is not None
    )


async def create_enrollment(
    session: AsyncSession, student_id: int, offering_id: int
) -> dict:
    item = Enrollment(
        student_id=student_id, offering_id=offering_id, status="ACTIVE", version=0
    )
    session.add(item)
    await session.flush()
    return {"id": item.id, "offering_id": offering_id, "status": "ACTIVE", "version": 0}


async def cached_result(key: str | None) -> dict | None:
    if key is None:
        return None
    try:
        async with asyncio.timeout(0.3):
            raw = await get_redis().get(key)
        return json.loads(raw) if raw else None
    except (RedisError, OSError, TimeoutError, ValueError):
        return None


async def cache_result(key: str | None, result: dict) -> None:
    if key:
        try:
            async with asyncio.timeout(0.3):
                await get_redis().set(
                    key,
                    json.dumps(result),
                    ex=get_settings().enrollment_idempotency_ttl_sec,
                )
        except (RedisError, OSError, TimeoutError):
            pass


async def run_transaction(
    session: AsyncSession, operation: Callable[[], Awaitable[dict]]
) -> dict:
    for attempt in range(3):
        try:
            result = await operation()
            await session.commit()
            return result
        except (QueueChanged, DBAPIError) as exc:
            await session.rollback()
            state = getattr(getattr(exc, "orig", None), "sqlstate", None)
            retry = isinstance(exc, QueueChanged) or state in {
                "40P01",
                "40001",
                "55P03",
            }
            if isinstance(exc, IntegrityError):
                raise api_error(409, "ALREADY_ENROLLED", "Đăng ký đã tồn tại") from exc
            if not retry:
                raise
            if attempt == 2:
                raise api_error(
                    409, "CONCURRENT_UPDATE", "Dữ liệu vừa thay đổi, hãy thử lại"
                ) from exc
            await asyncio.sleep(random.uniform(0.01, 0.04))
        except BaseException:
            await session.rollback()
            raise
    raise AssertionError("unreachable")


async def enroll(
    session: AsyncSession,
    student_id: int,
    offering_id: int,
    idempotency_key: str | None = None,
) -> dict:
    from app.services.waitlist_service import enqueue

    key = f"idem:enroll:{student_id}:{idempotency_key}" if idempotency_key else None
    # This hint uses a separate short connection: never hold a DB transaction
    # while waiting at the Redis gate. It has no role in business correctness.
    use_gate = False
    if get_settings().enrollment_redis_lock_enabled:
        async with session.bind.connect() as connection:
            remaining = await connection.scalar(
                select(CourseOffering.capacity - CourseOffering.enrolled_count).where(
                    CourseOffering.id == offering_id
                )
            )
        use_gate = (
            remaining is not None and remaining <= get_settings().lock_seat_threshold
        )

    async def operation() -> dict:
        students = await lock_students(session, {student_id})
        if student_id not in students:
            raise api_error(404, "NOT_FOUND", "Không tìm thấy sinh viên")
        cached = await cached_result(key)
        if cached and not cached.get("_committed"):
            # Reject a cache entry published by a transaction that rolled back.
            model = Enrollment if cached["status"] == "ACTIVE" else Waitlist
            persisted = await session.get(model, cached["id"])
            if persisted is None or persisted.student_id != student_id:
                cached = None
        if cached:
            if cached["offering_id"] != offering_id:
                raise api_error(
                    409, "IDEMPOTENCY_KEY_REUSED", "Key đã dùng cho lớp khác"
                )
            return {k: v for k, v in cached.items() if k != "_committed"}
        item = await get_offering(session, offering_id)
        eligibility_fields = (
            item.course_id,
            item.term,
            json.dumps(item.schedule, sort_keys=True),
        )
        # Different students may evaluate in parallel. Their own student row is
        # still locked, so concurrent schedule/credit checks cannot race.
        await ensure_eligible(session, students[student_id], item)
        item = await get_offering(session, offering_id, lock=True)
        if eligibility_fields != (
            item.course_id,
            item.term,
            json.dumps(item.schedule, sort_keys=True),
        ):
            raise QueueChanged()  # An admin changed eligibility data while we evaluated.
        if await session.scalar(
            select(Waitlist.id).where(
                Waitlist.student_id == student_id, Waitlist.offering_id == offering_id
            )
        ):
            raise api_error(409, "ALREADY_WAITLISTED", "Đã ở trong hàng chờ")
        if await reserve_seat(session, offering_id):
            result = await create_enrollment(session, student_id, offering_id)
        else:
            result = await enqueue(session, student_id, item)
        # Publish while the student row is held. A waiter sees this only after commit.
        await cache_result(key, result)
        return result

    async with acquire_offering_lock(offering_id, use_gate):
        result = await run_transaction(session, operation)
        # Preserve the original response even if its waitlist row is later removed.
        await cache_result(key, result | {"_committed": True})
        return result


async def cancel(
    session: AsyncSession,
    student_id: int,
    enrollment_id: int,
    version: int | None = None,
) -> dict:
    from app.services.waitlist_service import promote_next, queue_rows

    async def operation() -> dict:
        enrollment = await session.scalar(
            select(Enrollment)
            .where(Enrollment.id == enrollment_id, Enrollment.student_id == student_id)
            .execution_options(populate_existing=True)
        )
        if enrollment is None:
            raise api_error(404, "NOT_FOUND", "Không tìm thấy đăng ký")
        offering_id = enrollment.offering_id
        queue = await queue_rows(session, offering_id)
        ids = {student_id} | {w.student_id for w in queue}
        students = await lock_students(session, ids)
        # All affected students are locked in ascending order BEFORE the offering.
        await get_offering(session, offering_id, lock=True)
        queue = await queue_rows(session, offering_id)
        if any(w.student_id not in ids for w in queue):
            raise QueueChanged()
        await session.refresh(enrollment)
        promotion = None
        if enrollment.status != "CANCELLED":
            expected = enrollment.version if version is None else version
            changed = await session.scalar(
                update(Enrollment)
                .where(
                    Enrollment.id == enrollment_id,
                    Enrollment.version == expected,
                    Enrollment.status == "ACTIVE",
                )
                .values(
                    status="CANCELLED",
                    version=Enrollment.version + 1,
                    cancelled_at=func.now(),
                )
                .returning(Enrollment.id)
            )
            if changed is None:
                raise api_error(
                    409, "CONCURRENT_UPDATE", "Phiên bản đăng ký đã thay đổi"
                )
            await session.execute(
                update(CourseOffering)
                .where(CourseOffering.id == offering_id)
                .values(enrolled_count=CourseOffering.enrolled_count - 1)
            )
            promotion = await promote_next(session, offering_id, queue, students)
        return {
            "id": enrollment.id,
            "offering_id": offering_id,
            "status": "CANCELLED",
            "version": enrollment.version,
            "_promotion": promotion,
        }

    result = await run_transaction(session, operation)
    promotion = result.pop("_promotion", None)
    if promotion:
        logging.getLogger(__name__).info(json.dumps(promotion))
    return result
