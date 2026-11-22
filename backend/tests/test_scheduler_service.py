"""Unit tests cho thuật toán Gợi ý xếp lịch tự động (Smart Auto-Scheduler)."""

import pytest

from app.schemas.scheduler import SchedulerPreferences
from app.services.scheduler_service import (
    classify_tdtu_shift,
    solve_schedules,
)

pytestmark = pytest.mark.unit


def _off(oid: int, cid: int, code: str, sec: str, day: int, start: str, end: str):
    return {
        "id": oid,
        "course_id": cid,
        "code": code,
        "name": f"Course {code}",
        "credits": 3,
        "min_accumulated_credits": 0,
        "term": "2026-2",
        "section": sec,
        "instructor": "GV A",
        "room": "A1-101",
        "schedule": [{"day": day, "start": start, "end": end}],
        "capacity": 40,
        "enrolled_count": 5,
        "in_study_plan": True,
    }


@pytest.mark.parametrize(
    ("start", "expected_shift"),
    [
        ("06:50", 1),
        ("09:30", 2),
        ("12:45", 3),
        ("15:25", 4),
        ("18:05", 5),
    ],
)
def test_classify_tdtu_shift(start, expected_shift):
    assert classify_tdtu_shift(start) == expected_shift


def test_solve_schedules_avoids_conflicts_and_existing_classes():
    existing = [
        _off(100, 99, "BAS101", "01", day=1, start="06:50", end="09:20"),
    ]
    candidates = {
        1: [
            # Trùng với BAS101 (T2 Ca 1) -> phải bị cắt tỉa
            _off(1, 1, "INT131", "01", day=1, start="06:50", end="09:20"),
            # Hợp lệ (T2 Ca 2)
            _off(2, 1, "INT131", "02", day=1, start="09:30", end="12:00"),
        ],
        2: [
            # Trùng với INT131-02 (T2 Ca 2)
            _off(3, 2, "INT201", "01", day=1, start="09:30", end="12:00"),
            # Hợp lệ (T3 Ca 2)
            _off(4, 2, "INT201", "02", day=2, start="09:30", end="12:00"),
        ],
    }

    plans = solve_schedules(existing, candidates, SchedulerPreferences())
    assert len(plans) == 1
    chosen_ids = {o["id"] for o in plans[0]["offerings"]}
    assert chosen_ids == {2, 4}
    assert plans[0]["added_credits"] == 6


def test_solve_schedules_ranks_by_avoid_shift_1_and_saturday():
    candidates = {
        1: [
            _off(1, 1, "INT131", "01", day=6, start="06:50", end="09:20"),  # T7 Ca 1
            _off(2, 1, "INT131", "02", day=2, start="09:30", end="12:00"),  # T3 Ca 2
        ],
        2: [
            _off(3, 2, "INT201", "01", day=2, start="12:45", end="15:15"),  # T3 Ca 3
            _off(4, 2, "INT201", "02", day=4, start="06:50", end="09:20"),  # T5 Ca 1
        ],
    }

    prefs = SchedulerPreferences(
        avoid_first_shift=True,
        avoid_saturday=True,
        minimize_days=True,
    )
    plans = solve_schedules([], candidates, prefs, max_results=3)
    assert len(plans) == 3
    # Phương án tốt nhất phải chọn INT131-02 (T3 Ca 2) + INT201-01 (T3 Ca 3) -> chỉ 1 ngày, không Ca 1, nghỉ T7
    top_ids = {o["id"] for o in plans[0]["offerings"]}
    assert top_ids == {2, 3}
    assert plans[0]["study_days_count"] == 1
    assert "Không có Ca 1" in plans[0]["tags"]
    assert "Nghỉ Thứ 7" in plans[0]["tags"]


def test_solve_schedules_returns_empty_when_impossible():
    candidates = {
        1: [_off(1, 1, "INT131", "01", day=1, start="09:30", end="12:00")],
        2: [_off(2, 2, "INT201", "01", day=1, start="09:30", end="12:00")],
    }
    assert solve_schedules([], candidates, SchedulerPreferences()) == []
