"""Báo cáo thống kê cơ sở dữ liệu & toàn vẹn hệ thống (M4, Tuần 4).

Chạy bằng lệnh:
    python -m app.reports                  # In báo cáo tổng hợp
    python -m app.reports --json           # Xuất dạng JSON
    python -m app.reports --check-only     # Chỉ kiểm tra bất biến dữ liệu

Nội dung báo cáo:
1. Sĩ số lớp học phần: tỷ lệ lấp đầy, danh sách lớp đầy / sắp đầy, hàng chờ.
2. Cấu trúc DAG tiên quyết: truy vấn đệ quy tính độ sâu, số cạnh AND/OR, fan-in lớn nhất.
3. Hàng chờ (Waitlist): độ dài, thời gian chờ hiện tại (now() - enqueued_at).
4. Kiểm tra bất biến toàn vẹn (tích hợp trực tiếp bộ bất biến M5 từ app.tools.invariants).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.models import Course, CourseOffering, Prerequisite, Student, Waitlist
from app.tools.invariants import find_invariant_violations

logger = logging.getLogger("reports")


async def get_offering_capacity_stats(session: AsyncSession) -> dict[str, Any]:
    """Thống kê sĩ số, sức chứa, tỷ lệ lấp đầy của các lớp học phần."""
    stmt = (
        select(
            CourseOffering.id,
            CourseOffering.term,
            CourseOffering.section,
            CourseOffering.capacity,
            CourseOffering.enrolled_count,
            Course.code.label("course_code"),
            Course.name.label("course_name"),
            func.count(Waitlist.id).label("waitlist_count"),
        )
        .join(Course, CourseOffering.course_id == Course.id)
        .outerjoin(Waitlist, CourseOffering.id == Waitlist.offering_id)
        .group_by(CourseOffering.id, Course.code, Course.name)
        .order_by(Course.code, CourseOffering.section)
    )
    rows = (await session.execute(stmt)).all()

    total_offerings = len(rows)
    total_capacity = sum(r.capacity for r in rows)
    total_enrolled = sum(r.enrolled_count for r in rows)
    overall_fill_rate = (
        round((total_enrolled / total_capacity) * 100, 2) if total_capacity else 0.0
    )

    full_offerings: list[dict[str, Any]] = []
    nearly_full_offerings: list[dict[str, Any]] = []

    for r in rows:
        fill_pct = round((r.enrolled_count / r.capacity) * 100, 1)
        item = {
            "offering_id": r.id,
            "code": f"{r.course_code}-{r.section}",
            "course_name": r.course_name,
            "term": r.term,
            "enrolled": r.enrolled_count,
            "capacity": r.capacity,
            "fill_pct": fill_pct,
            "waitlist_len": r.waitlist_count,
        }
        if r.enrolled_count >= r.capacity:
            full_offerings.append(item)
        elif fill_pct >= 80.0:
            nearly_full_offerings.append(item)

    return {
        "total_offerings": total_offerings,
        "total_capacity": total_capacity,
        "total_enrolled": total_enrolled,
        "overall_fill_rate_pct": overall_fill_rate,
        "full_count": len(full_offerings),
        "nearly_full_count": len(nearly_full_offerings),
        "full_offerings": full_offerings,
        "nearly_full_offerings": nearly_full_offerings,
    }


async def get_dag_structure_stats(session: AsyncSession) -> dict[str, Any]:
    """Phân tích độ sâu và độ phức tạp của đồ thị tiên quyết bằng truy vấn đệ quy."""
    edges_stmt = select(
        Prerequisite.course_id,
        Prerequisite.prereq_course_id,
        Prerequisite.type,
        Prerequisite.group_no,
    )
    edges = (await session.execute(edges_stmt)).all()
    total_edges = len(edges)
    and_count = sum(1 for e in edges if e.type == "AND")
    or_count = sum(1 for e in edges if e.type == "OR")
    or_groups_count = len({(e.course_id, e.group_no) for e in edges if e.type == "OR"})

    fan_in: dict[int, int] = {}
    fan_out: dict[int, int] = {}
    for e in edges:
        fan_in[e.course_id] = fan_in.get(e.course_id, 0) + 1
        fan_out[e.prereq_course_id] = fan_out.get(e.prereq_course_id, 0) + 1

    max_fan_in_cid = max(fan_in, key=fan_in.get) if fan_in else None
    max_fan_in_val = fan_in[max_fan_in_cid] if max_fan_in_cid else 0

    max_fan_out_cid = max(fan_out, key=fan_out.get) if fan_out else None
    max_fan_out_val = fan_out[max_fan_out_cid] if max_fan_out_cid else 0

    # CTE đệ quy tính độ sâu chuỗi tiên quyết từ lá lên gốc
    cte_sql = text(
        """
        WITH RECURSIVE prereq_depth AS (
            -- Điểm bắt đầu: các môn không đòi hỏi môn nào khác (lá của đồ thị DAG)
            SELECT id AS course_id, 0 AS depth
            FROM courses
            WHERE id NOT IN (SELECT course_id FROM prerequisites)
            UNION ALL
            -- Bước đệ quy: môn c đòi hỏi môn p -> độ sâu của c = độ sâu p + 1
            SELECT p.course_id, pd.depth + 1
            FROM prerequisites p
            JOIN prereq_depth pd ON p.prereq_course_id = pd.course_id
            WHERE pd.depth < 50
        )
        SELECT pd.course_id, c.code, c.name, MAX(pd.depth) AS max_depth
        FROM prereq_depth pd
        JOIN courses c ON pd.course_id = c.id
        GROUP BY pd.course_id, c.code, c.name
        ORDER BY max_depth DESC;
        """
    )
    depth_rows = (await session.execute(cte_sql)).all()
    max_depth = depth_rows[0].max_depth if depth_rows else 0

    deepest_courses = [
        {"course_id": r.course_id, "code": r.code, "name": r.name, "depth": r.max_depth}
        for r in depth_rows[:5]
    ]

    max_fan_in_course = None
    if max_fan_in_cid:
        c = await session.get(Course, max_fan_in_cid)
        if c:
            max_fan_in_course = {
                "code": c.code,
                "name": c.name,
                "count": max_fan_in_val,
            }

    max_fan_out_course = None
    if max_fan_out_cid:
        c = await session.get(Course, max_fan_out_cid)
        if c:
            max_fan_out_course = {
                "code": c.code,
                "name": c.name,
                "count": max_fan_out_val,
            }

    return {
        "total_edges": total_edges,
        "and_edges": and_count,
        "or_edges": or_count,
        "distinct_or_groups": or_groups_count,
        "max_dag_depth": max_depth,
        "deepest_courses": deepest_courses,
        "max_fan_in": max_fan_in_course,
        "max_fan_out": max_fan_out_course,
    }


async def get_waitlist_stats(session: AsyncSession) -> dict[str, Any]:
    """Thống kê hàng chờ: số lượng, thời gian chờ hiện tại."""
    now = datetime.now(UTC)
    stmt = (
        select(
            Waitlist.id,
            Waitlist.offering_id,
            Waitlist.student_id,
            Waitlist.position,
            Waitlist.enqueued_at,
            Course.code.label("course_code"),
            CourseOffering.section,
            Student.mssv,
            Student.full_name,
        )
        .join(CourseOffering, Waitlist.offering_id == CourseOffering.id)
        .join(Course, CourseOffering.course_id == Course.id)
        .join(Student, Waitlist.student_id == Student.id)
        .order_by(Waitlist.offering_id, Waitlist.position)
    )
    rows = (await session.execute(stmt)).all()

    total_waitlisted = len(rows)
    offering_ids = {r.offering_id for r in rows}

    wait_durations_sec = [
        (
            now
            - (
                r.enqueued_at
                if r.enqueued_at.tzinfo
                else r.enqueued_at.replace(tzinfo=UTC)
            )
        ).total_seconds()
        for r in rows
    ]
    avg_wait_sec = (
        round(sum(wait_durations_sec) / len(wait_durations_sec), 1)
        if wait_durations_sec
        else 0.0
    )
    max_wait_sec = round(max(wait_durations_sec), 1) if wait_durations_sec else 0.0

    queue_by_offering: dict[str, int] = {}
    for r in rows:
        key = f"{r.course_code}-{r.section}"
        queue_by_offering[key] = queue_by_offering.get(key, 0) + 1

    longest_queues = [
        {"offering": k, "queue_length": v}
        for k, v in sorted(queue_by_offering.items(), key=lambda x: x[1], reverse=True)[
            :5
        ]
    ]

    return {
        "total_waitlisted": total_waitlisted,
        "offerings_with_waitlist": len(offering_ids),
        "avg_wait_time_seconds": avg_wait_sec,
        "max_wait_time_seconds": max_wait_sec,
        "longest_queues": longest_queues,
    }


async def generate_full_report(session: AsyncSession) -> dict[str, Any]:
    """Tạo báo cáo tổng hợp đầy đủ số liệu và kiểm tra bất biến."""
    capacity = await get_offering_capacity_stats(session)
    dag = await get_dag_structure_stats(session)
    waitlist = await get_waitlist_stats(session)
    violations = await find_invariant_violations(session)

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "capacity": capacity,
        "dag": dag,
        "waitlist": waitlist,
        "invariants": {
            "is_valid": len(violations) == 0,
            "violations_count": len(violations),
            "violations": [
                {
                    "invariant": v.invariant,
                    "message": v.message,
                    "context": v.context,
                }
                for v in violations
            ],
        },
    }


def print_text_report(rep: dict[str, Any]) -> None:
    """In báo cáo định dạng bảng rõ ràng ra màn hình terminal."""
    sep = "=" * 70
    sub_sep = "-" * 70
    print(sep)
    print(" BÁO CÁO THỐNG KÊ CƠ SỞ DỮ LIỆU & TOÀN VẸN HỆ THỐNG (M4)")
    print(f" Thời gian: {rep['generated_at']}")
    print(sep)

    cap = rep["capacity"]
    print("\n1. THỐNG KÊ SĨ SỐ & LỚP HỌC PHẦN:")
    print(f"  - Tổng số lớp mở:             {cap['total_offerings']}")
    print(f"  - Tổng sức chứa (capacity):    {cap['total_capacity']}")
    print(f"  - Tổng đã đăng ký (enrolled):  {cap['total_enrolled']}")
    print(f"  - Tỷ lệ lấp đầy toàn hệ thống: {cap['overall_fill_rate_pct']}%")
    print(f"  - Số lớp đã đầy (100%):        {cap['full_count']}")
    print(f"  - Số lớp sắp đầy (>= 80%):     {cap['nearly_full_count']}")

    if cap["full_offerings"]:
        print("\n  [Lớp đã đầy]:")
        for o in cap["full_offerings"][:5]:
            print(
                f"    * {o['code']:<12} | {o['course_name'][:25]:<25} | {o['enrolled']}/{o['capacity']} | Hàng chờ: {o['waitlist_len']}"
            )

    dag = rep["dag"]
    print(f"\n{sub_sep}")
    print("2. CẤU TRÚC ĐỒ THỊ TIÊN QUYẾT (DAG):")
    print(f"  - Tổng số cạnh tiên quyết:     {dag['total_edges']}")
    print(
        f"  - Cạnh AND / OR:               {dag['and_edges']} AND  |  {dag['or_edges']} OR"
    )
    print(f"  - Số nhóm OR riêng biệt:       {dag['distinct_or_groups']}")
    print(f"  - Độ sâu lớn nhất của DAG:     {dag['max_dag_depth']} tầng")
    if dag["max_fan_in"]:
        print(
            f"  - Môn nhiều tiên quyết nhất:   {dag['max_fan_in']['code']} ({dag['max_fan_in']['name']}) -> {dag['max_fan_in']['count']} môn"
        )
    if dag["max_fan_out"]:
        print(
            f"  - Môn làm tiên quyết cho nhiều nhất: {dag['max_fan_out']['code']} ({dag['max_fan_out']['name']}) -> {dag['max_fan_out']['count']} môn"
        )

    if dag["deepest_courses"]:
        print("\n  [Các môn có chuỗi tiên quyết sâu nhất]:")
        for d in dag["deepest_courses"]:
            print(
                f"    * {d['code']:<10} | {d['name'][:30]:<30} | Độ sâu: {d['depth']} tầng"
            )

    wl = rep["waitlist"]
    print(f"\n{sub_sep}")
    print("3. THỐNG KÊ HÀNG CHỜ (WAITLIST):")
    print(f"  - Tổng số lượt đang chờ:       {wl['total_waitlisted']}")
    print(f"  - Số lớp có hàng chờ:          {wl['offerings_with_waitlist']}")
    print(f"  - Thời gian chờ trung bình:    {wl['avg_wait_time_seconds']} giây")
    print(f"  - Thời gian chờ lâu nhất:      {wl['max_wait_time_seconds']} giây")
    if wl["longest_queues"]:
        print("  - Lớp có hàng chờ dài nhất:")
        for q in wl["longest_queues"]:
            print(f"    * {q['offering']:<12} -> {q['queue_length']} sinh viên chờ")

    inv = rep["invariants"]
    print(f"\n{sub_sep}")
    print("4. KIỂM TRA BẤT BIẾN TOÀN VẸN (INVARIANTS):")
    if inv["is_valid"]:
        print("  ✓ TẤT CẢ CÁC BẤT BIẾN TOÀN VẸN ĐỀU ĐẠT (0 vi phạm)!")
    else:
        print(f"  ✗ PHÁT HIỆN {inv['violations_count']} VI PHẠM:")
        for v in inv["violations"]:
            print(f"    * [{v['invariant']}]: {v['message']}")
    print(sep)


async def main_async(args: argparse.Namespace) -> int:
    settings = get_settings()
    url = args.database_url or os.environ.get("DATABASE_URL") or settings.database_url
    if not url:
        logger.error("Thiếu DATABASE_URL")
        return 1
    if os.path.exists("/.dockerenv"):
        url = url.replace("@localhost:5433", "@db:5432").replace(
            "@127.0.0.1:5433", "@db:5432"
        )

    engine = create_async_engine(url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        if args.check_only:
            violations = await find_invariant_violations(session)
            if violations:
                print(f"Có {len(violations)} vi phạm bất biến:")
                for v in violations:
                    print(f"  - [{v.invariant}]: {v.message}")
                return 1
            print("Toàn vẹn dữ liệu: 100% ĐẠT.")
            return 0

        report_data = await generate_full_report(session)

    await engine.dispose()

    if args.json:
        print(json.dumps(report_data, ensure_ascii=False, indent=2))
    else:
        print_text_report(report_data)

    if args.exit_on_violation and not report_data["invariants"]["is_valid"]:
        return 1
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Báo cáo thống kê cơ sở dữ liệu & bất biến toàn vẹn (M4)"
    )
    parser.add_argument(
        "--json", action="store_true", help="Xuất kết quả dưới định dạng JSON"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Chỉ kiểm tra tính bất biến toàn vẹn",
    )
    parser.add_argument(
        "--exit-on-violation",
        action="store_true",
        help="Trả về mã lỗi khác 0 nếu có vi phạm bất biến",
    )
    parser.add_argument(
        "--database-url", default=None, help="URL kết nối cơ sở dữ liệu PostgreSQL"
    )
    sys.exit(asyncio.run(main_async(parser.parse_args())))


if __name__ == "__main__":
    main()
