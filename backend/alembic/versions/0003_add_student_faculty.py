"""Thêm cột faculty (Khoa) cho bảng students.

Revision ID: 0003_add_student_faculty
Revises: 0002_add_accumulated_credits
Create Date: 2026-11-19
"""

import sqlalchemy as sa

from alembic import op

revision = "0003_add_student_faculty"
down_revision = "0002_add_accumulated_credits"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "students",
        sa.Column("faculty", sa.String(length=100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("students", "faculty")
