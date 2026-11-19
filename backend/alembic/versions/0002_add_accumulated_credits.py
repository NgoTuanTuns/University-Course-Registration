"""Thêm cột accumulated_credits cho students và min_accumulated_credits cho courses.

Revision ID: 0002_add_accumulated_credits
Revises: 4cf23a63c3a3
Create Date: 2026-11-19
"""

import sqlalchemy as sa

from alembic import op

revision = "0002_add_accumulated_credits"
down_revision = "4cf23a63c3a3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "students",
        sa.Column(
            "accumulated_credits",
            sa.SmallInteger(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.create_check_constraint(
        "ck_students_accumulated_credits",
        "students",
        "accumulated_credits BETWEEN 0 AND 200",
    )

    op.add_column(
        "courses",
        sa.Column(
            "min_accumulated_credits",
            sa.SmallInteger(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.create_check_constraint(
        "ck_courses_min_accumulated_credits",
        "courses",
        "min_accumulated_credits BETWEEN 0 AND 150",
    )


def downgrade() -> None:
    op.drop_constraint("ck_courses_min_accumulated_credits", "courses", type_="check")
    op.drop_column("courses", "min_accumulated_credits")

    op.drop_constraint("ck_students_accumulated_credits", "students", type_="check")
    op.drop_column("students", "accumulated_credits")
