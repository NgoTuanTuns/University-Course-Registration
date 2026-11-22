"""API Điều hành giai đoạn đợt đăng ký theo học kỳ (Registration Phase Control)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import CurrentUser, get_current_user, require_role
from app.schemas.registration_phase import (
    RegistrationPhaseOut,
    RegistrationPhaseUpdateRequest,
)
from app.services.phase_service import (
    get_registration_phase,
    update_registration_phase,
)

router = APIRouter(tags=["registration-phase"])


@router.get("/registration-phase", response_model=RegistrationPhaseOut)
async def read_registration_phase(
    session: Annotated[AsyncSession, Depends(get_session)],
    _user: Annotated[CurrentUser, Depends(get_current_user)],
    term: Annotated[str | None, Query(pattern=r"^\d{4}-[1-3]$")] = None,
) -> dict:
    return await get_registration_phase(session, term=term)


@router.patch("/admin/registration-phase", response_model=RegistrationPhaseOut)
async def admin_update_registration_phase(
    body: RegistrationPhaseUpdateRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    admin: Annotated[CurrentUser, Depends(require_role("admin"))],
) -> dict:
    return await update_registration_phase(
        session,
        term=body.term,
        phase=body.phase,
        phase_ends_at=body.phase_ends_at,
        note=body.note,
        admin_id=admin.id,
    )
