from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Waitlist(Base):
    """Hàng chờ FIFO theo (enqueued_at, id). `position` chỉ để hiển thị."""

    __tablename__ = "waitlist"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    offering_id: Mapped[int] = mapped_column(
        ForeignKey("course_offerings.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    enqueued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("student_id", "offering_id", name="uq_waitlist_student_offering"),
        CheckConstraint("position > 0", name="ck_waitlist_position"),
        Index("ix_waitlist_queue", "offering_id", "enqueued_at", "id"),
    )
