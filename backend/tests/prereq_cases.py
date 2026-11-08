"""Bảng ca nghiệm thu tiên quyết (M2 × M5, Mục 6.1) dùng chung cho mọi file test.

Đồ thị mẫu ("X cần Y"; `OR g1 {...}` là nhóm "hoặc" số 1):
  A1, A2, A3: không có tiên quyết
  B1 cần A1; B2 cần A1; C1 cần B1; D1 cần B1 và B2 (kim cương)
  E1 cần OR g1 {A2, A3}; F1 cần C1 và OR g1 {A2, A3}
  G1 cần OR g1 {A2, A3} và OR g2 {B1, B2}; H1 cần OR g1 {C1, E1}
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CompletedCourse, Course, Prerequisite

ACCEPTANCE_EDGES = [
    ("B1", "A1", "AND", 0),
    ("B2", "A1", "AND", 0),
    ("C1", "B1", "AND", 0),
    ("D1", "B1", "AND", 0),
    ("D1", "B2", "AND", 0),
    ("E1", "A2", "OR", 1),
    ("E1", "A3", "OR", 1),
    ("F1", "C1", "AND", 0),
    ("F1", "A2", "OR", 1),
    ("F1", "A3", "OR", 1),
    ("G1", "A2", "OR", 1),
    ("G1", "A3", "OR", 1),
    ("G1", "B1", "OR", 2),
    ("G1", "B2", "OR", 2),
    ("H1", "C1", "OR", 1),
    ("H1", "E1", "OR", 1),
]

ACCEPTANCE_CODES = sorted(
    {c for e in ACCEPTANCE_EDGES for c in (e[0], e[1])} | {"A1", "A2", "A3"}
)

# (số ca, đã học, môn xét, eligible, tập môn thiếu, {group_no: lựa chọn} chưa đạt)
# Ca #6 phụ thuộc D04 ("đã học là đủ"); ca #21 (môn không tồn tại) chỉ có ở mức API.
ACCEPTANCE_CASES = [
    (1, set(), "A1", True, set(), {}),
    (2, set(), "B1", False, {"A1"}, {}),
    (3, {"A1"}, "B1", True, set(), {}),
    (4, set(), "C1", False, {"B1", "A1"}, {}),
    (5, {"A1"}, "C1", False, {"B1"}, {}),
    (6, {"B1"}, "C1", True, set(), {}),
    (7, {"A1"}, "D1", False, {"B1", "B2"}, {}),
    (8, set(), "D1", False, {"B1", "B2", "A1"}, {}),
    (9, {"A1", "B1", "B2"}, "D1", True, set(), {}),
    (10, set(), "E1", False, set(), {1: {"A2", "A3"}}),
    (11, {"A3"}, "E1", True, set(), {}),
    (12, {"A2", "A3"}, "E1", True, set(), {}),
    (13, {"A2"}, "F1", False, {"C1", "B1", "A1"}, {}),
    (14, {"A1", "B1", "C1"}, "F1", False, set(), {1: {"A2", "A3"}}),
    (15, {"A1", "B1", "C1", "A2"}, "F1", True, set(), {}),
    (16, {"A2"}, "G1", False, set(), {2: {"B1", "B2"}}),
    (17, {"A2", "B2"}, "G1", True, set(), {}),
    (18, {"B1"}, "G1", False, set(), {1: {"A2", "A3"}}),
    (19, {"C1"}, "H1", True, set(), {}),
    (20, {"E1"}, "H1", True, set(), {}),
]

# (số ca, môn, tiên quyết thêm vào, đường đi vòng mong đợi hoặc None nếu chấp nhận)
CYCLE_CASES = [
    ("C1", "A1", "B1", ["A1", "B1", "A1"]),
    ("C2", "A1", "C1", ["A1", "C1", "B1", "A1"]),
    ("C3", "B1", "B1", ["B1", "B1"]),
    ("C4", "D1", "A2", None),
    ("C5", "C1", "A1", None),
]


ACCEPTANCE_IDS = [f"case{c[0]}" for c in ACCEPTANCE_CASES]
CYCLE_IDS = [str(c[0]) for c in CYCLE_CASES]


async def seed_acceptance_graph(session: AsyncSession) -> dict[str, Course]:
    """Ghi đồ thị mẫu vào DB test (dùng mã môn có tiền tố để không trùng seed)."""
    courses = {
        code: Course(code=f"ACC{code}", name=f"Môn {code}", credits=3)
        for code in ACCEPTANCE_CODES
    }
    session.add_all(courses.values())
    await session.flush()
    session.add_all(
        Prerequisite(
            course_id=courses[c].id,
            prereq_course_id=courses[p].id,
            type=t,
            group_no=g,
        )
        for c, p, t, g in ACCEPTANCE_EDGES
    )
    await session.flush()
    return courses


async def mark_completed(
    session: AsyncSession, student_id: int, courses: list[Course]
) -> None:
    session.add_all(
        CompletedCourse(student_id=student_id, course_id=c.id, grade=8.0, term="2025-1")
        for c in courses
    )
    await session.flush()
