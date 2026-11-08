"""Nạp dữ liệu mẫu vào PostgreSQL.

    python -m app.seed                       # profile default (200 học phần, 1000 sinh viên)
    python -m app.seed --profile minimal     # chỉ bộ ca đặc biệt (dùng cho test)
    python -m app.seed --reset               # xóa sạch 7 bảng rồi nạp lại (id bắt đầu lại từ 1)

Dữ liệu được sinh bởi app/seed_data.py (thuần Python, đã có test). File này chỉ lo phần ghi vào DB.
Thứ tự id: sinh viên sv000N có id = N (admin đặt cuối).
"""

import argparse
import asyncio
import logging
import os
import sys
from decimal import Decimal

from sqlalchemy import func, insert, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.redis import close_redis
from app.core.security import hash_password
from app.models import (
    CompletedCourse,
    Course,
    CourseOffering,
    Enrollment,
    Prerequisite,
    Student,
    Waitlist,
)
from app.seed_data import (
    ADMIN_EMAIL,
    ADMIN_PASSWORD,
    STUDENT_PASSWORD,
    Dataset,
    build_dataset,
    validate_dataset,
)
from app.services.prerequisite_cache import invalidate_graph
from app.services.prerequisite_core import PrerequisiteCycleError, assert_acyclic

CHUNK = 5000
logger = logging.getLogger("seed")
# Chuỗi hằng cố định (không có dữ liệu người dùng) nên không phải "ghép chuỗi SQL"
_TRUNCATE_SQL = (
    "TRUNCATE TABLE waitlist, enrollments, completed_courses, prerequisites, "
    "course_offerings, courses, students RESTART IDENTITY CASCADE"
)


async def _insert_many(session: AsyncSession, model, rows: list[dict]) -> None:
    for i in range(0, len(rows), CHUNK):
        await session.execute(insert(model), rows[i : i + CHUNK])


async def _insert_returning(session: AsyncSession, model, rows: list[dict], *cols):
    """Chèn nhiều dòng và trả về các cột chỉ định (dùng để ánh xạ mã -> id)."""
    out = []
    for i in range(0, len(rows), CHUNK):
        result = await session.execute(
            insert(model).returning(*cols), rows[i : i + CHUNK]
        )
        out.extend(result.all())
    return out


async def _load_students(session: AsyncSession, ds: Dataset) -> dict[str, int]:
    """Giữ thứ tự để sv000N có id = N. Băm mật khẩu MỘT lần rồi dùng lại cho mọi tài khoản mẫu."""
    admin_hash = hash_password(ADMIN_PASSWORD)
    student_hash = hash_password(STUDENT_PASSWORD)
    rows = [
        dict(
            mssv=s.mssv,
            email=s.email,
            full_name=s.full_name,
            role=s.role,
            program=s.program,
            max_credits=s.max_credits,
            password_hash=admin_hash if s.role == "admin" else student_hash,
        )
        for s in ds.students
    ]
    result = await _insert_returning(session, Student, rows, Student.id, Student.email)
    return {email: sid for sid, email in result}


async def _load_courses(session: AsyncSession, ds: Dataset) -> dict[str, int]:
    rows = [
        dict(code=c.code, name=c.name, credits=c.credits, description=c.description)
        for c in ds.courses
    ]
    result = await _insert_returning(session, Course, rows, Course.id, Course.code)
    return {code: cid for cid, code in result}


async def _load_offerings(
    session: AsyncSession, ds: Dataset, course_id: dict[str, int]
) -> dict[tuple[str, str], int]:
    """enrolled_count đã đúng bằng số đăng ký ACTIVE vì dataset đã được kiểm tra trước khi nạp."""
    rows = [
        dict(
            course_id=course_id[o.course_code],
            term=o.term,
            section=o.section,
            instructor=o.instructor,
            capacity=o.capacity,
            enrolled_count=o.enrolled_count,
            schedule=o.schedule,
            room=o.room,
        )
        for o in ds.offerings
    ]
    code_of = {v: k for k, v in course_id.items()}
    result = await _insert_returning(
        session,
        CourseOffering,
        rows,
        CourseOffering.id,
        CourseOffering.course_id,
        CourseOffering.section,
    )
    return {(code_of[cid], section): oid for oid, cid, section in result}


async def _load_prereqs(
    session: AsyncSession, ds: Dataset, course_id: dict[str, int]
) -> None:
    await _insert_many(
        session,
        Prerequisite,
        [
            dict(
                course_id=course_id[p.course_code],
                prereq_course_id=course_id[p.prereq_code],
                type=p.type,
                group_no=p.group_no,
            )
            for p in ds.prereqs
        ],
    )


