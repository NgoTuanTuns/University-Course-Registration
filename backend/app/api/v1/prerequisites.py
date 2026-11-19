"""Router mỏng: nhận request, kiểm tra quyền, gọi service, trả kết quả.
Không có logic nghiệp vụ (nằm ở services/prerequisite_engine.py)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_session
from app.core.errors import api_error
from app.core.faculty import course_allowed_for_faculty
from app.core.rate_limit import check_rate_limit
from app.core.security import CurrentUser, get_current_user
from app.models import CompletedCourse, Course, Prerequisite, Student
from app.schemas.prerequisite import (
    OrGroupOut,
    PrereqGraphEdgeOut,
    PrereqGraphNodeOut,
    PrereqGraphResponse,
    PrerequisiteCheckResponse,
    PrerequisiteExplainRequest,
    PrerequisiteExplainResponse,
)
from app.services import prerequisite_engine as engine
from app.services.prerequisite_core import PrerequisiteGraph, evaluate

router = APIRouter(prefix="/prerequisites", tags=["prerequisites"])

_ERROR_RESPONSES = {
    401: {"description": "UNAUTHENTICATED / TOKEN_EXPIRED"},
    403: {"description": "FORBIDDEN: sinh viên hỏi cho người khác"},
    404: {"description": "NOT_FOUND: môn học không tồn tại"},
    429: {"description": "RATE_LIMITED"},
}


async def prereq_rate_limit(
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CurrentUser:
    """Giới hạn tần suất check/explain theo người dùng (chống dò dữ liệu, quá tải)."""
    await check_rate_limit(
        "prereq",
        f"user:{user.id}",
        limit=get_settings().prereq_rate_limit_per_min,
        window_seconds=60,
    )
    return user


def _target_student(user: CurrentUser, student_id: int | None) -> int:
    """Sinh viên chỉ được hỏi cho chính mình; tham số student_id dành cho admin."""
    if student_id is None or student_id == user.id:
        return user.id
    if user.role != "admin":
        raise api_error(403, "FORBIDDEN", "Bạn chỉ được kiểm tra cho chính mình.")
    return student_id


def _not_found() -> Exception:
    return api_error(404, "NOT_FOUND", "Không tìm thấy môn học.")


@router.get(
    "/check", response_model=PrerequisiteCheckResponse, responses=_ERROR_RESPONSES
)
async def check_prerequisites(
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[CurrentUser, Depends(prereq_rate_limit)],
    course_id: int = Query(..., gt=0),
    student_id: int | None = Query(None, gt=0),  # chỉ dành cho admin
) -> PrerequisiteCheckResponse:
    target = _target_student(user, student_id)
    try:
        # eligible=False vẫn là kết quả hợp lệ -> 200 (PREREQ_NOT_MET 422 chỉ ở /enroll)
        res = await engine.check_eligibility(session, target, course_id)
    except engine.CourseNotFoundError:
        raise _not_found() from None

    return PrerequisiteCheckResponse(
        course_id=course_id,
        course_code=res.course_code or "",
        eligible=res.eligible,
        missing_courses=[str(c) for c in res.missing_courses],
        unmet_or_groups=[
            OrGroupOut(group_no=g.group_no, options=[str(o) for o in g.options])
            for g in res.unmet_or_groups
        ],
    )


@router.post(
    "/explain", response_model=PrerequisiteExplainResponse, responses=_ERROR_RESPONSES
)
async def explain_prerequisites(
    body: PrerequisiteExplainRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[CurrentUser, Depends(prereq_rate_limit)],
) -> PrerequisiteExplainResponse:
    target = _target_student(user, body.student_id)
    try:
        return await engine.explain_eligibility(
            session,
            target,
            body.course_id,
            max_items=get_settings().prereq_explain_max_items,
        )
    except engine.CourseNotFoundError:
        raise _not_found() from None


@router.get("/graph", response_model=PrereqGraphResponse)
async def get_prerequisite_graph(
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> PrereqGraphResponse:
    """Trả toàn bộ đồ thị tiên quyết DAG kèm trạng thái COMPLETED / ELIGIBLE / LOCKED cho sinh viên hiện tại."""
    courses = list(
        (await session.execute(select(Course).order_by(Course.code))).scalars().all()
    )
    prereq_rows = list((await session.execute(select(Prerequisite))).scalars().all())
    student = await session.get(Student, user.id)
    student_acc = int(getattr(student, "accumulated_credits", 0) or 0)
    student_faculty = (
        getattr(student, "faculty", None)
        if student and student.role == "student"
        else None
    )
    if student_faculty:
        courses = [
            c for c in courses if course_allowed_for_faculty(c.code, student_faculty)
        ]
    allowed_course_ids = {c.id for c in courses}
    prereq_rows = [
        p
        for p in prereq_rows
        if p.course_id in allowed_course_ids
        and p.prereq_course_id in allowed_course_ids
    ]

    completed_ids: set[int] = set(
        (
            await session.execute(
                select(CompletedCourse.course_id).where(
                    CompletedCourse.student_id == user.id
                )
            )
        )
        .scalars()
        .all()
    )

    code_by_id = {c.id: c.code for c in courses}
    raw_edges = [
        (p.course_id, p.prereq_course_id, p.type, p.group_no) for p in prereq_rows
    ]
    graph = PrerequisiteGraph.from_edges(raw_edges)

    # Tính tầng (level 1..N) dựa trên độ sâu dài nhất trong DAG
    memo_level: dict[int, int] = {}

    def calc_level(cid: int, visiting: set[int]) -> int:
        if cid in memo_level:
            return memo_level[cid]
        if cid in visiting:
            return 1
        visiting.add(cid)
        succs = graph.successors(cid)
        lv = 1 if not succs else 1 + max(calc_level(p, visiting) for p in succs)
        visiting.remove(cid)
        memo_level[cid] = lv
        return lv

    nodes: list[PrereqGraphNodeOut] = []
    for c in courses:
        lv = calc_level(c.id, set())
        and_codes = sorted(
            code_by_id[p] for p in graph.and_prereqs.get(c.id, ()) if p in code_by_id
        )
        or_groups = [
            OrGroupOut(
                group_no=gno,
                options=sorted(code_by_id[o] for o in members if o in code_by_id),
            )
            for gno, members in sorted(graph.or_groups.get(c.id, {}).items())
        ]
        if c.id in completed_ids:
            status_val = "COMPLETED"
            missing_credits = 0
            missing_courses: list[str] = []
        else:
            ev = evaluate(graph, c.id, completed_ids)
            missing_courses = [
                code_by_id[m] for m in ev.missing_courses if m in code_by_id
            ]
            missing_credits = max(0, int(c.min_accumulated_credits) - student_acc)
            status_val = (
                "ELIGIBLE" if (ev.eligible and missing_credits == 0) else "LOCKED"
            )
        nodes.append(
            PrereqGraphNodeOut(
                id=c.id,
                code=c.code,
                name=c.name,
                credits=c.credits,
                min_accumulated_credits=c.min_accumulated_credits,
                level=lv,
                status=status_val,
                missing_credits=missing_credits,
                missing_courses=missing_courses,
                and_prereqs=and_codes,
                or_groups=or_groups,
            )
        )

    edges = [
        PrereqGraphEdgeOut(
            course_id=p.course_id,
            prereq_course_id=p.prereq_course_id,
            type=p.type,  # type: ignore[arg-type]
            group_no=p.group_no,
        )
        for p in prereq_rows
    ]
    return PrereqGraphResponse(
        student_accumulated_credits=student_acc,
        nodes=nodes,
        edges=edges,
    )
