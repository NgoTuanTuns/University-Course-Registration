"""Unit tests cho quy trình Đăng ký Kế hoạch Học tập (ĐKKHHT) & Mở lớp theo nhu cầu."""

from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.core.config import get_settings
from app.seed_data import MIN_PLAN_STUDENTS_TO_OPEN, STUDY_PLAN_TERM, build_dataset
from app.services.enrollment_queries import rank_courses_for_student
from app.services.study_plan_service import (
    add_course_to_study_plan,
    remove_course_from_study_plan,
)

pytestmark = pytest.mark.unit


def test_seed_default_generates_study_plans_and_both_opening_states():
    ds = build_dataset("default")
    assert len(ds.study_plans) > 3000
    assert {sp.term for sp in ds.study_plans} == {STUDY_PLAN_TERM}

    opened = [op for op in ds.course_openings if op.status == "OPENED"]
    not_opened = [op for op in ds.course_openings if op.status == "NOT_OPENED"]
    assert len(opened) > 30
    assert len(not_opened) >= 8

    # Không có CourseOffering nào trong kỳ 2026-2 thuộc môn NOT_OPENED
    not_opened_codes = {op.course_code for op in not_opened}
    for off in ds.offerings:
        assert off.course_code not in not_opened_codes

    # Tài khoản demo sv0587 phải là sinh viên năm 3 Khoa CNTT và có cả môn OPENED lẫn NOT_OPENED
    from app.core.faculty import FACULTY_CNTT

    sv587 = next(s for s in ds.students if s.email == "sv0587@uni.edu.vn")
    assert sv587.faculty == FACULTY_CNTT
    assert 40 <= sv587.accumulated_credits <= 59

    op_map = {op.course_code: op for op in ds.course_openings}
    sv587_codes = [
        sp.course_code
        for sp in ds.study_plans
        if sp.student_email == "sv0587@uni.edu.vn"
    ]
    assert len(sv587_codes) >= 4
    assert any(op_map[c].status == "OPENED" for c in sv587_codes)
    assert any(op_map[c].status == "NOT_OPENED" for c in sv587_codes)
    for op in not_opened:
        assert op.planned_count < MIN_PLAN_STUDENTS_TO_OPEN

    # Môn có nhiều SV ĐKKHHT phải tự động mở nhiều lớp (ceil(planned_count / 40))
    import math

    sections_by_code: dict[str, list[str]] = {}
    for off in ds.offerings:
        sections_by_code.setdefault(off.course_code, []).append(off.section)
    high_demand = [op for op in opened if op.planned_count > 40]
    assert len(high_demand) > 10
    for op in high_demand:
        expected_min = math.ceil(op.planned_count / 40)
        assert len(sections_by_code.get(op.course_code, [])) >= expected_min, (
            op.course_code,
            op.planned_count,
            sections_by_code.get(op.course_code, []),
        )


@pytest.mark.asyncio
async def test_study_plan_add_and_remove_blocked_when_period_closed(monkeypatch):
    monkeypatch.setenv("STUDY_PLAN_EDITABLE", "false")
    get_settings.cache_clear()
    try:
        session = AsyncMock()
        with pytest.raises(HTTPException) as add_exc:
            await add_course_to_study_plan(session, student_id=1, course_id=1)
        assert add_exc.value.status_code == 403
        assert add_exc.value.detail["code"] == "STUDY_PLAN_PERIOD_CLOSED"

        with pytest.raises(HTTPException) as del_exc:
            await remove_course_from_study_plan(session, student_id=1, plan_id=1)
        assert del_exc.value.status_code == 403
        assert del_exc.value.detail["code"] == "STUDY_PLAN_PERIOD_CLOSED"
    finally:
        get_settings.cache_clear()


def test_rank_courses_prioritizes_study_plan_courses_first():
    courses = [
        (1, "INT321", 24),  # Đúng năm 3 nhưng không nằm trong KHHT
        (2, "MAT201", 3),  # Nằm trong KHHT của sinh viên -> phải lên đầu tiên!
        (3, "INT101", 0),  # Đã hoàn thành -> cuối cùng
    ]
    rank_map, status_map = rank_courses_for_student(
        courses,
        accumulated_credits=50,
        completed_ids={3},
        prereq_rows=[],
        planned_ids={2},
    )
    assert status_map[2] == "RECOMMENDED"
    assert status_map[1] == "RECOMMENDED"
    assert status_map[3] == "COMPLETED"
    assert rank_map[2] < rank_map[1] < rank_map[3]
