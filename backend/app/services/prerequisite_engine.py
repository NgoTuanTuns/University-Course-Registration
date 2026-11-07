"""Engine kiểm tra điều kiện tiên quyết (M2) — điểm vào công khai cho cả nhóm.

Chia thành 3 phần, file này chỉ ghép chúng lại:
  prerequisite_core.py        lõi THUẦN (DAG, evaluate, explain, chu trình) - test độc lập
  prerequisite_repository.py  đọc DB với số truy vấn cố định (không N+1)
  prerequisite_cache.py       cache Redis + invalidation

Dùng cho người khác:
  M3 (/enroll):  await check_eligibility(session, student_id, course_id)
                 -> EligibilityResult (missing_courses là MÃ MÔN). Chỉ đọc, dùng chung
                 session của M3, không commit/rollback.
  M4 (admin):    await ensure_edge_allowed(session, course_id, prereq_course_id)
                 trước khi ghi cạnh; bắt PrerequisiteCycleError -> raise cycle_http_error(e).
                 Sau commit: await invalidate_graph(). Seed/import: assert_acyclic(edges).
                 completed_courses của một sinh viên đổi: await invalidate_student(id).

Số truy vấn DB cho mỗi lần check (đo bằng test):
  cache kết quả trúng                 -> 0
  trượt, đồ thị đã có trong Redis     -> 1 (completed_courses)
  trượt, đồ thị chưa có / Redis tắt   -> 3 (cạnh, danh mục môn, completed_courses)
Không tăng theo kích cỡ DAG.
"""

from __future__ import annotations

from collections.abc import Iterable

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import api_error
from app.schemas.prerequisite import (
    MissingCourseOut,
    OrGroupExplainOut,
    OrOptionOut,
    PrerequisiteExplainResponse,
)
from app.services import prerequisite_cache as cache
from app.services import prerequisite_repository as repo
from app.services.prerequisite_cache import (
    get_metrics,
    invalidate_graph,
    invalidate_student,
)
from app.services.prerequisite_core import (
    KIND_DIRECT,
    KIND_TRANSITIVE,
    CourseId,
    CourseNotFoundError,
    EligibilityResult,
    Explanation,
    MissingCourse,
    OrGroupExplanation,
    OrGroupResult,
    OrOption,
    PrerequisiteCycleError,
    PrerequisiteGraph,
    assert_acyclic,
    evaluate,
    explain,
    find_cycle,
    suggested_order,
    would_create_cycle,
)
from app.services.prerequisite_repository import (
    CourseLabel,
    GraphSnapshot,
    load_completed,
    load_course_codes,
    load_edges,
)

__all__ = [
    "KIND_DIRECT",
    "KIND_TRANSITIVE",
    "CourseId",
    "CourseLabel",
    "CourseNotFoundError",
    "EligibilityResult",
    "Explanation",
    "GraphSnapshot",
    "MissingCourse",
    "OrGroupExplanation",
    "OrGroupResult",
    "OrOption",
    "PrerequisiteCycleError",
    "PrerequisiteGraph",
    "assert_acyclic",
    "check_eligibility",
    "check_eligibility_many",
    "cycle_http_error",
    "ensure_edge_allowed",
    "evaluate",
    "explain",
    "explain_eligibility",
    "find_cycle",
    "get_metrics",
    "invalidate_graph",
    "invalidate_student",
    "load_completed",
    "load_course_codes",
    "load_edges",
    "suggested_order",
    "warm_graph_cache",
    "would_create_cycle",
]


# --------------------------------------------------------------------- đồ thị
async def _load_and_cache_graph(
    session: AsyncSession, generation: str
) -> GraphSnapshot:
    """Đồ thị chưa có trong Redis: chỉ MỘT request dựng lại (SET NX), các request
    khác chờ ngắn rồi đọc lại -> tránh "cache stampede" khi khóa đồ thị vừa bị xóa."""
    token = await cache.try_acquire_graph_lock()
    if token is None:
        waited = await cache.wait_for_graph()
        if waited is not None:
            return waited
        snapshot = await repo.load_graph_snapshot(session)
        await cache.store_graph(snapshot, generation)
        return snapshot
    try:
        snapshot = await repo.load_graph_snapshot(session)
        await cache.store_graph(snapshot, generation)
        return snapshot
    finally:
        await cache.release_graph_lock(token)


