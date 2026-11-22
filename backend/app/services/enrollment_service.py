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
from app.core.faculty import course_allowed_for_faculty
from app.core.redis import get_redis
from app.models import (
    CompletedCourse,
    Course,
    CourseOffering,
    Enrollment,
    Student,
    TermCourseOpening,
    Waitlist,
)
from app.services.enrollment_lock import acquire_offering_lock
from app.services.enrollment_queries import active_items
from app.services.phase_service import assert_enrollment_open
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
    opening = await session.get(TermCourseOpening, (offering.term, offering.course_id))
    if opening is not None and getattr(opening, "status", None) == "NOT_OPENED":
        raise api_error(
            422,
            "COURSE_NOT_OPENED",
            "Học phần này không mở lớp trong học kỳ do không đủ số lượng sinh viên đăng ký kế hoạch học tập",
        )
    course_row = (
        await session.execute(
            select(Course.credits, Course.min_accumulated_credits, Course.code).where(
                Course.id == offering.course_id
            )
        )
    ).one_or_none()
    credits = int(course_row[0]) if course_row else 0
    min_acc_credits = int(course_row[1]) if course_row else 0
    course_code = str(course_row[2]) if course_row and len(course_row) > 2 else ""
    student_faculty = getattr(student, "faculty", None)
    if (
        getattr(student, "role", "student") == "student"
        and student_faculty
        and course_code
        and not course_allowed_for_faculty(course_code, student_faculty)
    ):
        raise api_error(
            422,
            "FACULTY_MISMATCH",
            f"Học phần {course_code} không thuộc chương trình đào tạo của {student_faculty}.",
        )
    student_acc = int(getattr(student, "accumulated_credits", 0) or 0)
    if min_acc_credits > 0 and student_acc < min_acc_credits:
        raise api_error(
            422,
            "MIN_ACCUMULATED_CREDITS_NOT_MET",
            f"Chưa đủ tín chỉ tích lũy tối thiểu (cần {min_acc_credits} TC, hiện có {student_acc} TC)",
            required_credits=min_acc_credits,
            current_credits=student_acc,
        )
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
        result = json.loads(raw) if raw else None
        if (
            not isinstance(result, dict)
            or not {"id", "offering_id", "status"} <= result.keys()
        ):
            return None
        if result["status"] not in {"ACTIVE", "WAITLISTED"}:
            return None
        return result
    except (RedisError, OSError, TimeoutError, ValueError):
        return None


async def cache_result(
    key: str | None, result: dict, *, committed: bool = False
) -> None:
    if key:
        try:
            async with asyncio.timeout(0.3):
                ttl = get_settings().enrollment_idempotency_ttl_sec
                if committed:
                    # A delayed finalizer must not replace a newer value after
                    # expiration/reuse of the key by another transaction.
                    await get_redis().eval(
                        "if redis.call('get',KEYS[1]) == ARGV[1] then "
                        "return redis.call('set',KEYS[1],ARGV[2],'EX',ARGV[3]) end return 0",
                        1,
                        key,
                        json.dumps(result),
                        json.dumps(result | {"_committed": True}),
                        ttl,
                    )
                else:
                    await get_redis().set(key, json.dumps(result), ex=ttl)
        except (RedisError, OSError, TimeoutError):
            pass


