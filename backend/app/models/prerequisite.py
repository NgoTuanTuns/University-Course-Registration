from sqlalchemy import CheckConstraint, ForeignKey, Index, SmallInteger, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Prerequisite(Base):
    """Điều kiện tiên quyết (danh sách kề của đồ thị DAG).

    type = 'AND': bắt buộc phải học xong môn này (group_no = 0).
    type = 'OR' : các dòng cùng (course_id, group_no) là một nhóm, chỉ cần học xong 1 môn trong nhóm.
    """

    __tablename__ = "prerequisites"

    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), primary_key=True
    )
    prereq_course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), primary_key=True)
    type: Mapped[str] = mapped_column(String(3), nullable=False, server_default="AND")
    group_no: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("0"))

    __table_args__ = (
        CheckConstraint("type IN ('AND','OR')", name="ck_prereq_type"),
        CheckConstraint("course_id <> prereq_course_id", name="ck_prereq_no_self"),
        CheckConstraint(
            "(type = 'AND' AND group_no = 0) OR (type = 'OR' AND group_no > 0)",
            name="ck_prereq_group",
        ),
        Index("ix_prereq_prereq", "prereq_course_id"),
    )
