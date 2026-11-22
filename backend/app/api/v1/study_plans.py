"""API Đăng ký Kế hoạch Học tập (ĐKKHHT) cho sinh viên và chốt mở lớp cho Admin."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import CurrentUser, get_current_user, require_role
from app.schemas.study_plan import (
    AdminFinalizeStudyPlansRequest,
    AdminFinalizeStudyPlansResponse,
    AdminStudyPlanSummaryResponse,
    StudyPlanCreateRequest,
    StudyPlanResponse,
)
from app.services.study_plan_service import (
    add_course_to_study_plan,
    finalize_study_plan_openings,
    get_admin_study_plan_summary,
    get_student_study_plan,
    remove_course_from_study_plan,
)

router = APIRouter(tags=["study-plans"])


@router.get("/study-plans", response_model=StudyPlanResponse)
async def get_my_study_plan(
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[CurrentUser, Depends(get_current_user)],
    term: Annotated[str | None, Query(pattern=r"^\d{4}-[1-3]$")] = None,
) -> dict:
    return await get_student_study_plan(session, user.id, term=term)


@router.post("/study-plans", response_model=StudyPlanResponse, status_code=201)
async def add_to_my_study_plan(
    body: StudyPlanCreateRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict:
    return await add_course_to_study_plan(session, user.id, body.course_id, body.term)


@router.delete("/study-plans/{plan_id}", response_model=StudyPlanResponse)
async def remove_from_my_study_plan(
    plan_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict:
    return await remove_course_from_study_plan(session, user.id, plan_id)


@router.get(
    "/admin/study-plans/summary",
    response_model=AdminStudyPlanSummaryResponse,
)
async def admin_study_plan_summary(
    session: Annotated[AsyncSession, Depends(get_session)],
    _admin: Annotated[CurrentUser, Depends(require_role("admin"))],
    term: Annotated[str | None, Query(pattern=r"^\d{4}-[1-3]$")] = None,
    status: Annotated[
        str | None, Query(pattern=r"^(ALL|PENDING|OPENED|NOT_OPENED)$")
    ] = None,
) -> dict:
    return await get_admin_study_plan_summary(session, term=term, status_filter=status)


@router.post(
    "/admin/study-plans/finalize",
    response_model=AdminFinalizeStudyPlansResponse,
)
async def admin_finalize_study_plans(
    body: AdminFinalizeStudyPlansRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    _admin: Annotated[CurrentUser, Depends(require_role("admin"))],
) -> dict:
    return await finalize_study_plan_openings(
        session, term=body.term, min_students_to_open=body.min_students_to_open
    )
