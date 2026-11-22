from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class StudyPlan(Base):
    """Kế hoạch học tập (ĐKKHHT) của sinh viên cho một học kỳ tiếp theo."""

    __tablename__ = "study_plans"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    student_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    course_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False
    )
    term: Mapped[str] = mapped_column(String(10), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "course_id",
            "term",
            name="uq_study_plans_student_course_term",
        ),
        Index("ix_study_plans_term_course", "term", "course_id"),
    )


class TermCourseOpening(Base):
    """Trạng thái tổng hợp nhu cầu ĐKKHHT và quyết định mở lớp theo học kỳ."""

    __tablename__ = "term_course_openings"

    term: Mapped[str] = mapped_column(String(10), primary_key=True)
    course_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("courses.id", ondelete="CASCADE"), primary_key=True
    )
    planned_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    min_required: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=text("15")
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="PENDING"
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint(
            "planned_count >= 0", name="ck_term_course_openings_planned_count"
        ),
        CheckConstraint(
            "min_required BETWEEN 1 AND 200",
            name="ck_term_course_openings_min_required",
        ),
        CheckConstraint(
            "status IN ('PENDING','OPENED','NOT_OPENED')",
            name="ck_term_course_openings_status",
        ),
    )
