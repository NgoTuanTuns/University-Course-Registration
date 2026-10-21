from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Identity,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Student(Base):
    """Tài khoản người dùng: sinh viên hoặc quản trị viên (đúng 2 vai trò)."""

    __tablename__ = "students"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    mssv: Mapped[str | None] = mapped_column(String(20))  # admin có thể để trống
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    role: Mapped[str] = mapped_column(String(10), nullable=False, server_default="student")
    program: Mapped[str | None] = mapped_column(String(100))
    max_credits: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("25"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("mssv", name="uq_students_mssv"),
        UniqueConstraint("email", name="uq_students_email"),
        CheckConstraint("role IN ('student','admin')", name="ck_students_role"),
        CheckConstraint("max_credits BETWEEN 1 AND 40", name="ck_students_max_credits"),
        CheckConstraint("role <> 'student' OR mssv IS NOT NULL", name="ck_students_student_has_mssv"),
    )
