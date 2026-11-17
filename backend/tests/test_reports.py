"""Kiểm thử bộ công cụ báo cáo thống kê cơ sở dữ liệu - app.reports (M4, Tuần 4)."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models import Course
from app.reports import (
    generate_full_report,
    get_dag_structure_stats,
    get_offering_capacity_stats,
    get_waitlist_stats,
)

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_get_offering_capacity_stats():
    session = AsyncMock()
    mock_row1 = MagicMock(
        id=1,
        term="2026-1",
        section="01",
        capacity=50,
        enrolled_count=50,
        course_code="INT131",
        course_name="Cấu trúc dữ liệu",
        waitlist_count=3,
    )
    mock_row2 = MagicMock(
        id=2,
        term="2026-1",
        section="02",
        capacity=50,
        enrolled_count=42,
        course_code="INT101",
        course_name="Nhập môn lập trình",
        waitlist_count=0,
    )

    mock_res = MagicMock()
    mock_res.all.return_value = [mock_row1, mock_row2]
    session.execute.return_value = mock_res

    stats = await get_offering_capacity_stats(session)
    assert stats["total_offerings"] == 2
    assert stats["total_capacity"] == 100
    assert stats["total_enrolled"] == 92
    assert stats["overall_fill_rate_pct"] == 92.0
    assert stats["full_count"] == 1
    assert stats["nearly_full_count"] == 1


@pytest.mark.asyncio
async def test_get_dag_structure_stats():
    session = AsyncMock()

    mock_edge1 = MagicMock(course_id=2, prereq_course_id=1, type="AND", group_no=0)
    mock_edge2 = MagicMock(course_id=3, prereq_course_id=2, type="OR", group_no=1)

    edges_res = MagicMock()
    edges_res.all.return_value = [mock_edge1, mock_edge2]

    depth_row1 = MagicMock(course_id=3, code="INT431", name="Đồ án", max_depth=3)
    depth_res = MagicMock()
    depth_res.all.return_value = [depth_row1]

    session.execute.side_effect = [edges_res, depth_res]

    c = Course(id=2, code="INT131", name="Cấu trúc dữ liệu", credits=3)
    session.get = AsyncMock(return_value=c)

    stats = await get_dag_structure_stats(session)
    assert stats["total_edges"] == 2
    assert stats["and_edges"] == 1
    assert stats["or_edges"] == 1
    assert stats["distinct_or_groups"] == 1
    assert stats["max_dag_depth"] == 3
    assert len(stats["deepest_courses"]) == 1


@pytest.mark.asyncio
async def test_get_waitlist_stats():
    session = AsyncMock()
    now = datetime.now(UTC)

    mock_w1 = MagicMock(
        id=1,
        offering_id=10,
        student_id=1,
        position=1,
        enqueued_at=now,
        course_code="INT331",
        section="01",
        mssv="20000001",
        full_name="Nguyễn Văn A",
    )
    mock_res = MagicMock()
    mock_res.all.return_value = [mock_w1]
    session.execute.return_value = mock_res

    stats = await get_waitlist_stats(session)
    assert stats["total_waitlisted"] == 1
    assert stats["offerings_with_waitlist"] == 1
    assert len(stats["longest_queues"]) == 1
    assert stats["longest_queues"][0]["offering"] == "INT331-01"


@pytest.mark.asyncio
async def test_generate_full_report():
    session = AsyncMock()

    with (
        patch(
            "app.reports.get_offering_capacity_stats",
            new_callable=AsyncMock,
            return_value={"total_offerings": 10},
        ),
        patch(
            "app.reports.get_dag_structure_stats",
            new_callable=AsyncMock,
            return_value={"total_edges": 15},
        ),
        patch(
            "app.reports.get_waitlist_stats",
            new_callable=AsyncMock,
            return_value={"total_waitlisted": 5},
        ),
        patch(
            "app.reports.find_invariant_violations",
            new_callable=AsyncMock,
            return_value=[],
        ),
    ):
        report = await generate_full_report(session)
        assert report["capacity"]["total_offerings"] == 10
        assert report["dag"]["total_edges"] == 15
        assert report["waitlist"]["total_waitlisted"] == 5
        assert report["invariants"]["is_valid"] is True
        assert report["invariants"]["violations_count"] == 0
