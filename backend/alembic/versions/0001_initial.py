"""Khởi tạo 7 bảng đúng DDL ở Mục 6 của quy ước nhóm

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-20

Ghi chú: migration này VIẾT TAY (không autogenerate) để đảm bảo đúng từng cột, CHECK có tên,
chỉ mục từng phần. Sau khi sửa models, luôn chạy `alembic check` để chắc models và DB còn khớp.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def _create_students() -> None:
    op.create_table(
        "students",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("mssv", sa.String(length=20), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=150), nullable=False),
        sa.Column("role", sa.String(length=10), server_default="student", nullable=False),
        sa.Column("program", sa.String(length=100), nullable=True),
        sa.Column("max_credits", sa.SmallInteger(), server_default=sa.text("25"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("role IN ('student','admin')", name="ck_students_role"),
        sa.CheckConstraint("max_credits BETWEEN 1 AND 40", name="ck_students_max_credits"),
        sa.CheckConstraint("role <> 'student' OR mssv IS NOT NULL", name="ck_students_student_has_mssv"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_students")),
        sa.UniqueConstraint("mssv", name="uq_students_mssv"),
        sa.UniqueConstraint("email", name="uq_students_email"),
    )


def _create_courses() -> None:
    op.create_table(
        "courses",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("credits", sa.SmallInteger(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("credits BETWEEN 1 AND 10", name="ck_courses_credits"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_courses")),
        sa.UniqueConstraint("code", name="uq_courses_code"),
    )


def _create_course_offerings() -> None:
    op.create_table(
        "course_offerings",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("term", sa.String(length=10), nullable=False),
        sa.Column("section", sa.String(length=10), nullable=False),
        sa.Column("instructor", sa.String(length=150), nullable=True),
        sa.Column("capacity", sa.SmallInteger(), nullable=False),
        sa.Column("enrolled_count", sa.SmallInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("schedule", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("room", sa.String(length=50), nullable=True),
        sa.CheckConstraint("capacity > 0", name="ck_offerings_capacity"),
        sa.CheckConstraint("enrolled_count BETWEEN 0 AND capacity", name="ck_offerings_enrolled_range"),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], name=op.f("fk_course_offerings_course_id_courses")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_course_offerings")),
        sa.UniqueConstraint("course_id", "term", "section", name="uq_offerings_course_term_section"),
    )
    op.create_index("ix_offerings_term", "course_offerings", ["term"], unique=False)
    op.create_index("ix_offerings_course", "course_offerings", ["course_id"], unique=False)


def _create_prerequisites() -> None:
    op.create_table(
        "prerequisites",
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("prereq_course_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=3), server_default="AND", nullable=False),
        sa.Column("group_no", sa.SmallInteger(), server_default=sa.text("0"), nullable=False),
        sa.CheckConstraint("type IN ('AND','OR')", name="ck_prereq_type"),
        sa.CheckConstraint("course_id <> prereq_course_id", name="ck_prereq_no_self"),
        sa.CheckConstraint(
            "(type = 'AND' AND group_no = 0) OR (type = 'OR' AND group_no > 0)",
            name="ck_prereq_group",
        ),
        sa.ForeignKeyConstraint(
            ["course_id"], ["courses.id"],
            name=op.f("fk_prerequisites_course_id_courses"), ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["prereq_course_id"], ["courses.id"],
            name=op.f("fk_prerequisites_prereq_course_id_courses"),
        ),
        sa.PrimaryKeyConstraint("course_id", "prereq_course_id", name=op.f("pk_prerequisites")),
    )
    op.create_index("ix_prereq_prereq", "prerequisites", ["prereq_course_id"], unique=False)


def _create_completed_courses() -> None:
    op.create_table(
        "completed_courses",
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("grade", sa.Numeric(precision=3, scale=1), nullable=True),
        sa.Column("term", sa.String(length=10), nullable=True),
        sa.CheckConstraint("grade BETWEEN 0 AND 10", name="ck_completed_grade"),
        sa.ForeignKeyConstraint(
            ["student_id"], ["students.id"],
            name=op.f("fk_completed_courses_student_id_students"), ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["course_id"], ["courses.id"], name=op.f("fk_completed_courses_course_id_courses"),
        ),
        sa.PrimaryKeyConstraint("student_id", "course_id", name=op.f("pk_completed_courses")),
    )


def _create_enrollments() -> None:
    op.create_table(
        "enrollments",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("offering_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=10), server_default="ACTIVE", nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("enrolled_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('ACTIVE','CANCELLED')", name="ck_enrollments_status"),
        sa.ForeignKeyConstraint(
            ["student_id"], ["students.id"],
            name=op.f("fk_enrollments_student_id_students"), ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["offering_id"], ["course_offerings.id"],
            name=op.f("fk_enrollments_offering_id_course_offerings"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_enrollments")),
    )
    # Mỗi sinh viên chỉ có một đăng ký ACTIVE cho mỗi lớp (hủy rồi vẫn đăng ký lại được)
    op.create_index(
        "uq_enrollments_active", "enrollments", ["student_id", "offering_id"],
        unique=True, postgresql_where=sa.text("status = 'ACTIVE'"),
    )
    op.create_index("ix_enrollments_student", "enrollments", ["student_id", "status"], unique=False)
    op.create_index(
        "ix_enrollments_offering", "enrollments", ["offering_id"],
        unique=False, postgresql_where=sa.text("status = 'ACTIVE'"),
    )


def _create_waitlist() -> None:
    op.create_table(
        "waitlist",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("offering_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("enqueued_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("position > 0", name="ck_waitlist_position"),
        sa.ForeignKeyConstraint(
            ["student_id"], ["students.id"],
            name=op.f("fk_waitlist_student_id_students"), ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["offering_id"], ["course_offerings.id"],
            name=op.f("fk_waitlist_offering_id_course_offerings"), ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_waitlist")),
        sa.UniqueConstraint("student_id", "offering_id", name="uq_waitlist_student_offering"),
    )
    op.create_index("ix_waitlist_queue", "waitlist", ["offering_id", "enqueued_at", "id"], unique=False)


def upgrade() -> None:
    _create_students()
    _create_courses()
    _create_course_offerings()
    _create_prerequisites()
    _create_completed_courses()
    _create_enrollments()
    _create_waitlist()


def downgrade() -> None:
    # Xóa theo thứ tự ngược của khóa ngoại; xóa bảng thì chỉ mục đi kèm cũng mất.
    op.drop_table("waitlist")
    op.drop_table("enrollments")
    op.drop_table("completed_courses")
    op.drop_table("prerequisites")
    op.drop_table("course_offerings")
    op.drop_table("courses")
    op.drop_table("students")
