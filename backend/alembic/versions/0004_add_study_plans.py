"""Thêm bảng study_plans (ĐKKHHT) và term_course_openings (Mở lớp theo nhu cầu).

Revision ID: 0004_add_study_plans
Revises: 0003_add_student_faculty
Create Date: 2026-11-22
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004_add_study_plans"
down_revision: str | Sequence[str] | None = "0003_add_student_faculty"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "study_plans",
        sa.Column(
            "id",
            sa.Integer(),
            sa.Identity(always=False),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "student_id",
            sa.Integer(),
            sa.ForeignKey("students.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "course_id",
            sa.Integer(),
            sa.ForeignKey("courses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("term", sa.String(length=10), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "student_id",
            "course_id",
            "term",
            name="uq_study_plans_student_course_term",
        ),
    )
    op.create_index("ix_study_plans_term_course", "study_plans", ["term", "course_id"])

    op.create_table(
        "term_course_openings",
        sa.Column("term", sa.String(length=10), primary_key=True, nullable=False),
        sa.Column(
            "course_id",
            sa.Integer(),
            sa.ForeignKey("courses.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "planned_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "min_required",
            sa.SmallInteger(),
            server_default=sa.text("15"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="PENDING",
            nullable=False,
        ),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "planned_count >= 0", name="ck_term_course_openings_planned_count"
        ),
        sa.CheckConstraint(
            "min_required BETWEEN 1 AND 200",
            name="ck_term_course_openings_min_required",
        ),
        sa.CheckConstraint(
            "status IN ('PENDING','OPENED','NOT_OPENED')",
            name="ck_term_course_openings_status",
        ),
    )


def downgrade() -> None:
    op.drop_table("term_course_openings")
    op.drop_index("ix_study_plans_term_course", table_name="study_plans")
    op.drop_table("study_plans")
