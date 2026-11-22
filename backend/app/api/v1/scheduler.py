"""API Gợi ý xếp lịch tự động không trùng ca (Smart Auto-Scheduler)."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import CurrentUser, require_role
from app.schemas.scheduler import SchedulerSuggestRequest, SchedulerSuggestResponse
from app.services.scheduler_service import suggest_schedules

router = APIRouter(prefix="/scheduler", tags=["scheduler"])


@router.post("/suggest", response_model=SchedulerSuggestResponse)
async def suggest_timetable(
    body: SchedulerSuggestRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[CurrentUser, Depends(require_role("student"))],
) -> dict:
    return await suggest_schedules(session, user.id, body)
