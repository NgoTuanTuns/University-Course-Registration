"""Router mỏng: nhận request, kiểm tra quyền, gọi service, trả kết quả.
Không có logic nghiệp vụ (nằm ở services/prerequisite_engine.py)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_session
from app.core.errors import api_error
from app.core.rate_limit import check_rate_limit
from app.core.security import CurrentUser, get_current_user
from app.schemas.prerequisite import (
    OrGroupOut,
    PrerequisiteCheckResponse,
    PrerequisiteExplainRequest,
    PrerequisiteExplainResponse,
)
from app.services import prerequisite_engine as engine

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
