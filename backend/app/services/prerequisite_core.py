"""Lõi THUẦN của engine tiên quyết (M2): không đụng DB/Redis, test độc lập (SR-NF-02).

Mô hình: DAG, cạnh X -> Y nghĩa là "X cần Y".
  - type 'AND' (group_no = 0): bắt buộc đã học Y.
  - type 'OR'  (group_no >= 1): các dòng cùng (course, group_no) là 1 nhóm,
    chỉ cần đã học 1 môn trong nhóm.
Ngữ nghĩa bắc cầu (D04, phương án a): môn nằm trong `completed` thì coi là đủ,
không xét lại tổ tiên của nó. Môn CHƯA học thì mở rộng tiếp tiên quyết AND của
nó để liệt kê đủ chuỗi cần học.

Mọi phép duyệt dùng vòng lặp/hàng đợi, không đệ quy (giới hạn ~1000 của Python),
và có tập `seen` (memoization) để môn xuất hiện ở nhiều nhánh (kim cương) chỉ
được xử lý một lần -> O(V + E) trên đồ thị con tới được từ môn đang xét.
"""

from __future__ import annotations

import heapq
from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass, field

CourseId = int | str
Edge = tuple[CourseId, CourseId, str, int]

KIND_DIRECT = "DIRECT"
KIND_TRANSITIVE = "TRANSITIVE"


class PrerequisiteCycleError(Exception):
    """Dữ liệu tiên quyết có vòng lặp. `path` là đường đi của chu trình."""

    def __init__(self, path: list[CourseId]):
        self.path = path
        super().__init__(" -> ".join(str(p) for p in path))


class CourseNotFoundError(Exception):
    """Môn học không tồn tại."""


def _key(value: CourseId) -> str:
    """Khóa sắp xếp xác định cho cả id số lẫn mã chuỗi (test ổn định, UI không "nhảy")."""
    return str(value)


@dataclass
class PrerequisiteGraph:
    and_prereqs: dict[CourseId, set[CourseId]] = field(default_factory=dict)
    or_groups: dict[CourseId, dict[int, set[CourseId]]] = field(default_factory=dict)
    # Bản đã sắp xếp của and_prereqs, tính một lần khi cần (đồ thị coi như bất biến
    # sau khi dựng) để BFS không phải sort lại ở mỗi lần duyệt.
    _sorted_and: dict[CourseId, tuple[CourseId, ...]] = field(
        default_factory=dict, repr=False, compare=False
    )

    def ordered_and(self, course: CourseId) -> tuple[CourseId, ...]:
        cached = self._sorted_and.get(course)
        if cached is None:
            cached = tuple(sorted(self.and_prereqs.get(course, ()), key=_key))
            self._sorted_and[course] = cached
        return cached

    @classmethod
    def from_edges(cls, edges: Iterable[Edge]) -> PrerequisiteGraph:
        """edges: (course_id, prereq_course_id, type, group_no)."""
        g = cls()
        for course, prereq, kind, group_no in edges:
            if kind == "AND":
                g.and_prereqs.setdefault(course, set()).add(prereq)
            elif kind == "OR":
                if group_no < 1:
                    raise ValueError("Cạnh OR phải có group_no >= 1")
                g.or_groups.setdefault(course, {}).setdefault(group_no, set()).add(
                    prereq
                )
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


@dataclass
class MissingCourse:
    """Một môn bắt buộc còn thiếu, kèm MỘT đường suy diễn tiêu biểu (ngắn nhất)."""

    course_id: CourseId
    kind: str  # KIND_DIRECT | KIND_TRANSITIVE
    required_by: CourseId
    path: list[CourseId]  # từ môn đang xét tới môn thiếu


@dataclass
class OrOption:
    course_id: CourseId
    can_take_now: bool
    missing_courses: list[CourseId] = field(default_factory=list)


@dataclass
class OrGroupExplanation:
    group_no: int
    required_by: CourseId
    options: list[OrOption]


@dataclass
class Explanation:
    course_id: CourseId
    eligible: bool
    missing: list[MissingCourse]
    unmet_or_groups: list[OrGroupExplanation]
    suggested_order: list[CourseId]
    total_missing: int
    total_unmet_or_groups: int

    @property
    def truncated(self) -> bool:
        return (
            len(self.missing) < self.total_missing
            or len(self.unmet_or_groups) < self.total_unmet_or_groups
        )