async def run_transaction(
    session: AsyncSession, operation: Callable[[], Awaitable[dict]]
) -> dict:
    for attempt in range(3):
        try:
            # Bound pool checkout too: lock_timeout starts only after checkout.
            # Overload must become a retryable business response, not a pool 500.
            async with asyncio.timeout(
                get_settings().enrollment_db_admission_timeout_sec
            ):
                await session.execute(
                    select(
                        func.set_config(
                            "lock_timeout",
                            f"{get_settings().enrollment_db_lock_timeout_ms}ms",
                            True,
                        )
                    )
                )
            result = await operation()
            await session.commit()
            return result
        except TimeoutError as exc:
            await session.rollback()
            raise api_error(
                409, "CONCURRENT_UPDATE", "Hệ thống đang bận, hãy thử lại"
            ) from exc
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
        try:
            async with asyncio.timeout(
                get_settings().enrollment_db_admission_timeout_sec
            ):
                async with session.bind.connect() as connection:
                    remaining = await connection.scalar(
                        select(
                            CourseOffering.capacity - CourseOffering.enrolled_count
                        ).where(CourseOffering.id == offering_id)
                    )
        except TimeoutError as exc:
            raise api_error(
                409, "CONCURRENT_UPDATE", "Hệ thống đang bận, hãy thử lại"
            ) from exc
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
            if (
                persisted is None
                or persisted.student_id != student_id
                or persisted.offering_id != cached["offering_id"]
            ):
                cached = None
        if cached:
            if cached["offering_id"] != offering_id:
                raise api_error(
                    409, "IDEMPOTENCY_KEY_REUSED", "Key đã dùng cho lớp khác"
                )
            return {k: v for k, v in cached.items() if k != "_committed"}
        item = await get_offering(session, offering_id)
        await assert_enrollment_open(session, term=item.term)
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
        await cache_result(key, result, committed=True)
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
        offering = await get_offering(session, offering_id, lock=True)
        await assert_enrollment_open(session, term=offering.term)
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


