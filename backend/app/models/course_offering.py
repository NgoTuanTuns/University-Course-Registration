from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Identity,
    Index,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CourseOffering(Base):
    """Lớp học phần mở trong một học kỳ.

    schedule (JSONB): [{"day": 1, "start": "07:00", "end": "09:30"}], day 1 = Thứ Hai ... 7 = Chủ nhật.
    """

    __tablename__ = "course_offerings"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False)
    term: Mapped[str] = mapped_column(String(10), nullable=False)  # 2026-1
    section: Mapped[str] = mapped_column(String(10), nullable=False)  # mã lớp, ví dụ 01
    instructor: Mapped[str | None] = mapped_column(String(150))
    capacity: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    enrolled_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("0"))
    schedule: Mapped[list] = mapped_column(JSONB, nullable=False)
    room: Mapped[str | None] = mapped_column(String(50))

    __table_args__ = (
        UniqueConstraint("course_id", "term", "section", name="uq_offerings_course_term_section"),
        CheckConstraint("capacity > 0", name="ck_offerings_capacity"),
        CheckConstraint("enrolled_count BETWEEN 0 AND capacity", name="ck_offerings_enrolled_range"),
        Index("ix_offerings_term", "term"),
        Index("ix_offerings_course", "course_id"),
    )
