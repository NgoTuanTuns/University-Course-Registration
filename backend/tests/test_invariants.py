from datetime import UTC, datetime, timedelta

import pytest

from app.tools.invariants import find_invariant_violations, find_snapshot_violations


def clean_snapshot():
    return {
        "students": [{"id": 1, "max_credits": 25}],
        "courses": [{"id": 10, "credits": 3}, {"id": 11, "credits": 3}],
        "offerings": [
            {
                "id": 100,
                "course_id": 10,
                "term": "2026-1",
                "capacity": 2,
                "enrolled_count": 1,
                "schedule": [{"day": 1, "start": "09:00", "end": "10:00"}],
            },
            {
                "id": 101,
                "course_id": 11,
                "term": "2026-1",
                "capacity": 2,
                "enrolled_count": 0,
                "schedule": [{"day": 1, "start": "10:00", "end": "11:00"}],
            },
        ],
        "enrollments": [
            {"id": 1, "student_id": 1, "offering_id": 100, "status": "ACTIVE"}
        ],
        "waitlist": [],
        "completed": [],
        "prerequisites": [],
    }


@pytest.mark.unit
def test_clean_snapshot_has_no_violations_and_adjacent_classes_do_not_overlap():
    assert find_snapshot_violations(clean_snapshot()) == []


@pytest.mark.unit
@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        (lambda data: data["offerings"][0].update(capacity=0), "I1"),
        (lambda data: data["offerings"][0].update(enrolled_count=0), "I2"),
        (
            lambda data: data["enrollments"].append(
                {"id": 2, "student_id": 1, "offering_id": 100, "status": "ACTIVE"}
            ),
            "I3",
        ),
        (
            lambda data: (
                data["students"][0].update(max_credits=5),
                data["courses"][1].update(credits=4),
                data["offerings"][1].update(enrolled_count=1),
                data["enrollments"].append(
                    {"id": 2, "student_id": 1, "offering_id": 101, "status": "ACTIVE"}
                ),
            ),
            "I4",
        ),
        (
            lambda data: (
                data["offerings"][1]["schedule"][0].update(start="09:30"),
                data["offerings"][1].update(enrolled_count=1),
                data["enrollments"].append(
                    {"id": 2, "student_id": 1, "offering_id": 101, "status": "ACTIVE"}
                ),
            ),
            "I5",
        ),
        (
            lambda data: data["waitlist"].append(
                {
                    "id": 1,
                    "student_id": 1,
                    "offering_id": 100,
                    "position": 2,
                    "enqueued_at": datetime.now(UTC),
                }
            ),
            "I6",
        ),
        (
            lambda data: data["waitlist"].append(
                {
                    "id": 1,
                    "student_id": 1,
                    "offering_id": 100,
                    "position": 1,
                    "enqueued_at": datetime.now(UTC),
                }
            ),
            "I7",
        ),
        (
            lambda data: (
                data["prerequisites"].append(
                    {
                        "course_id": 10,
                        "prereq_course_id": 11,
                        "type": "AND",
                        "group_no": 0,
                    }
                ),
                data["offerings"][0].update(enrolled_count=1),
            ),
            "I9",
        ),
    ],
)
def test_snapshot_detects_each_decided_invariant(mutate, expected):
    data = clean_snapshot()
    mutate(data)
    assert expected in {item.invariant for item in find_snapshot_violations(data)}


@pytest.mark.unit
def test_waitlist_fifo_uses_enqueue_time_then_id():
    data = clean_snapshot()
    now = datetime.now(UTC)
    data["waitlist"] = [
        {
            "id": 2,
            "student_id": 2,
            "offering_id": 100,
            "position": 1,
            "enqueued_at": now + timedelta(seconds=1),
        },
        {
            "id": 1,
            "student_id": 3,
            "offering_id": 100,
            "position": 2,
            "enqueued_at": now,
        },
    ]
    assert "I6" in {item.invariant for item in find_snapshot_violations(data)}


@pytest.mark.integration
async def test_database_checker_reports_clean_isolated_database(test_session):
    assert await find_invariant_violations(test_session) == []
