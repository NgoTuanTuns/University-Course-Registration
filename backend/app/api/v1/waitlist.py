from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import CurrentUser, require_role
from app.schemas.enrollment import WaitlistPage
from app.services.waitlist_service import leave, list_waitlist

router = APIRouter(prefix="/waitlist", tags=["waitlist"])
Session = Annotated[AsyncSession, Depends(get_session)]
User = Annotated[CurrentUser, Depends(require_role("student"))]


@router.get("", response_model=WaitlistPage)
async def get_waitlist(
    session: Session,
    user: User,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict:
    return await list_waitlist(session, user.id, page, page_size)


@router.delete("/{waitlist_id}")
async def leave_waitlist(waitlist_id: int, session: Session, user: User) -> dict:
    return await leave(session, user.id, waitlist_id)
