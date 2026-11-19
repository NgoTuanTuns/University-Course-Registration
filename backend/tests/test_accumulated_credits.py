"""Unit tests cho ràng buộc tín chỉ tích lũy, dữ liệu sinh viên/môn học và API DAG graph."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.seed_data import build_dataset, validate_dataset
from app.services.enrollment_service import ensure_eligible

pytestmark = pytest.mark.unit


def test_seed_level1_courses_require_zero_accumulated_credits():
    ds = build_dataset("default")
    assert validate_dataset(ds) == []

    level1 = [c for c in ds.courses if c.level == 1]
    assert len(level1) >= 11
    for c in level1:
        assert c.min_accumulated_credits == 0, c.code

    higher = [c for c in ds.courses if c.level >= 2]
    assert all(c.min_accumulated_credits > 0 for c in higher)


def test_seed_students_accumulated_credits_matches_completed_courses():
    ds = build_dataset("default")
    credits_by_code = {c.code: c.credits for c in ds.courses}
    expected: dict[str, int] = {}
    for comp in ds.completed:
        expected[comp.student_email] = (
            expected.get(comp.student_email, 0) + credits_by_code[comp.course_code]
        )

    for s in ds.students:
        assert s.accumulated_credits == expected.get(s.email, 0), s.email

    # sv0055 là tân sinh viên năm nhất 0 tín chỉ tích lũy
    sv55 = next(s for s in ds.students if s.email == "sv0055@uni.edu.vn")
    assert sv55.accumulated_credits == 0


@pytest.mark.asyncio
async def test_ensure_eligible_blocks_when_accumulated_credits_below_minimum(
    monkeypatch,
):
    session = AsyncMock()
    session.get = AsyncMock(return_value=None)  # chưa completed

    exec_result = MagicMock()
    exec_result.one_or_none.return_value = (3, 15)  # credits=3, min_acc=15
    session.execute = AsyncMock(return_value=exec_result)

    monkeypatch.setattr(
        "app.services.enrollment_service.active_items",
        AsyncMock(return_value=[]),
    )

    student = SimpleNamespace(id=55, max_credits=25, accumulated_credits=0)
    offering = SimpleNamespace(id=1, course_id=10, term="2026-1", schedule=[])

    with pytest.raises(HTTPException) as exc_info:
        await ensure_eligible(session, student, offering)  # type: ignore[arg-type]

    assert exc_info.value.status_code == 422
    detail = exc_info.value.detail
    assert detail["code"] == "MIN_ACCUMULATED_CREDITS_NOT_MET"
    assert detail["required_credits"] == 15
    assert detail["current_credits"] == 0


@pytest.mark.asyncio
async def test_ensure_eligible_allows_freshman_for_zero_min_credit_course(monkeypatch):
    session = AsyncMock()
    session.get = AsyncMock(return_value=None)

    exec_result = MagicMock()
    exec_result.one_or_none.return_value = (3, 0)  # credits=3, min_acc=0 (năm 1)
    session.execute = AsyncMock(return_value=exec_result)

    monkeypatch.setattr(
        "app.services.enrollment_service.active_items",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        "app.services.enrollment_service.check_eligibility",
        AsyncMock(return_value=SimpleNamespace(eligible=True, missing_courses=[])),
    )

    student = SimpleNamespace(id=55, max_credits=25, accumulated_credits=0)
    offering = SimpleNamespace(id=1, course_id=1, term="2026-1", schedule=[])

    # Không raise exception -> hợp lệ
    await ensure_eligible(session, student, offering)  # type: ignore[arg-type]


def test_faculty_isolation_for_cntt_students():
    from app.core.faculty import FACULTY_CNTT, course_allowed_for_faculty

    assert course_allowed_for_faculty("INT101", FACULTY_CNTT) is True
    assert course_allowed_for_faculty("BAS101", FACULTY_CNTT) is True
    assert course_allowed_for_faculty("MAT201", FACULTY_CNTT) is True
    assert course_allowed_for_faculty("PHY101", FACULTY_CNTT) is True
    assert course_allowed_for_faculty("ENG101", FACULTY_CNTT) is True
    # Không hiển thị môn khoa khác (Điện - Điện tử, Quản trị kinh doanh)
    assert course_allowed_for_faculty("ELE101", FACULTY_CNTT) is False
    assert course_allowed_for_faculty("MAN101", FACULTY_CNTT) is False

    ds = build_dataset("default")
    cntt_emails = {s.email for s in ds.students if s.faculty == FACULTY_CNTT}
    assert "sv0001@uni.edu.vn" in cntt_emails
    assert "sv0055@uni.edu.vn" in cntt_emails
    for comp in ds.completed:
        if comp.student_email in cntt_emails:
            assert course_allowed_for_faculty(comp.course_code, FACULTY_CNTT), (
                comp.student_email,
                comp.course_code,
            )


def test_course_ranking_prioritizes_eligible_on_pace_courses():
    from app.services.enrollment_queries import (
        rank_courses_for_student,
        student_academic_year,
    )

    # Sinh viên năm 3 có 48 tín chỉ tích lũy
    assert student_academic_year(48) == 3

    courses = [
        (1, "INT101", 0),  # Đã hoàn thành -> cuối danh sách
        (2, "BAS101", 0),  # Đủ điều kiện nhưng là môn năm 1 -> ELIGIBLE (nhóm 1)
        (
            3,
            "INT321",
            24,
        ),  # Đủ TC + đủ tiên quyết INT101 + đúng năm 3 -> RECOMMENDED (nhóm 0)
        (4, "INT451", 60),  # Chưa đủ TC (cần 60 > 48) -> LOCKED (nhóm 2)
        (5, "INT331", 15),  # Thiếu tiên quyết (cần môn 99 chưa học) -> LOCKED (nhóm 2)
    ]
    completed_ids = {1}
    prereq_rows = [
        (3, 1, "AND", 0),  # INT321 cần INT101 (đã học)
        (5, 99, "AND", 0),  # INT331 cần môn 99 (chưa học)
    ]

    rank_map, status_map = rank_courses_for_student(
        courses,
        accumulated_credits=48,
        completed_ids=completed_ids,
        prereq_rows=prereq_rows,
    )

    assert status_map[3] == "RECOMMENDED"
    assert status_map[2] == "ELIGIBLE"
    assert status_map[4] == "LOCKED"
    assert status_map[5] == "LOCKED"
    assert status_map[1] == "COMPLETED"

    # Thứ tự phải đúng: RECOMMENDED < ELIGIBLE < LOCKED < COMPLETED
    assert rank_map[3] < rank_map[2] < rank_map[5] < rank_map[1]
    assert rank_map[2] < rank_map[4] < rank_map[1]
