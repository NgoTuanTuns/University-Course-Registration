from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Enrollment(Base):
    """Đăng ký học phần. `version` tăng 1 mỗi lần sửa (optimistic locking)."""

    __tablename__ = "enrollments"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    offering_id: Mapped[int] = mapped_column(ForeignKey("course_offerings.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False, server_default="ACTIVE")
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    enrolled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint("status IN ('ACTIVE','CANCELLED')", name="ck_enrollments_status"),
        # Mỗi sinh viên chỉ có một đăng ký ACTIVE cho mỗi lớp (hủy rồi vẫn đăng ký lại được)
        Index(
            "uq_enrollments_active",
            "student_id",
            "offering_id",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
        ),
        Index("ix_enrollments_student", "student_id", "status"),
        Index("ix_enrollments_offering", "offering_id", postgresql_where=text("status = 'ACTIVE'")),
    )