async def _graph_snapshot(
    session: AsyncSession, generation: str | None
) -> GraphSnapshot:
    """generation=None nghĩa là không dùng cache (Redis lỗi hoặc gọi không cache)."""
    if generation is None:
        return await repo.load_graph_snapshot(session)
    cached = await cache.read_graph()
    if cached is not None:
        return cached
    return await _load_and_cache_graph(session, generation)


async def warm_graph_cache(session: AsyncSession) -> bool:
    """Làm nóng đồ thị khi khởi động (FastAPI lifespan). Trả True nếu đồ thị đã sẵn."""
    generation = await cache.read_generation()
    if generation is None:
        return False
    if await cache.read_graph() is not None:
        return True
    await _load_and_cache_graph(session, generation)
    return True


async def _labels_for(
    session: AsyncSession, snapshot: GraphSnapshot, ids: Iterable[CourseId]
) -> dict[int, CourseLabel]:
    """Nhãn (mã, tên) cho các id; chỉ hỏi DB với id không có trong danh mục đã cache
    (ví dụ môn vừa được tạo sau khi đồ thị được dựng)."""
    wanted = {int(c) for c in ids}
    labels = {c: snapshot.courses[c] for c in wanted if c in snapshot.courses}
    unknown = wanted - labels.keys()
    if unknown:
        labels |= await repo.load_course_labels(session, unknown)
    return labels


# --------------------------------------------------------------------- check
def _to_codes(
    raw: EligibilityResult, labels: dict[int, CourseLabel]
) -> EligibilityResult:
    def code(c: CourseId) -> str:
        return labels[int(c)].code

    return EligibilityResult(
        course_id=raw.course_id,
        course_code=code(raw.course_id),
        eligible=raw.eligible,
        missing_courses=[code(c) for c in raw.missing_courses],
        unmet_or_groups=[
            OrGroupResult(g.group_no, [code(o) for o in g.options])
            for g in raw.unmet_or_groups
        ],
    )


def _ids_in(raw: EligibilityResult) -> set[CourseId]:
    ids = {raw.course_id, *raw.missing_courses}
    for g in raw.unmet_or_groups:
        ids.update(g.options)
    return ids


async def check_eligibility_many(
    session: AsyncSession,
    student_id: int,
    course_ids: Iterable[int],
    *,
    use_cache: bool = True,
) -> dict[int, EligibilityResult]:
    """Kiểm tra nhiều môn cho MỘT sinh viên: một lần tra Redis (MGET trong Lua),
    phần trượt dùng chung một đồ thị và một lần đọc completed_courses.
    Môn không tồn tại không có trong kết quả."""
    ids = [int(c) for c in dict.fromkeys(course_ids)]
    lookup = (
        await cache.read_results(student_id, ids)
        if use_cache
        else cache.CachedLookup(results={}, generation=None)
    )
    pending = [c for c in ids if c not in lookup.results]
    if not pending:
        return {c: lookup.results[c] for c in ids}

    snapshot = await _graph_snapshot(session, lookup.generation)
    existing = await _labels_for(session, snapshot, pending)
    pending = [c for c in pending if c in existing]
    completed = await repo.load_completed(session, student_id)

    raws = [evaluate(snapshot.graph, c, completed) for c in pending]
    needed = set().union(*(_ids_in(r) for r in raws)) if raws else set()
    labels = existing | await _labels_for(session, snapshot, needed - existing.keys())
    fresh = [_to_codes(r, labels) for r in raws]
    await cache.store_results(student_id, fresh, lookup.generation)

    merged = lookup.results | {int(r.course_id): r for r in fresh}
    return {c: merged[c] for c in ids if c in merged}


async def check_eligibility(
    session: AsyncSession, student_id: int, course_id: int, *, use_cache: bool = True
) -> EligibilityResult:
    """Giao diện cho M3 gọi trong /enroll. CHỈ ĐỌC, dùng chung session của M3
    (không commit/rollback). missing_courses là MÃ MÔN (vd "INT131").
    Môn không tồn tại -> CourseNotFoundError."""
    results = await check_eligibility_many(
        session, student_id, [course_id], use_cache=use_cache
    )
    if course_id not in results:
        raise CourseNotFoundError(f"Không tìm thấy môn id={course_id}")
    return results[course_id]


