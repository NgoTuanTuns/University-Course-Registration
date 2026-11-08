"""Truy cập dữ liệu cho engine tiên quyết (M2). Chỉ ĐỌC, không commit/rollback.

Mọi hàm chạy một số truy vấn CỐ ĐỊNH, không phụ thuộc kích cỡ DAG (tránh N+1):
  - load_graph_snapshot: 2 truy vấn (toàn bộ cạnh + danh mục môn);
  - load_completed: 1 truy vấn theo khóa chính (student_id, course_id);
  - load_subgraph_edges: 1 truy vấn WITH RECURSIVE chỉ lấy đồ thị con (chiến lược
    thay thế, dùng để so sánh trong benchmark khi DAG rất lớn).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CompletedCourse, Course, Prerequisite
from app.services.prerequisite_core import PrerequisiteGraph

Edge = tuple[int, int, str, int]

# Khóa advisory lock của PostgreSQL để tuần tự hóa việc GHI vào DAG (admin/import):
# hai giao dịch cùng thêm cạnh sẽ không thể cùng "thấy" đồ thị cũ rồi cùng tạo vòng.
PREREQ_WRITE_LOCK_KEY = 0x50524551  # "PREQ"


@dataclass(frozen=True)
class CourseLabel:
    code: str
    name: str


@dataclass
class GraphSnapshot:
    """Toàn bộ DAG + danh mục môn (id -> mã, tên), đủ để kiểm tra mà không hỏi lại DB."""

    edges: list[Edge]
    courses: dict[int, CourseLabel]
    _graph: PrerequisiteGraph | None = field(default=None, repr=False, compare=False)

    @property
    def graph(self) -> PrerequisiteGraph:
        if self._graph is None:
            self._graph = PrerequisiteGraph.from_edges(self.edges)
        return self._graph


async def load_edges(session: AsyncSession) -> list[Edge]:
    rows = await session.execute(
        select(
            Prerequisite.course_id,
            Prerequisite.prereq_course_id,
            Prerequisite.type,
            Prerequisite.group_no,
        )
    )
    return [(r[0], r[1], r[2], r[3]) for r in rows.all()]


async def load_course_catalog(session: AsyncSession) -> dict[int, CourseLabel]:
    rows = await session.execute(select(Course.id, Course.code, Course.name))
    return {r[0]: CourseLabel(r[1], r[2]) for r in rows.all()}


async def load_graph_snapshot(session: AsyncSession) -> GraphSnapshot:
    return GraphSnapshot(
        edges=await load_edges(session),
        courses=await load_course_catalog(session),
    )


async def load_completed(session: AsyncSession, student_id: int) -> set[int]:
    rows = await session.execute(
        select(CompletedCourse.course_id).where(
            CompletedCourse.student_id == student_id
        )
    )
    return {r[0] for r in rows.all()}


async def load_course_labels(
    session: AsyncSession, ids: Iterable[int]
) -> dict[int, CourseLabel]:
    wanted = set(ids)
    if not wanted:
        return {}
    rows = await session.execute(
        select(Course.id, Course.code, Course.name).where(Course.id.in_(wanted))
    )
    return {r[0]: CourseLabel(r[1], r[2]) for r in rows.all()}


async def load_course_codes(
    session: AsyncSession, ids: Iterable[int]
) -> dict[int, str]:
    labels = await load_course_labels(session, ids)
    return {cid: label.code for cid, label in labels.items()}


async def load_subgraph_edges(session: AsyncSession, course_id: int) -> list[Edge]:
    """Chỉ lấy các cạnh tới được từ `course_id` bằng một truy vấn WITH RECURSIVE.

    UNION (không phải UNION ALL) loại dòng trùng nên truy vấn luôn dừng, kể cả khi
    dữ liệu lỡ có vòng. Dùng chỉ mục khóa chính (course_id, prereq_course_id).
    """
    p = Prerequisite.__table__
    base = (
        select(p.c.course_id, p.c.prereq_course_id, p.c.type, p.c.group_no)
        .where(p.c.course_id == course_id)
        .cte("prereq_subgraph", recursive=True)
    )
    child = p.alias("child")
    step = select(
        child.c.course_id, child.c.prereq_course_id, child.c.type, child.c.group_no
    ).join(base, child.c.course_id == base.c.prereq_course_id)
    subgraph = base.union(step)
    rows = await session.execute(select(subgraph))
    return [(r[0], r[1], r[2], r[3]) for r in rows.all()]


async def lock_prerequisite_writes(session: AsyncSession) -> None:
    """Khóa giao dịch (tự nhả khi commit/rollback) cho mọi thao tác ghi DAG."""
    await session.execute(select(func.pg_advisory_xact_lock(PREREQ_WRITE_LOCK_KEY)))
