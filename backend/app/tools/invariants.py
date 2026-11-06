"""Read-only integrity checks for enrollment, waitlist, and prerequisite data.

Run with ``python -m app.tools.invariants`` from the backend directory.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import time
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    CompletedCourse,
    Course,
    CourseOffering,
    Enrollment,
    Prerequisite,
    Student,
    Waitlist,
)
from app.services.prerequisite_engine import PrerequisiteGraph, evaluate


@dataclass(frozen=True)
class InvariantViolation:
    invariant: str
    message: str
    context: dict[str, Any]


def _parse_time(value: str) -> time:
    return time.fromisoformat(value)


def find_snapshot_violations(
    snapshot: dict[str, list[dict[str, Any]]],
) -> list[InvariantViolation]:
    """Check normalized rows in memory; useful for states DB constraints reject."""
    offerings = {row["id"]: row for row in snapshot["offerings"]}
    courses = {row["id"]: row for row in snapshot["courses"]}
    students = {row["id"]: row for row in snapshot["students"]}
    enrollments = snapshot["enrollments"]
    waitlist = snapshot["waitlist"]
    completed = defaultdict(set)
    for row in snapshot["completed"]:
        completed[row["student_id"]].add(row["course_id"])
    graph = PrerequisiteGraph.from_edges(
        [
            (row["course_id"], row["prereq_course_id"], row["type"], row["group_no"])
            for row in snapshot["prerequisites"]
        ]
    )

    violations: list[InvariantViolation] = []
    active = [row for row in enrollments if row["status"] == "ACTIVE"]
    active_by_offering = defaultdict(list)
    active_by_student_term = defaultdict(list)
    seen_student_offering = set()

    for row in active:
        offering = offerings.get(row["offering_id"])
        if offering is None:
            continue
        active_by_offering[offering["id"]].append(row)
        student = students.get(row["student_id"])
        course = courses.get(offering["course_id"])
        if student and course:
            active_by_student_term[(student["id"], offering["term"])].append(
                (row, offering, course)
            )

        key = (row["student_id"], row["offering_id"])
        if key in seen_student_offering:
            violations.append(
                InvariantViolation(
                    "I3",
                    "Duplicate ACTIVE enrollment for student and offering.",
                    {"student_id": key[0], "offering_id": key[1]},
                )
            )
        seen_student_offering.add(key)

        if course is not None:
            result = evaluate(graph, course["id"], completed[row["student_id"]])
            if not result.eligible:
                violations.append(
                    InvariantViolation(
                        "I9",
                        "ACTIVE enrollment does not satisfy prerequisites.",
                        {
                            "student_id": row["student_id"],
                            "offering_id": offering["id"],
                            "course_id": course["id"],
                            "missing_courses": result.missing_courses,
                            "unmet_or_groups": [
                                {
                                    "group_no": group.group_no,
                                    "options": group.options,
                                }
                                for group in result.unmet_or_groups
                            ],
                        },
                    )
                )

    for offering_id, offering in offerings.items():
        current = active_by_offering[offering_id]
        count = len(current)
        if count > offering["capacity"]:
            violations.append(
                InvariantViolation(
                    "I1",
                    "ACTIVE enrollment count exceeds offering capacity.",
                    {
                        "offering_id": offering_id,
                        "active_count": count,
                        "capacity": offering["capacity"],
                    },
                )
            )
        if offering["enrolled_count"] != count:
            violations.append(
                InvariantViolation(
                    "I2",
                    "enrolled_count does not match ACTIVE enrollments.",
                    {
                        "offering_id": offering_id,
                        "enrolled_count": offering["enrolled_count"],
                        "active_count": count,
                    },
                )
            )

    for (student_id, term), rows in active_by_student_term.items():
        total_credits = sum(course["credits"] for _, _, course in rows)
        max_credits = students[student_id]["max_credits"]
        if total_credits > max_credits:
            violations.append(
                InvariantViolation(
                    "I4",
                    "ACTIVE credits exceed student limit for term.",
                    {
                        "student_id": student_id,
                        "term": term,
                        "credits": total_credits,
                        "max_credits": max_credits,
                    },
                )
            )

        for index, (first, first_offering, _) in enumerate(rows):
            first_days = first_offering["schedule"]
            for second, second_offering, _ in rows[index + 1 :]:
                for a in first_days:
                    for b in second_offering["schedule"]:
                        if a.get("day") != b.get("day"):
                            continue
                        try:
                            overlaps = _parse_time(a["start"]) < _parse_time(
                                b["end"]
                            ) and _parse_time(b["start"]) < _parse_time(a["end"])
                        except (KeyError, TypeError, ValueError):
                            violations.append(
                                InvariantViolation(
                                    "I5",
                                    "Offering schedule has an invalid day or time interval.",
                                    {
                                        "offering_ids": [
                                            first_offering["id"],
                                            second_offering["id"],
                                        ]
                                    },
                                )
                            )
                            continue
                        if overlaps:
                            violations.append(
                                InvariantViolation(
                                    "I5",
                                    "Student has overlapping ACTIVE class schedules.",
                                    {
                                        "student_id": student_id,
                                        "term": term,
                                        "offering_ids": [
                                            first_offering["id"],
                                            second_offering["id"],
                                        ],
                                        "enrollment_ids": [
                                            first["id"],
                                            second["id"],
                                        ],
                                        "day": a["day"],
                                    },
                                )
                            )

    queues = defaultdict(list)
    waiting_keys = set()
    for row in waitlist:
        queues[row["offering_id"]].append(row)
        waiting_keys.add((row["student_id"], row["offering_id"]))
    for offering_id, rows in queues.items():
        ordered = sorted(rows, key=lambda item: (item["enqueued_at"], item["id"]))
        positions = sorted(row["position"] for row in rows)
        if positions != list(range(1, len(rows) + 1)) or any(
            row["position"] != index for index, row in enumerate(ordered, start=1)
        ):
            violations.append(
                InvariantViolation(
                    "I6",
                    "Waitlist positions are not contiguous FIFO order.",
                    {
                        "offering_id": offering_id,
                        "ordered_ids": [row["id"] for row in ordered],
                        "positions": positions,
                    },
                )
            )

    for row in active:
        if (row["student_id"], row["offering_id"]) in waiting_keys:
            violations.append(
                InvariantViolation(
                    "I7",
                    "Student is both ACTIVE and waitlisted for the same offering.",
                    {
                        "student_id": row["student_id"],
                        "offering_id": row["offering_id"],
                    },
                )
            )

    return violations


async def find_invariant_violations(session: AsyncSession) -> list[InvariantViolation]:
    """Read current database state and return violations without modifying it."""
    students = (await session.scalars(select(Student))).all()
    courses = (await session.scalars(select(Course))).all()
    offerings = (await session.scalars(select(CourseOffering))).all()
    enrollments = (await session.scalars(select(Enrollment))).all()
    waitlist = (await session.scalars(select(Waitlist))).all()
    completed = (await session.scalars(select(CompletedCourse))).all()
    prerequisites = (await session.scalars(select(Prerequisite))).all()
    snapshot = {
        "students": [
            {"id": row.id, "max_credits": row.max_credits} for row in students
        ],
        "courses": [{"id": row.id, "credits": row.credits} for row in courses],
        "offerings": [
            {
                "id": row.id,
                "course_id": row.course_id,
                "term": row.term,
                "capacity": row.capacity,
                "enrolled_count": row.enrolled_count,
                "schedule": row.schedule,
            }
            for row in offerings
        ],
        "enrollments": [
            {
                "id": row.id,
                "student_id": row.student_id,
                "offering_id": row.offering_id,
                "status": row.status,
            }
            for row in enrollments
        ],
        "waitlist": [
            {
                "id": row.id,
                "student_id": row.student_id,
                "offering_id": row.offering_id,
                "position": row.position,
                "enqueued_at": row.enqueued_at,
            }
            for row in waitlist
        ],
        "completed": [
            {"student_id": row.student_id, "course_id": row.course_id}
            for row in completed
        ],
        "prerequisites": [
            {
                "course_id": row.course_id,
                "prereq_course_id": row.prereq_course_id,
                "type": row.type,
                "group_no": row.group_no,
            }
            for row in prerequisites
        ],
    }
    return find_snapshot_violations(snapshot)


async def _run_cli() -> int:
    from app.core.db import _get_session_factory

    factory = _get_session_factory()
    async with factory() as session:
        violations = await find_invariant_violations(session)
    bind = factory.kw.get("bind")
    if bind is not None:
        await bind.dispose()

    print(json.dumps([asdict(item) for item in violations], indent=2, default=str))
    print(
        "Deferred by unresolved group decisions: I8 (D12 waitlist rounding), "
        "I10 (D10 same-course enrollment)."
    )
    print(f"Found {len(violations)} invariant violation(s).")
    return 1 if violations else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    return asyncio.run(_run_cli())


if __name__ == "__main__":
    raise SystemExit(main())