def _collect_missing(
    graph: PrerequisiteGraph, course_id: CourseId, completed: set[CourseId]
) -> tuple[list[CourseId], dict[CourseId, CourseId]]:
    """BFS theo cạnh AND từ môn đích, chỉ đi qua các môn CHƯA học.

    Trả (order, parent):
      - order: các môn thiếu theo thứ tự phát hiện (gần môn đích trước);
      - parent[x]: môn đã "đòi" x lần đầu. Vì BFS mở rộng theo từng tầng nên
        chuỗi parent cho ra đường đi NGẮN NHẤT từ môn đích tới x.
    `seen` vừa chống xử lý lặp ở hình kim cương vừa chặn vòng nếu dữ liệu hỏng.
    """
    order: list[CourseId] = []
    parent: dict[CourseId, CourseId] = {}
    seen: set[CourseId] = {course_id}
    queue: deque[CourseId] = deque([course_id])
    while queue:
        cur = queue.popleft()
        for p in graph.ordered_and(cur):
            # Môn đã học -> đủ, không đi tiếp (bắc cầu phương án a).
            if p in completed or p in seen:
                continue
            seen.add(p)
            parent[p] = cur
            order.append(p)
            queue.append(p)
    return order, parent


def _unmet_groups(
    graph: PrerequisiteGraph, course_id: CourseId, completed: set[CourseId]
) -> list[tuple[int, list[CourseId]]]:
    """Các nhóm OR của MỘT môn chưa có môn nào đã học, theo group_no tăng dần."""
    out: list[tuple[int, list[CourseId]]] = []
    for group_no, members in sorted(graph.or_groups.get(course_id, {}).items()):
        if not (members & completed):
            out.append((group_no, sorted(members, key=_key)))
    return out


def evaluate(
    graph: PrerequisiteGraph, course_id: CourseId, completed: set[CourseId]
) -> EligibilityResult:
    """Hàm thuần: sinh viên có `completed` thì đủ điều kiện học `course_id` chưa.

    `missing_courses` gồm môn AND trực tiếp còn thiếu và toàn bộ chuỗi bắc cầu.
    `unmet_or_groups` chỉ gồm nhóm OR của chính môn đích, KHÔNG gộp vào
    `missing_courses` (không bắt buộc học cả nhóm).
    """
    missing, _ = _collect_missing(graph, course_id, completed)
    unmet = [
        OrGroupResult(group_no, options)
        for group_no, options in _unmet_groups(graph, course_id, completed)
    ]
    return EligibilityResult(
        course_id=course_id,
        eligible=not missing and not unmet,
        missing_courses=missing,
        unmet_or_groups=unmet,
    )


def _path_to(
    course_id: CourseId, target: CourseId, parent: dict[CourseId, CourseId]
) -> list[CourseId]:
    path = [target]
    while path[-1] != course_id:
        path.append(parent[path[-1]])
    path.reverse()
    return path


def suggested_order(
    graph: PrerequisiteGraph, missing: list[CourseId]
) -> list[CourseId]:
    """Thứ tự học gợi ý: topological sort (Kahn) trên tập môn thiếu.

    Môn nào có tiên quyết AND cũng đang thiếu thì đứng SAU tiên quyết đó.
    Khi nhiều môn cùng sẵn sàng, chọn theo khóa sắp xếp để kết quả xác định.
    """
    missing_set = set(missing)
    indegree = {c: 0 for c in missing}
    dependents: dict[CourseId, list[CourseId]] = {c: [] for c in missing}
    for c in missing:
        for p in graph.and_prereqs.get(c, ()):
            if p in missing_set:
                indegree[c] += 1
                dependents[p].append(c)
    heap = [(_key(c), c) for c in missing if indegree[c] == 0]
    heapq.heapify(heap)
    out: list[CourseId] = []
    while heap:
        _, cur = heapq.heappop(heap)
        out.append(cur)
        for d in dependents[cur]:
            indegree[d] -= 1
            if indegree[d] == 0:
                heapq.heappush(heap, (_key(d), d))
    return out


