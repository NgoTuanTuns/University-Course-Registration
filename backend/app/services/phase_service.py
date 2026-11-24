"""Nghiệp vụ quản lý giai đoạn đợt đăng ký theo học kỳ (Registration Phase Control)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import api_error
from app.models import TermRegistrationSetting

VALID_PHASES: tuple[str, ...] = (
    "STUDY_PLAN_OPEN",
    "CLASS_OPENING_REVIEW",
    "ENROLLMENT_OPEN",
    "LOCKED",
)

PHASE_METADATA: dict[str, dict[str, str]] = {
    "STUDY_PLAN_OPEN": {
        "label": "Đợt ĐKKHHT",
        "description": (
            "Sinh viên đăng ký hoặc điều chỉnh danh sách môn dự kiến học (KHHT). "
            "Cổng đăng ký lớp học phần chưa mở."
        ),
    },
    "CLASS_OPENING_REVIEW": {
        "label": "Chốt mở lớp",
        "description": (
            "Đã khóa KHHT. Phòng Đào tạo đang tổng hợp nhu cầu và mở các lớp học phần "
            "đủ sĩ số tối thiểu."
        ),
    },
    "ENROLLMENT_OPEN": {
        "label": "Đợt ĐKMH chính thức",
        "description": (
            "Sinh viên thực hiện đăng ký học phần, đổi lớp và sắp xếp thời khóa biểu "
            "dựa trên các lớp đã mở."
        ),
    },
    "LOCKED": {
        "label": "Đã khóa sổ học kỳ",
        "description": (
            "Kết thúc đợt đăng ký. Sinh viên chỉ được xem lại Kế hoạch học tập và "
            "Thời khóa biểu đã chốt."
        ),
    },
}


def phase_permissions(phase: str) -> tuple[bool, bool]:
    """Trả về (can_edit_study_plan, can_enroll) tương ứng với giai đoạn hiện tại."""
    if phase not in PHASE_METADATA:
        raise ValueError(f"Giai đoạn không hợp lệ: {phase}")
    return (phase == "STUDY_PLAN_OPEN", phase == "ENROLLMENT_OPEN")


def build_phase_payload(
    term: str,
    phase: str,
    *,
    phase_ends_at: datetime | None = None,
    note: str | None = None,
    updated_at: datetime | None = None,
    now: datetime | None = None,
) -> dict:
    can_edit_sp, can_enroll = phase_permissions(phase)
    current_now = now or datetime.now(UTC)
    if phase_ends_at is not None:
        ends_utc = (
            phase_ends_at.replace(tzinfo=UTC)
            if phase_ends_at.tzinfo is None
            else phase_ends_at.astimezone(UTC)
        )
        if ends_utc <= current_now:
            can_edit_sp = False
            can_enroll = False
    meta = PHASE_METADATA[phase]
    return {
        "term": term,
        "phase": phase,
        "phase_label": meta["label"],
        "phase_description": meta["description"],
        "phase_ends_at": phase_ends_at,
        "note": note,
        "can_edit_study_plan": can_edit_sp,
        "can_enroll": can_enroll,
        "updated_at": updated_at,
    }


def default_phase_for_settings() -> str:
    settings = get_settings()
    return "STUDY_PLAN_OPEN" if settings.study_plan_editable else "ENROLLMENT_OPEN"


async def get_registration_phase(
    session: AsyncSession, term: str | None = None
) -> dict:
    settings = get_settings()
    target_term = term or settings.study_plan_term
    row = await session.scalar(
        select(TermRegistrationSetting).where(
            TermRegistrationSetting.term == target_term
        )
    )
    if not isinstance(row, TermRegistrationSetting):
        return build_phase_payload(target_term, default_phase_for_settings())
    return build_phase_payload(
        row.term,
        row.phase,
        phase_ends_at=row.phase_ends_at,
        note=row.note,
        updated_at=row.updated_at,
    )


async def update_registration_phase(
    session: AsyncSession,
    *,
    term: str,
    phase: str,
    phase_ends_at: datetime | None,
    note: str | None,
    admin_id: int,
) -> dict:
    if phase not in PHASE_METADATA:
        raise api_error(422, "INVALID_PHASE", f"Giai đoạn '{phase}' không hợp lệ.")
    now = datetime.now(UTC)
    row = (
        await session.execute(
            select(TermRegistrationSetting).where(TermRegistrationSetting.term == term)
        )
    ).scalar_one_or_none()
    cleaned_note = note.strip() if note and note.strip() else None
    if row is None:
        row = TermRegistrationSetting(
            term=term,
            phase=phase,
            phase_ends_at=phase_ends_at,
            note=cleaned_note,
            updated_by_id=admin_id,
            updated_at=now,
        )
        session.add(row)
    else:
        row.phase = phase
        row.phase_ends_at = phase_ends_at
        row.note = cleaned_note
        row.updated_by_id = admin_id
        row.updated_at = now
    await session.commit()
    await session.refresh(row)
    return build_phase_payload(
        row.term,
        row.phase,
        phase_ends_at=row.phase_ends_at,
        note=row.note,
        updated_at=row.updated_at,
    )


async def assert_study_plan_open(
    session: AsyncSession, term: str | None = None
) -> None:
    info = await get_registration_phase(session, term=term)
    if not info["can_edit_study_plan"]:
        raise api_error(
            403,
            "STUDY_PLAN_PERIOD_CLOSED",
            f"Đợt Đăng ký Kế hoạch học tập học kỳ {info['term']} đã kết thúc "
            f"(hiện đang ở giai đoạn: {info['phase_label']}). "
            "Sinh viên không thể thêm hoặc xóa học phần trong KHHT.",
        )


async def assert_enrollment_open(
    session: AsyncSession, term: str | None = None
) -> None:
    info = await get_registration_phase(session, term=term)
    if not info["can_enroll"]:
        raise api_error(
            403,
            "REGISTRATION_PHASE_CLOSED",
            f"Cổng đăng ký học phần học kỳ {info['term']} hiện đang đóng "
            f"(giai đoạn hiện tại: {info['phase_label']}).",
        )
