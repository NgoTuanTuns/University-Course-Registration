"""Engine kiểm tra điều kiện tiên quyết (M2 - Tuần 1).

Thiết kế: lõi THUẦN (không đụng DB/Redis) để test độc lập (SR-NF-02).
Phần truy cập DB nằm cuối file và import model theo kiểu lazy, nên lõi
chạy/test được ngay cả khi models của M4 chưa có trên main.

Mô hình: DAG, cạnh X -> Y nghĩa là "X cần Y".
  - type 'AND' (group_no = 0): bắt buộc đã học Y.
  - type 'OR'  (group_no >= 1): các dòng cùng (course, group_no) là 1 nhóm,
    chỉ cần đã học 1 môn trong nhóm.
Ngữ nghĩa bắc cầu (phương án a): môn nằm trong completed thì coi là đủ,
không xét lại tổ tiên của nó. Môn CHƯA học thì mở rộng tiếp tiên quyết của
nó để liệt kê đủ chuỗi cần học.
Tất cả duyệt bằng vòng lặp/hàng đợi, không đệ quy (giới hạn ~1000 của Python).
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field, replace
from typing import Iterable

CourseId = int | str


class PrerequisiteCycleError(Exception):
    """Dữ liệu tiên quyết có vòng lặp. `path` là đường đi của chu trình."""

    def __init__(self, path: list[CourseId]):
        self.path = path
        super().__init__(" -> ".join(str(p) for p in path))


class CourseNotFoundError(Exception):
    """Môn học không tồn tại."""


@dataclass
class PrerequisiteGraph:
    and_prereqs: dict[CourseId, set[CourseId]] = field(default_factory=dict)
    or_groups: dict[CourseId, dict[int, set[CourseId]]] = field(default_factory=dict)

    @classmethod
    def from_edges(
        cls, edges: Iterable[tuple[CourseId, CourseId, str, int]]
    ) -> "PrerequisiteGraph":
        """edges: (course_id, prereq_course_id, type, group_no)."""
        g = cls()
        for course, prereq, kind, group_no in edges:
            if kind == "AND":
                g.and_prereqs.setdefault(course, set()).add(prereq)
            elif kind == "OR":
                if group_no < 1:
                    raise ValueError("Cạnh OR phải có group_no >= 1")
                g.or_groups.setdefault(course, {}).setdefault(group_no, set()).add(prereq)
            else:
                raise ValueError(f"type không hợp lệ: {kind!r}")
        return g

    def successors(self, course: CourseId) -> set[CourseId]:
        """Mọi môn mà `course` cần (cả AND lẫn OR) - dùng cho phát hiện chu trình."""
        out = set(self.and_prereqs.get(course, ()))
        for members in self.or_groups.get(course, {}).values():
            out |= members
        return out

    def nodes(self) -> set[CourseId]:
        nodes: set[CourseId] = set(self.and_prereqs) | set(self.or_groups)
        for c in list(nodes):
            nodes |= self.successors(c)
        return nodes


@dataclass
class OrGroupResult:
    group_no: int
    options: list[CourseId]


@dataclass
class EligibilityResult:
    course_id: CourseId
    eligible: bool
    missing_courses: list[CourseId] = field(default_factory=list)
    unmet_or_groups: list[OrGroupResult] = field(default_factory=list)
    course_code: str | None = None


def evaluate(
    graph: PrerequisiteGraph, course_id: CourseId, completed: set[CourseId]
) -> EligibilityResult:
    """Hàm thuần: sinh viên có `completed` thì đủ điều kiện học `course_id` chưa."""
    # Môn thiếu (AND) = BFS từ môn đích. `seen` là memoization: môn xuất hiện ở
    # nhiều nhánh (hình kim cương) chỉ xử lý 1 lần -> O(V + E), không bùng nổ.
    missing: list[CourseId] = []
    seen: set[CourseId] = set()
    queue: deque[CourseId] = deque()

    def push_unmet(parent: CourseId) -> None:
        # sorted(key=str) để kết quả xác định (test ổn định, UI không "nhảy")
        for p in sorted(graph.and_prereqs.get(parent, ()), key=str):
            if p not in completed and p not in seen:
                queue.append(p)

    push_unmet(course_id)
    while queue:
        cur = queue.popleft()
        if cur in seen:
            continue
        seen.add(cur)
        missing.append(cur)
        # Môn chưa học -> tiên quyết của nó cũng phải học (bắc cầu).
        # Môn đã học thì không đi tiếp (phương án a).
        push_unmet(cur)

    # Nhóm OR của môn đích: đạt khi có ÍT NHẤT 1 môn đã học.
    # Nhóm chưa đạt đưa vào unmet_or_groups, KHÔNG gộp vào missing_courses.
    unmet: list[OrGroupResult] = []
    for group_no, members in sorted(graph.or_groups.get(course_id, {}).items()):
        if not (members & completed):
            unmet.append(OrGroupResult(group_no, sorted(members, key=str)))

    return EligibilityResult(
        course_id=course_id,
        eligible=not missing and not unmet,
        missing_courses=missing,
        unmet_or_groups=unmet,
    )


def find_cycle(graph: PrerequisiteGraph) -> list[CourseId] | None:
    """DFS 3 màu (vòng lặp). Trả đường đi chu trình [a, b, ..., a] hoặc None."""
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[CourseId, int] = {}
    for start in sorted(graph.nodes(), key=str):
        if color.get(start, WHITE) != WHITE:
            continue
        color[start] = GRAY
        path = [start]
        stack = [iter(sorted(graph.successors(start), key=str))]
        while stack:
            nxt = next(stack[-1], None)
            if nxt is None:  # hết con -> đóng node
                color[path.pop()] = BLACK
                stack.pop()
                continue
            state = color.get(nxt, WHITE)
            if state == GRAY:  # gặp node đang trong đường đi hiện tại -> có vòng
                return path[path.index(nxt):] + [nxt]
            if state == WHITE:
                color[nxt] = GRAY
                path.append(nxt)
                stack.append(iter(sorted(graph.successors(nxt), key=str)))
    return None


def would_create_cycle(
    graph: PrerequisiteGraph, course_id: CourseId, prereq_course_id: CourseId
) -> list[CourseId] | None:
    """Thêm cạnh 'course_id cần prereq_course_id' có tạo vòng không?

    Có vòng khi course_id đã TỚI ĐƯỢC từ prereq_course_id theo chiều "cần".
    Trả đường đi vòng [course, prereq, ..., course] hoặc None.
    """
    if course_id == prereq_course_id:
        return [course_id, course_id]
    parent: dict[CourseId, CourseId | None] = {prereq_course_id: None}
    queue: deque[CourseId] = deque([prereq_course_id])
    while queue:
        cur = queue.popleft()
        for nxt in sorted(graph.successors(cur), key=str):
            if nxt in parent:
                continue
            parent[nxt] = cur
            if nxt == course_id:
                path = [nxt]
                while parent[path[-1]] is not None:
                    path.append(parent[path[-1]])  # type: ignore[arg-type]
                path.reverse()  # prereq ... course
                return [course_id] + path
            queue.append(nxt)
    return None


def assert_acyclic(edges: Iterable[tuple[CourseId, CourseId, str, int]]) -> None:
    """Dùng cho seed/import (M4): ném PrerequisiteCycleError nếu dữ liệu có vòng."""
    cycle = find_cycle(PrerequisiteGraph.from_edges(edges))
    if cycle:
        raise PrerequisiteCycleError(cycle)


# ----------------------------------------------------------------------------
# Truy cập dữ liệu (mỏng). Import model lazy để lõi ở trên không phụ thuộc M4.
# TODO(M4): đối chiếu tên model/cột với models/ thật.
# ----------------------------------------------------------------------------
async def load_edges(session) -> list[tuple[int, int, str, int]]:
    from sqlalchemy import select
    from app.models.prerequisite import Prerequisite

    rows = await session.execute(
        select(
            Prerequisite.course_id,
            Prerequisite.prereq_course_id,
            Prerequisite.type,
            Prerequisite.group_no,
        )
    )
    return [tuple(r) for r in rows.all()]


async def load_completed(session, student_id: int) -> set[int]:
    from sqlalchemy import select
    from app.models.completed_course import CompletedCourse

    rows = await session.execute(
        select(CompletedCourse.course_id).where(CompletedCourse.student_id == student_id)
    )
    return {r[0] for r in rows.all()}


async def load_course_codes(session, ids: set[int]) -> dict[int, str]:
    from sqlalchemy import select
    from app.models.course import Course

    if not ids:
        return {}
    rows = await session.execute(select(Course.id, Course.code).where(Course.id.in_(ids)))
    return {r[0]: r[1] for r in rows.all()}


async def check_eligibility(session, student_id: int, course_id: int) -> EligibilityResult:
    """Giao diện cho M3 gọi trong /enroll. CHỈ ĐỌC, dùng chung session của M3
    (không commit/rollback). missing_courses là MÃ MÔN (vd "INT131")."""
    graph = PrerequisiteGraph.from_edges(await load_edges(session))
    completed = await load_completed(session, student_id)

    codes = await load_course_codes(session, {course_id})
    if course_id not in codes:
        raise CourseNotFoundError(f"Không tìm thấy môn id={course_id}")

    raw = evaluate(graph, course_id, completed)
    need = set(raw.missing_courses)
    for grp in raw.unmet_or_groups:
        need |= set(grp.options)
    codes |= await load_course_codes(session, need)  # 1 truy vấn cho mọi mã cần dịch

    return replace(
        raw,
        course_code=codes[course_id],
        missing_courses=[codes[c] for c in raw.missing_courses],
        unmet_or_groups=[
            OrGroupResult(g.group_no, [codes[c] for c in g.options])
            for g in raw.unmet_or_groups
        ],
    )
