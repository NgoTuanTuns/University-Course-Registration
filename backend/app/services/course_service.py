"""Nghiệp vụ quản trị học phần (M4, Tuần 3).

Quy ước chung của nhóm:
- Tầng service thực hiện logic và quyết định commit/rollback.
- Kiểm tra trùng lặp mã (ALREADY_EXISTS 409).
- Kiểm tra tính toàn vẹn tham chiếu trước khi xóa (IN_USE 409):
  Không cho phép xóa học phần nếu đang có lớp học phần mở, có trong bảng điểm
  hoặc đang là môn tiên quyết của môn khác.
"""

from __future__ import annotations

import logging

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import api_error
from app.core.redis import get_redis
from app.models import CompletedCourse, Course, CourseOffering, Prerequisite
from app.schemas.course import CourseCreate, CourseUpdate

logger = logging.getLogger(__name__)


async def list_courses(
    session: AsyncSession,
    q: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Course], int]:
    """Lấy danh sách học phần có phân trang và tìm kiếm theo mã hoặc tên."""
    page = max(1, page)
    page_size = min(max(1, page_size), 100)

    query = select(Course)
    count_query = select(func.count()).select_from(Course)

    if q:
        search_filter = or_(
            Course.code.ilike(f"%{q.strip()}%"),
            Course.name.ilike(f"%{q.strip()}%"),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    total_res = await session.execute(count_query)
    total = total_res.scalar_one()

    query = query.order_by(Course.code).offset((page - 1) * page_size).limit(page_size)
    items_res = await session.execute(query)
    items = list(items_res.scalars().all())

    return items, total


async def get_course_by_id(session: AsyncSession, course_id: int) -> Course:
    """Lấy thông tin học phần theo ID, ném NOT_FOUND nếu không tìm thấy."""
    res = await session.execute(select(Course).where(Course.id == course_id))
    course = res.scalar_one_or_none()
    if course is None:
        raise api_error(404, "NOT_FOUND", f"Không tìm thấy học phần có ID={course_id}")
    return course


async def create_course(session: AsyncSession, data: CourseCreate) -> Course:
    """Tạo học phần mới, kiểm tra trùng mã."""
    code_normalized = data.code.strip().upper()
    name_normalized = data.name.strip()

    # Kiểm tra mã đã tồn tại
    existing = await session.execute(
        select(Course).where(Course.code == code_normalized)
    )
    if existing.scalar_one_or_none() is not None:
        raise api_error(
            409, "ALREADY_EXISTS", f"Mã học phần '{code_normalized}' đã tồn tại"
        )

    course = Course(
        code=code_normalized,
        name=name_normalized,
        credits=data.credits,
        description=data.description.strip() if data.description else None,
    )
    session.add(course)
    await session.commit()
    await session.refresh(course)
    return course


async def update_course(
    session: AsyncSession, course_id: int, data: CourseUpdate
) -> Course:
    """Cập nhật thông tin học phần (tên, tín chỉ, mô tả)."""
    course = await get_course_by_id(session, course_id)

    if data.name is not None:
        course.name = data.name.strip()
    if data.credits is not None:
        course.credits = data.credits
    if data.description is not None:
        course.description = data.description.strip()

    await session.commit()
    await session.refresh(course)
    return course


async def delete_course(session: AsyncSession, course_id: int) -> None:
    """Xóa học phần với kiểm tra ràng buộc tham chiếu chặt chẽ.

    Nếu học phần đang được tham chiếu bởi lớp học phần, bảng điểm hoàn thành
    hoặc cây tiên quyết, trả 409 IN_USE kèm danh sách chi tiết lý do.
    """
    course = await get_course_by_id(session, course_id)

    reasons: list[str] = []

    # 1. Kiểm tra lớp học phần (course_offerings)
    offering_count_res = await session.execute(
        select(func.count())
        .select_from(CourseOffering)
        .where(CourseOffering.course_id == course_id)
    )
    offering_count = offering_count_res.scalar_one()
    if offering_count > 0:
        reasons.append(f"Đang có {offering_count} lớp học phần được mở cho môn này")

    # 2. Kiểm tra là môn tiên quyết của môn khác (prerequisites.prereq_course_id)
    prereq_of_res = await session.execute(
        select(func.count())
        .select_from(Prerequisite)
        .where(Prerequisite.prereq_course_id == course_id)
    )
    prereq_of_count = prereq_of_res.scalar_one()
    if prereq_of_count > 0:
        reasons.append(
            f"Đang là điều kiện tiên quyết cho {prereq_of_count} môn học khác"
        )

    # 3. Kiểm tra môn học có điều kiện tiên quyết (prerequisites.course_id)
    has_prereq_res = await session.execute(
        select(func.count())
        .select_from(Prerequisite)
        .where(Prerequisite.course_id == course_id)
    )
    has_prereq_count = has_prereq_res.scalar_one()
    if has_prereq_count > 0:
        reasons.append(
            f"Môn học đang có {has_prereq_count} điều kiện tiên quyết liên kết"
        )

    # 4. Kiểm tra đã có sinh viên hoàn thành (completed_courses)
    completed_res = await session.execute(
        select(func.count())
        .select_from(CompletedCourse)
        .where(CompletedCourse.course_id == course_id)
    )
    completed_count = completed_res.scalar_one()
    if completed_count > 0:
        reasons.append(
            f"Đã có {completed_count} sinh viên có điểm hoàn thành môn học này"
        )

    if reasons:
        raise api_error(
            status_code=409,
            code="IN_USE",
            message=f"Học phần '{course.code}' đang được tham chiếu, không thể xóa",
            references=reasons,
        )

    await session.delete(course)
    await session.commit()

    # Xóa cache tiên quyết trong Redis nếu có
    try:
        r = get_redis()
        keys = []
        async for k in r.scan_iter(match="prereq:*"):
            keys.append(k)
        if keys:
            await r.delete(*keys)
    except Exception as exc:
        logger.warning("Không thể xóa cache Redis sau khi xóa học phần: %s", exc)
