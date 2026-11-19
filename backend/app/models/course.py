from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Identity,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Course(Base):
    """Học phần (môn học), ví dụ INT131."""

    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    credits: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    min_accumulated_credits: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=text("0")
    )
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("code", name="uq_courses_code"),
        CheckConstraint("credits BETWEEN 1 AND 10", name="ck_courses_credits"),
        CheckConstraint(
            "min_accumulated_credits BETWEEN 0 AND 150",
            name="ck_courses_min_accumulated_credits",
        ),
    )