# --------------------------------------------------------------------- explain
def _render_explanation(
    exp: Explanation, labels: dict[int, CourseLabel]
) -> PrerequisiteExplainResponse:
    """Chỉ trả mã + tên môn, không lộ id nội bộ hay thuật ngữ đồ thị (UR-NF-02)."""

    def code(c: CourseId) -> str:
        return labels[int(c)].code

    return PrerequisiteExplainResponse(
        course_id=int(exp.course_id),
        course_code=code(exp.course_id),
        course_name=labels[int(exp.course_id)].name,
        eligible=exp.eligible,
        missing=[
            MissingCourseOut(
                course_code=code(m.course_id),
                course_name=labels[int(m.course_id)].name,
                kind=m.kind,
                required_by=code(m.required_by),
                path=[code(c) for c in m.path],
            )
            for m in exp.missing
        ],
        unmet_or_groups=[
            OrGroupExplainOut(
                group_no=g.group_no,
                required_by=code(g.required_by),
                options=[
                    OrOptionOut(
                        course_code=code(o.course_id),
                        course_name=labels[int(o.course_id)].name,
                        can_take_now=o.can_take_now,
                        missing_courses=[code(c) for c in o.missing_courses],
                    )
                    for o in g.options
                ],
            )
            for g in exp.unmet_or_groups
        ],
        suggested_order=[code(c) for c in exp.suggested_order],
        total_missing=exp.total_missing,
        truncated=exp.truncated,
    )


def _ids_in_explanation(exp: Explanation) -> set[CourseId]:
    ids: set[CourseId] = {exp.course_id, *exp.suggested_order}
    for m in exp.missing:
        ids.update(m.path)
    for g in exp.unmet_or_groups:
        ids.add(g.required_by)
        for o in g.options:
            ids.add(o.course_id)
            ids.update(o.missing_courses)
    return ids


async def explain_eligibility(
    session: AsyncSession, student_id: int, course_id: int, *, max_items: int
) -> PrerequisiteExplainResponse:
    """Giải thích có cấu trúc cho M1. Dùng chung cache đồ thị; kết quả explain
    không cache riêng (ít gọi hơn check, vẫn chỉ 1 truy vấn khi đồ thị đã cache)."""
    snapshot = await _graph_snapshot(session, await cache.read_generation())
    if not await _labels_for(session, snapshot, [course_id]):
        raise CourseNotFoundError(f"Không tìm thấy môn id={course_id}")
    completed = await repo.load_completed(session, student_id)
    exp = explain(snapshot.graph, course_id, completed, max_items=max_items)
    labels = await _labels_for(session, snapshot, _ids_in_explanation(exp))
    return _render_explanation(exp, labels)


# --------------------------------------------------------------------- chặn chu trình
async def ensure_edge_allowed(
    session: AsyncSession,
    course_id: int,
    prereq_course_id: int,
    *,
    lock: bool = True,
) -> None:
    """Gọi TRƯỚC khi ghi cạnh "course_id cần prereq_course_id" (M4, /admin/prereqs).

    Đọc DAG trực tiếp từ DB trong CÙNG giao dịch (không dùng cache) để quyết định
    dựa trên dữ liệu mới nhất. lock=True giữ advisory lock tới khi giao dịch kết thúc,
    nên hai admin cùng thêm cạnh không thể cùng tạo vòng.
    Có vòng -> PrerequisiteCycleError(path) với path là MÃ MÔN, ví dụ
    ["INT101", "INT131", "INT101"].
    """
    if lock:
        await repo.lock_prerequisite_writes(session)
    graph = PrerequisiteGraph.from_edges(await repo.load_edges(session))
    path = would_create_cycle(graph, course_id, prereq_course_id)
    if path is None:
        return
    labels = await repo.load_course_labels(session, path)
    raise PrerequisiteCycleError(
        [labels[c].code if c in labels else str(c) for c in path]
    )


def cycle_http_error(exc: PrerequisiteCycleError) -> HTTPException:
    """Lỗi API thống nhất cho dữ liệu tạo vòng: 422 PREREQ_CYCLE kèm cycle_path."""
    chain = " → ".join(str(c) for c in exc.path)
    return api_error(
        422,
        "PREREQ_CYCLE",
        f"Điều kiện tiên quyết này tạo vòng lặp: {chain}",
        cycle_path=[str(c) for c in exc.path],
    )
