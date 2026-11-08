from datetime import time
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import api_error
from app.core.security import CurrentUser, get_current_user
from app.schemas.enrollment import CoursePage
from app.services.enrollment_queries import search_courses

router = APIRouter(prefix="/courses", tags=["courses"])


@router.get(
    "",
    response_model=CoursePage,
    description="A time filter matches at least one meeting on day fully contained in [from, to]. Latest term by default.",
)
async def courses(
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[CurrentUser, Depends(get_current_user)],
    term: Annotated[str | None, Query(pattern=r"^\d{4}-[1-3]$")] = None,
    q: Annotated[str | None, Query(max_length=200)] = None,
    section: Annotated[str | None, Query(max_length=10)] = None,
    credits: Annotated[int | None, Query(ge=1, le=10)] = None,
    instructor: Annotated[str | None, Query(max_length=150)] = None,
    day: Annotated[int | None, Query(ge=1, le=7)] = None,
    from_time: Annotated[time | None, Query(alias="from")] = None,
    to_time: Annotated[time | None, Query(alias="to")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict:
    if from_time and to_time and from_time >= to_time:
        raise api_error(422, "VALIDATION_ERROR", "from phải nhỏ hơn to")
    if any(
        value and (value.second or value.microsecond or value.tzinfo)
        for value in (from_time, to_time)
    ):
        raise api_error(
            422, "VALIDATION_ERROR", "Giờ phải ở dạng HH:MM, không có múi giờ"
        )
    return await search_courses(
        session,
        user.id,
        term=term,
        q=q,
        section=section,
        credits=credits,
        instructor=instructor,
        day=day,
        from_time=from_time.strftime("%H:%M") if from_time else None,
        to_time=to_time.strftime("%H:%M") if to_time else None,
        page=page,
        page_size=page_size,
    )
