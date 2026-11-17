"""Dịch vụ quản trị điều kiện tiên quyết (M4, Tuần 4 - /admin/prereqs).

Các chức năng:
- Xem danh sách tiên quyết của môn học (nhóm AND và các nhóm OR).
- Thêm cạnh tiên quyết mới:
  + Kiểm tra loại AND (group_no = 0) / OR (group_no >= 1).
  + Chặn tự trỏ (course_id <> prereq_course_id).
  + Kiểm tra tồn tại môn học (404 NOT_FOUND).
  + Kiểm tra trùng cạnh (409 ALREADY_EXISTS).
  + Chặn chu trình bằng DFS (422 PREREQ_CYCLE kèm cycle_path).
  + Khóa PostgreSQL advisory lock để tuần tự hóa hai admin cùng thêm cạnh.
  + Sau commit: tự động xóa cache Redis bằng invalidate_graph().
- Cập nhật loại / nhóm OR của cạnh tiên quyết.
- Xóa cạnh tiên quyết và xóa cache Redis tương ứng.
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import aliased

from app.core.errors import api_error
from app.models import Course, Prerequisite
from app.schemas.prerequisite import (
    CoursePrereqsResponse,
    OrGroupPrereqOut,
    PrereqCreate,
    PrereqEdgeOut,
    PrereqItemOut,
    PrereqUpdate,
)
from app.services import prerequisite_engine
from app.services.prerequisite_core import PrerequisiteCycleError

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def get_course_prerequisites(
    session: AsyncSession, course_id: int
) -> CoursePrereqsResponse:
    """Lấy danh sách điều kiện tiên quyết của một học phần, chia thành AND và các nhóm OR."""
    course = await session.get(Course, course_id)
    if course is None:
        raise api_error(404, "NOT_FOUND", f"Không tìm thấy học phần có ID={course_id}")

    PrereqCourse = aliased(Course)
    stmt = (
        select(Prerequisite, PrereqCourse)
        .join(PrereqCourse, Prerequisite.prereq_course_id == PrereqCourse.id)
        .where(Prerequisite.course_id == course_id)
        .order_by(Prerequisite.type, Prerequisite.group_no, PrereqCourse.code)
    )
    results = (await session.execute(stmt)).all()

    and_items: list[PrereqItemOut] = []
    or_dict: dict[int, list[PrereqItemOut]] = defaultdict(list)
    all_items: list[PrereqItemOut] = []

    for prereq, p_course in results:
        item = PrereqItemOut(
            prereq_course_id=p_course.id,
            prereq_code=p_course.code,
            prereq_name=p_course.name,
            credits=p_course.credits,
            type=prereq.type,
            group_no=prereq.group_no,
        )
        all_items.append(item)
        if prereq.type == "AND":
            and_items.append(item)
        else:
            or_dict[prereq.group_no].append(item)

    or_groups = [
        OrGroupPrereqOut(group_no=g_no, options=options)
        for g_no, options in sorted(or_dict.items())
    ]

    return CoursePrereqsResponse(
        course_id=course.id,
        course_code=course.code,
        course_name=course.name,
        and_prerequisites=and_items,
        or_groups=or_groups,
        items=all_items,
    )


async def list_prerequisites(
    session: AsyncSession, course_id: int | None = None
) -> list[PrereqEdgeOut]:
    """Lấy toàn bộ danh sách cạnh tiên quyết trong hệ thống hoặc lọc theo môn học."""
    ParentCourse = aliased(Course)
    PrereqCourse = aliased(Course)

    stmt = (
        select(Prerequisite, ParentCourse, PrereqCourse)
        .join(ParentCourse, Prerequisite.course_id == ParentCourse.id)
        .join(PrereqCourse, Prerequisite.prereq_course_id == PrereqCourse.id)
    )
    if course_id is not None:
        stmt = stmt.where(Prerequisite.course_id == course_id)

    stmt = stmt.order_by(
        ParentCourse.code,
        Prerequisite.type,
        Prerequisite.group_no,
        PrereqCourse.code,
    )
    results = (await session.execute(stmt)).all()

    return [
        PrereqEdgeOut(
            course_id=parent.id,
            course_code=parent.code,
            course_name=parent.name,
            prereq_course_id=prereq.id,
            prereq_code=prereq.code,
            prereq_name=prereq.name,
            type=edge.type,
            group_no=edge.group_no,
        )
        for edge, parent, prereq in results
    ]


def _validate_prereq_type_and_group(edge_type: str, group_no: int) -> None:
    if edge_type == "AND" and group_no != 0:
        raise api_error(
            422,
            "VALIDATION_ERROR",
            "Điều kiện loại AND bắt buộc phải có group_no = 0",
        )
    if edge_type == "OR" and group_no < 1:
        raise api_error(
            422,
            "VALIDATION_ERROR",
            "Điều kiện loại OR bắt buộc phải có group_no >= 1",
        )


async def create_prerequisite(
    session: AsyncSession, body: PrereqCreate
) -> PrereqEdgeOut:
    """Thêm một điều kiện tiên quyết mới có kiểm tra chu trình và khóa advisory."""
    if body.course_id == body.prereq_course_id:
        raise api_error(
            422,
            "VALIDATION_ERROR",
            "Học phần không thể đặt điều kiện tiên quyết là chính nó",
        )

    _validate_prereq_type_and_group(body.type, body.group_no)

    parent_course = await session.get(Course, body.course_id)
    if parent_course is None:
        raise api_error(
            404, "NOT_FOUND", f"Không tìm thấy học phần có ID={body.course_id}"
        )

    prereq_course = await session.get(Course, body.prereq_course_id)
    if prereq_course is None:
        raise api_error(
            404,
            "NOT_FOUND",
            f"Không tìm thấy học phần tiên quyết có ID={body.prereq_course_id}",
        )

    existing = await session.execute(
        select(Prerequisite).where(
            Prerequisite.course_id == body.course_id,
            Prerequisite.prereq_course_id == body.prereq_course_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise api_error(
            409,
            "ALREADY_EXISTS",
            f"Điều kiện tiên quyết giữa {parent_course.code} và {prereq_course.code} đã tồn tại",
        )

    # Kiểm tra chu trình có giữ khóa tư vấn PostgreSQL pg_advisory_xact_lock
    try:
        await prerequisite_engine.ensure_edge_allowed(
            session, body.course_id, body.prereq_course_id, lock=True
        )
    except PrerequisiteCycleError as exc:
        raise prerequisite_engine.cycle_http_error(exc) from exc

    new_edge = Prerequisite(
        course_id=body.course_id,
        prereq_course_id=body.prereq_course_id,
        type=body.type,
        group_no=body.group_no,
    )
    session.add(new_edge)
    await session.commit()

    # Xóa cache tiên quyết sau khi commit thành công
    await prerequisite_engine.invalidate_graph()

    return PrereqEdgeOut(
        course_id=parent_course.id,
        course_code=parent_course.code,
        course_name=parent_course.name,
        prereq_course_id=prereq_course.id,
        prereq_code=prereq_course.code,
        prereq_name=prereq_course.name,
        type=new_edge.type,
        group_no=new_edge.group_no,
    )


async def update_prerequisite(
    session: AsyncSession,
    course_id: int,
    prereq_course_id: int,
    body: PrereqUpdate,
) -> PrereqEdgeOut:
    """Cập nhật loại (AND/OR) hoặc group_no của điều kiện tiên quyết."""
    _validate_prereq_type_and_group(body.type, body.group_no)

    stmt = select(Prerequisite).where(
        Prerequisite.course_id == course_id,
        Prerequisite.prereq_course_id == prereq_course_id,
    )
    edge = (await session.execute(stmt)).scalar_one_or_none()
    if edge is None:
        raise api_error(
            404, "NOT_FOUND", "Không tìm thấy điều kiện tiên quyết cần cập nhật"
        )

    parent_course = await session.get(Course, course_id)
    prereq_course = await session.get(Course, prereq_course_id)

    edge.type = body.type
    edge.group_no = body.group_no
    await session.commit()

    await prerequisite_engine.invalidate_graph()

    return PrereqEdgeOut(
        course_id=parent_course.id,
        course_code=parent_course.code,
        course_name=parent_course.name,
        prereq_course_id=prereq_course.id,
        prereq_code=prereq_course.code,
        prereq_name=prereq_course.name,
        type=edge.type,
        group_no=edge.group_no,
    )


async def delete_prerequisite(
    session: AsyncSession, course_id: int, prereq_course_id: int
) -> None:
    """Xóa một điều kiện tiên quyết và dọn dẹp cache."""
    stmt = select(Prerequisite).where(
        Prerequisite.course_id == course_id,
        Prerequisite.prereq_course_id == prereq_course_id,
    )
    edge = (await session.execute(stmt)).scalar_one_or_none()
    if edge is None:
        raise api_error(404, "NOT_FOUND", "Không tìm thấy điều kiện tiên quyết cần xóa")

    await session.delete(edge)
    await session.commit()

    await prerequisite_engine.invalidate_graph()