def _explain_groups(
    graph: PrerequisiteGraph,
    owners: list[CourseId],
    completed: set[CourseId],
    limit: int | None,
) -> tuple[list[OrGroupExplanation], int]:
    """Nhóm OR chưa thỏa của môn đích và của từng môn thiếu (theo thứ tự `owners`).

    Với mỗi lựa chọn trong nhóm, tính `can_take_now` (đủ điều kiện học ngay chưa)
    để người dùng biết nên chọn nhánh nào. Kết quả evaluate của một lựa chọn được
    nhớ lại vì cùng một môn có thể nằm trong nhiều nhóm.
    """
    memo: dict[CourseId, EligibilityResult] = {}
    groups: list[OrGroupExplanation] = []
    total = 0
    for owner in owners:
        for group_no, options in _unmet_groups(graph, owner, completed):
            total += 1
            if limit is not None and len(groups) >= limit:
                continue
            rendered = []
            for option in options:
                if option not in memo:
                    memo[option] = evaluate(graph, option, completed)
                res = memo[option]
                rendered.append(
                    OrOption(option, res.eligible, res.missing_courses[:limit])
                )
            groups.append(OrGroupExplanation(group_no, owner, rendered))
    return groups, total


def explain(
    graph: PrerequisiteGraph,
    course_id: CourseId,
    completed: set[CourseId],
    max_items: int | None = None,
) -> Explanation:
    """Giải thích vì sao chưa đủ điều kiện và cần học gì.

    - missing: môn bắt buộc còn thiếu, mỗi môn MỘT đường đi ngắn nhất (không liệt
      kê mọi đường: số đường trong DAG có thể tăng theo cấp số nhân).
    - unmet_or_groups: nhóm OR chưa thỏa của môn đích VÀ của các môn còn thiếu
      (môn thiếu cũng phải đủ điều kiện mới học được), kèm `required_by`.
    - suggested_order: thứ tự học gợi ý cho các môn bắt buộc còn thiếu.
    - max_items: giới hạn số phần tử trả về để phản hồi không khổng lồ; tổng
      thật nằm ở total_missing / total_unmet_or_groups.
    """
    order, parent = _collect_missing(graph, course_id, completed)
    shown = order if max_items is None else order[:max_items]
    missing = [
        MissingCourse(
            course_id=c,
            kind=KIND_DIRECT if parent[c] == course_id else KIND_TRANSITIVE,
            required_by=parent[c],
            path=_path_to(course_id, c, parent),
        )
        for c in shown
    ]
    groups, total_groups = _explain_groups(
        graph, [course_id, *order], completed, max_items
    )
    plan = suggested_order(graph, order)
    return Explanation(
        course_id=course_id,
        eligible=not order and total_groups == 0,
        missing=missing,
        unmet_or_groups=groups,
        suggested_order=plan if max_items is None else plan[:max_items],
        total_missing=len(order),
        total_unmet_or_groups=total_groups,
    )


def find_cycle(graph: PrerequisiteGraph) -> list[CourseId] | None:
    """DFS 3 màu (vòng lặp). Trả đường đi chu trình [a, b, ..., a] hoặc None.

    WHITE = chưa thăm, GRAY = đang nằm trên đường đi hiện tại, BLACK = đã xong.
    Gặp lại một đỉnh GRAY nghĩa là quay về tổ tiên trên đường đi -> có vòng.
    """
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[CourseId, int] = {}
    for start in sorted(graph.nodes(), key=_key):
        if color.get(start, WHITE) != WHITE:
            continue
        color[start] = GRAY
        path = [start]
        stack = [iter(sorted(graph.successors(start), key=_key))]
        while stack:
            nxt = next(stack[-1], None)
            if nxt is None:  # hết con -> đóng node
                color[path.pop()] = BLACK
                stack.pop()
                continue
            state = color.get(nxt, WHITE)
            if state == GRAY:  # gặp node đang trong đường đi hiện tại -> có vòng
                return path[path.index(nxt) :] + [nxt]
            if state == WHITE:
                color[nxt] = GRAY
                path.append(nxt)
                stack.append(iter(sorted(graph.successors(nxt), key=_key)))
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
        for nxt in sorted(graph.successors(cur), key=_key):
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


def assert_acyclic(edges: Iterable[Edge]) -> None:
    """Dùng cho seed/import (M4): ném PrerequisiteCycleError nếu dữ liệu có vòng."""
    cycle = find_cycle(PrerequisiteGraph.from_edges(edges))
    if cycle:
        raise PrerequisiteCycleError(cycle)
