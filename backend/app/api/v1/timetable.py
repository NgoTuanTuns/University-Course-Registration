from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import CurrentUser, require_role
from app.schemas.enrollment import Timetable
from app.services.enrollment_queries import timetable

router = APIRouter(prefix="/timetable", tags=["timetable"])


@router.get("", response_model=Timetable)
async def get_timetable(
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[CurrentUser, Depends(require_role("student"))],
    term: Annotated[str | None, Query(pattern=r"^\d{4}-[1-3]$")] = None,
) -> dict:
    return await timetable(session, user.id, term)
