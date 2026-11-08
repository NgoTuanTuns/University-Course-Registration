from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import CurrentUser, require_role
from app.schemas.enrollment import EnrollmentResult, EnrollRequest
from app.services import enrollment_service

router = APIRouter(prefix="/enroll", tags=["enrollment"])
Session = Annotated[AsyncSession, Depends(get_session)]
User = Annotated[CurrentUser, Depends(require_role("student"))]


@router.post(
    "",
    response_model=EnrollmentResult,
    status_code=201,
    responses={200: {"model": EnrollmentResult, "description": "WAITLISTED"}},
)
async def enroll(
    payload: EnrollRequest,
    response: Response,
    session: Session,
    user: User,
    idempotency_key: Annotated[str | None, Header(min_length=1, max_length=128)] = None,
) -> dict:
    result = await enrollment_service.enroll(
        session, user.id, payload.offering_id, idempotency_key
    )
    response.status_code = 200 if result["status"] == "WAITLISTED" else 201
    return result


@router.delete(
    "/{enrollment_id}",
    response_model=EnrollmentResult,
    description="Owner only. Repeating a cancellation succeeds without decrementing twice.",
)
async def cancel(
    enrollment_id: int,
    session: Session,
    user: User,
    version: Annotated[int | None, Query(ge=0)] = None,
) -> dict:
    return await enrollment_service.cancel(session, user.id, enrollment_id, version)
