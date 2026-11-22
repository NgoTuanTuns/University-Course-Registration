from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class TermRegistrationSetting(Base):
    """Cấu hình giai đoạn đợt đăng ký cho từng học kỳ (Điều hành bởi Phòng Đào tạo)."""

    __tablename__ = "term_registration_settings"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    term: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    phase: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="ENROLLMENT_OPEN"
    )
    phase_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    note: Mapped[str | None] = mapped_column(String(300))
    updated_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("students.id", ondelete="SET NULL")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "phase IN ('STUDY_PLAN_OPEN','CLASS_OPENING_REVIEW','ENROLLMENT_OPEN','LOCKED')",
            name="ck_term_registration_settings_phase",
        ),
    )
