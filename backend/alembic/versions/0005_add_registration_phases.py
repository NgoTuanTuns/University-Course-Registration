"""Thêm bảng term_registration_settings quản lý giai đoạn đợt đăng ký theo học kỳ.

Revision ID: 0005_add_registration_phases
Revises: 0004_add_study_plans
Create Date: 2026-11-22
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005_add_registration_phases"
down_revision: str | Sequence[str] | None = "0004_add_study_plans"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "term_registration_settings",
        sa.Column(
            "id",
            sa.Integer(),
            sa.Identity(always=False),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("term", sa.String(length=20), nullable=False),
        sa.Column(
            "phase",
            sa.String(length=32),
            nullable=False,
            server_default="ENROLLMENT_OPEN",
        ),
        sa.Column("phase_ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("note", sa.String(length=300), nullable=True),
        sa.Column(
            "updated_by_id",
            sa.Integer(),
            sa.ForeignKey("students.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("term", name="uq_term_registration_settings_term"),
        sa.CheckConstraint(
            "phase IN ('STUDY_PLAN_OPEN','CLASS_OPENING_REVIEW','ENROLLMENT_OPEN','LOCKED')",
            name="ck_term_registration_settings_phase",
        ),
    )


def downgrade() -> None:
    op.drop_table("term_registration_settings")