async def _load_student_data(
    session: AsyncSession,
    ds: Dataset,
    student_id: dict[str, int],
    course_id: dict[str, int],
    offering_id: dict[tuple[str, str], int],
) -> None:
    """Đã học, đăng ký, hàng chờ."""
    await _insert_many(
        session,
        CompletedCourse,
        [
            dict(
                student_id=student_id[r.student_email],
                course_id=course_id[r.course_code],
                grade=Decimal(str(r.grade)),
                term=r.term,
            )
            for r in ds.completed
        ],
    )
    await _insert_many(
        session,
        Enrollment,
        [
            dict(
                student_id=student_id[e.student_email],
                offering_id=offering_id[e.offering_key],
                status=e.status,
                version=0,
                enrolled_at=e.enrolled_at,
            )
            for e in ds.enrollments
        ],
    )
    await _insert_many(
        session,
        Waitlist,
        [
            dict(
                student_id=student_id[w.student_email],
                offering_id=offering_id[w.offering_key],
                position=w.position,
                enqueued_at=w.enqueued_at,
            )
            for w in ds.waitlist
        ],
    )


async def load_dataset(session: AsyncSession, ds: Dataset) -> dict[str, int]:
    """Ghi toàn bộ dataset trong MỘT transaction (do caller commit). Trả về số dòng từng bảng."""
    student_id = await _load_students(session, ds)
    course_id = await _load_courses(session, ds)
    await _load_prereqs(session, ds, course_id)
    offering_id = await _load_offerings(session, ds, course_id)
    await _load_student_data(session, ds, student_id, course_id, offering_id)
    return {
        "students": len(ds.students),
        "courses": len(ds.courses),
        "prerequisites": len(ds.prereqs),
        "course_offerings": len(ds.offerings),
        "completed_courses": len(ds.completed),
        "enrollments": len(ds.enrollments),
        "waitlist": len(ds.waitlist),
    }


async def _clear_prereq_cache() -> None:
    """Quy ước Mục 7: seed lại toàn bộ thì xóa đồ thị `prereqgraph:v1` và mọi `prereq:*`.

    Dùng invalidate_graph() của M2 (SCAN + UNLINK, không KEYS). Redis chưa chạy thì
    hàm chỉ ghi log, seed vẫn thành công.
    """
    try:
        await invalidate_graph()
    finally:
        await close_redis()


def _check_acyclic(ds: Dataset) -> list[str]:
    """Kiểm tra DAG bằng assert_acyclic của M2 trước khi ghi: có vòng thì seed thất bại."""
    try:
        assert_acyclic(
            (p.course_code, p.prereq_code, p.type, p.group_no) for p in ds.prereqs
        )
    except PrerequisiteCycleError as exc:
        return [f"Tiên quyết có vòng lặp: {exc}"]
    return []


async def _prepare(session: AsyncSession, args: argparse.Namespace) -> int | None:
    """Quyết định có nạp không. Trả mã thoát nếu dừng; None nếu tiếp tục nạp."""
    existing = (
        await session.execute(select(func.count()).select_from(Course))
    ).scalar_one()
    if existing and not args.reset:
        logger.error(
            "DB đã có %d học phần. Chạy lại với --reset để xóa và nạp lại.", existing
        )
        return 1
    if args.reset:
        await session.execute(text(_TRUNCATE_SQL))
    return None


def _report(args: argparse.Namespace, counts: dict[str, int]) -> None:
    logger.info("Seed profile '%s' xong:", args.profile)
    for table, n in counts.items():
        logger.info("  %-18s %6d", table, n)
    logger.info(
        "Admin: %s / %s   |   Sinh viên: svNNNN@uni.edu.vn / %s",
        ADMIN_EMAIL,
        ADMIN_PASSWORD,
        STUDENT_PASSWORD,
    )


async def main_async(args: argparse.Namespace) -> int:
    url = (
        args.database_url
        or os.environ.get("DATABASE_URL")
        or get_settings().database_url
    )
    if not url:
        logger.error("Thiếu DATABASE_URL (hoặc dùng --database-url).")
        return 2
    ds = build_dataset(
        args.profile,
        default_max_credits=int(os.environ.get("DEFAULT_MAX_CREDITS", "25")),
    )
    errors = validate_dataset(
        ds, waitlist_ratio=float(os.environ.get("WAITLIST_MAX_RATIO", "0.2"))
    ) + _check_acyclic(ds)
    if errors:
        logger.error(
            "Dữ liệu mẫu KHÔNG nhất quán, dừng:\n  - %s", "\n  - ".join(errors[:10])
        )
        return 3

    engine = create_async_engine(url)
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            stop = await _prepare(session, args)
            if stop is not None:
                return stop
            counts = await load_dataset(session, ds)
            await session.commit()
    finally:
        await engine.dispose()

    _report(args, counts)
    await _clear_prereq_cache()
    return 0


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="Nạp dữ liệu mẫu vào PostgreSQL")
    parser.add_argument("--profile", choices=["minimal", "default"], default="default")
    parser.add_argument(
        "--reset", action="store_true", help="xóa sạch dữ liệu rồi nạp lại"
    )
    parser.add_argument(
        "--database-url", default=None, help="mặc định lấy từ biến DATABASE_URL"
    )
    sys.exit(asyncio.run(main_async(parser.parse_args())))


if __name__ == "__main__":
    main()
