"""Router mỏng: nhận request, gọi service, trả kết quả. Không có logic nghiệp vụ."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

# M4: đã chuẩn hóa import từ app.core.db và app.core.security theo quy ước nhóm.
from app.core.db import get_session
from app.core.security import CurrentUser, get_current_user
from app.schemas.prerequisite import OrGroupOut, PrerequisiteCheckResponse
from app.services import prerequisite_engine as engine

router = APIRouter(prefix="/prerequisites", tags=["prerequisites"])


@router.get("/check", response_model=PrerequisiteCheckResponse)
async def check_prerequisites(
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[CurrentUser, Depends(get_current_user)],
    course_id: int = Query(..., gt=0),
    student_id: int | None = Query(None, gt=0),  # chỉ dành cho admin
):
    target = user.id
    if student_id is not None and student_id != user.id:
        if user.role != "admin":
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "FORBIDDEN",
                    "message": "Bạn chỉ được kiểm tra cho chính mình.",
                },
            )
        target = student_id

    try:
        # eligible=False vẫn là kết quả hợp lệ -> 200 (PREREQ_NOT_MET 422 chỉ ở /enroll)
        res = await engine.check_eligibility(session, target, course_id)
    except engine.CourseNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": "Không tìm thấy môn học."},
        ) from None

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