async def swap_section(
    session: AsyncSession,
    student_id: int,
    from_enrollment_id: int,
    to_offering_id: int,
    idempotency_key: str | None = None,
) -> dict:
    """Đổi lớp học phần nguyên tử (Atomic Section Swap).

    Khóa sinh viên theo thứ tự ID tăng dần trước, sau đó khóa 2 CourseOffering theo
    thứ tự ID tăng dần để đảm bảo tuyệt đối không deadlock khi đổi chéo đồng thời.
    """
    from app.services.waitlist_service import promote_next, queue_rows, reindex

    key = f"idem:swap:{student_id}:{idempotency_key}" if idempotency_key else None

    async def operation() -> dict:
        enrollment = await session.scalar(
            select(Enrollment)
            .where(
                Enrollment.id == from_enrollment_id,
                Enrollment.student_id == student_id,
            )
            .execution_options(populate_existing=True)
        )
        if enrollment is None:
            raise api_error(404, "NOT_FOUND", "Không tìm thấy đăng ký hiện tại")
        if enrollment.status != "ACTIVE":
            raise api_error(
                409,
                "ENROLLMENT_NOT_ACTIVE",
                "Chỉ có thể đổi lớp đối với học phần đang ở trạng thái ACTIVE",
            )

        from_offering_id = enrollment.offering_id
        if from_offering_id == to_offering_id:
            raise api_error(
                422,
                "SAME_SECTION",
                "Bạn đang đăng ký chính lớp học phần này",
            )

        queue = await queue_rows(session, from_offering_id)
        ids = {student_id} | {w.student_id for w in queue}
        students = await lock_students(session, ids)
        if student_id not in students:
            raise api_error(404, "NOT_FOUND", "Không tìm thấy sinh viên")

        cached = await cached_result(key)
        if cached and cached.get("_committed"):
            if (
                cached.get("from_enrollment_id") != from_enrollment_id
                or cached.get("to_offering_id") != to_offering_id
            ):
                raise api_error(
                    409,
                    "IDEMPOTENCY_KEY_REUSED",
                    "Idempotency-Key đã được dùng cho yêu cầu đổi lớp khác",
                )
            return {k: v for k, v in cached.items() if k != "_committed"}

        # Khóa đồng thời 2 lớp học phần theo thứ tự ID tăng dần để tránh deadlock
        locked_offerings = {
            row.id: row
            for row in (
                await session.scalars(
                    select(CourseOffering)
                    .where(CourseOffering.id.in_([from_offering_id, to_offering_id]))
                    .order_by(CourseOffering.id)
                    .with_for_update()
                    .execution_options(populate_existing=True)
                )
            ).all()
        }
        from_offering = locked_offerings.get(from_offering_id)
        to_offering = locked_offerings.get(to_offering_id)
        if from_offering is None or to_offering is None:
            raise api_error(404, "NOT_FOUND", "Không tìm thấy lớp học phần đích")

        await assert_enrollment_open(session, term=to_offering.term)

        if from_offering.course_id != to_offering.course_id:
            raise api_error(
                422,
                "DIFFERENT_COURSE",
                "Chỉ được phép đổi giữa các lớp thuộc cùng một học phần",
            )
        if from_offering.term != to_offering.term:
            raise api_error(
                422,
                "DIFFERENT_TERM",
                "Chỉ được phép đổi sang lớp học phần thuộc cùng học kỳ",
            )

        opening = await session.get(
            TermCourseOpening, (to_offering.term, to_offering.course_id)
        )
        if opening is not None and getattr(opening, "status", None) == "NOT_OPENED":
            raise api_error(
                422,
                "COURSE_NOT_OPENED",
                "Học phần này không mở lớp trong học kỳ hiện tại",
            )

        # Kiểm tra lại hàng chờ của lớp cũ sau khi đã giữ khóa offering
        queue = await queue_rows(session, from_offering_id)
        if any(w.student_id not in ids for w in queue):
            raise QueueChanged()

        await session.refresh(enrollment)
        if enrollment.status != "ACTIVE":
            raise api_error(
                409, "CONCURRENT_UPDATE", "Trạng thái đăng ký lớp cũ vừa thay đổi"
            )

        if to_offering.enrolled_count >= to_offering.capacity:
            raise api_error(
                409,
                "SECTION_FULL",
                "Lớp học phần đích đã hết chỗ. Lớp cũ của bạn vẫn được giữ nguyên.",
            )

        # Kiểm tra trùng lịch với các môn ACTIVE khác (LOẠI TRỪ lớp đang đổi đi)
        other_active = [
            item
            for item in await active_items(session, student_id, to_offering.term)
            if item["id"] != from_offering_id
        ]
        conflicts = find_schedule_conflicts(
            to_offering.schedule, other_active, get_settings().min_break_minutes
        )
        if conflicts:
            raise api_error(
                409,
                "SCHEDULE_CONFLICT",
                "Lớp đích bị trùng lịch học. Lớp cũ của bạn vẫn được giữ nguyên.",
                conflicts_with=[
                    {
                        "offering_id": i["id"],
                        "course_code": i["code"],
                        "section": i["section"],
                    }
                    for i in conflicts
                ],
            )

        # Thực thi đổi lớp nguyên tử: hủy lớp cũ -> nhả chỗ cũ -> giữ chỗ mới -> tạo đăng ký mới
        changed = await session.scalar(
            update(Enrollment)
            .where(
                Enrollment.id == from_enrollment_id,
                Enrollment.version == enrollment.version,
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
            raise api_error(409, "CONCURRENT_UPDATE", "Phiên bản đăng ký đã thay đổi")

        await session.execute(
            update(CourseOffering)
            .where(CourseOffering.id == from_offering_id)
            .values(enrolled_count=CourseOffering.enrolled_count - 1)
        )

        if not await reserve_seat(session, to_offering_id):
            raise api_error(
                409,
                "SECTION_FULL",
                "Lớp học phần đích vừa hết chỗ. Lớp cũ của bạn vẫn được giữ nguyên.",
            )

        new_enr = await create_enrollment(session, student_id, to_offering_id)

        # Nếu sinh viên từng nằm trong Waitlist của chính lớp đích thì tự dọn sạch
        existing_wl = await session.scalar(
            select(Waitlist).where(
                Waitlist.student_id == student_id,
                Waitlist.offering_id == to_offering_id,
            )
        )
        if existing_wl is not None:
            await session.delete(existing_wl)
            await session.flush()
            await reindex(session, to_offering_id)

        # Tự động đôn người đầu hàng chờ của lớp cũ (nếu có)
        promotion = await promote_next(session, from_offering_id, queue, students)

        payload = {
            "from_enrollment_id": from_enrollment_id,
            "new_enrollment_id": new_enr["id"],
            "from_offering_id": from_offering_id,
            "to_offering_id": to_offering_id,
            "status": "SWAPPED",
            "version": new_enr["version"],
            "promoted_student_id": (
                int(promotion["student_id"]) if promotion else None
            ),
            "_promotion": promotion,
        }
        await cache_result(key, {k: v for k, v in payload.items() if k != "_promotion"})
        return payload

    result = await run_transaction(session, operation)
    promotion = result.pop("_promotion", None)
    if promotion:
        logging.getLogger(__name__).info(json.dumps(promotion))
    await cache_result(key, result, committed=True)
    return result
