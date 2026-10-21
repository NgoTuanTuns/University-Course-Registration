from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CompletedCourse(Base):
    """Chỉ lưu các môn sinh viên đã học xong và đạt (thang điểm 10)."""

    __tablename__ = "completed_courses"

    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), primary_key=True
    )
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), primary_key=True)
    grade: Mapped[Decimal | None] = mapped_column(Numeric(3, 1))
    term: Mapped[str | None] = mapped_column(String(10))

    __table_args__ = (CheckConstraint("grade BETWEEN 0 AND 10", name="ck_completed_grade"),)
