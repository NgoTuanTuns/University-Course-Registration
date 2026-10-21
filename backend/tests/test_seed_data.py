"""Kiểm thử bộ dữ liệu seed (thuần Python, KHÔNG cần database).

Chạy:  cd backend && python -m pytest tests/test_seed_data.py
(nếu báo không import được `app`, thêm `pythonpath = .` vào pytest.ini / pyproject.toml)
"""
import math

import pytest

from app.seed_data import (
    ADMIN_EMAIL,
    TERM,
    Dataset,
    _requirements,
    _to_min,
    build_dataset,
    find_cycle,
    satisfies,
    validate_dataset,
)


@pytest.fixture(scope="module")
def minimal() -> Dataset:
    return build_dataset("minimal")


@pytest.fixture(scope="module")
def default() -> Dataset:
    return build_dataset("default")


def _completed(ds: Dataset, email: str) -> set[str]:
    return {r.course_code for r in ds.completed if r.student_email == email}


def _missing(ds: Dataset, email: str, target: str):
    """Môn AND chưa học (kèm đệ quy cho phần bắc cầu) và các nhóm OR chưa thỏa."""
    and_map, or_map = _requirements(ds.prereqs)
    done = _completed(ds, email)
    missing: list[str] = []
    queue = [target]
    unmet_or: list[tuple[str, int, list[str]]] = []
    seen = {target}
    while queue:
        cur = queue.pop(0)
        for g, opts in sorted(or_map.get(cur, {}).items()):
            if not any(o in done for o in opts):
                unmet_or.append((cur, g, sorted(opts)))
        for p in and_map.get(cur, []):
            if p not in done and p not in seen:
                seen.add(p)
                missing.append(p)
                queue.append(p)
    return missing, unmet_or


def _overlap(a: list[dict], b: list[dict]) -> bool:
    return any(
        x["day"] == y["day"] and _to_min(x["start"]) < _to_min(y["end"]) and _to_min(y["start"]) < _to_min(x["end"])
        for x in a
        for y in b
    )


# ------------------------------------------------------------------ nhất quán chung
@pytest.mark.parametrize("profile", ["minimal", "default"])
def test_dataset_valid(profile):
    assert validate_dataset(build_dataset(profile)) == []


def test_deterministic():
    a, b = build_dataset("default"), build_dataset("default")
    assert a.courses == b.courses and a.prereqs == b.prereqs and a.offerings == b.offerings
    assert a.students == b.students and a.completed == b.completed


def test_default_sizes(default):
    assert len(default.courses) == 200
    students = [s for s in default.students if s.role == "student"]
    assert len(students) == 1000
    assert sum(1 for s in default.students if s.role == "admin") == 1
    assert default.students[-1].email == ADMIN_EMAIL  # admin đặt cuối, sv000N có id = N
    assert default.students[0].email == "sv0001@uni.edu.vn"


def test_dag_depth_at_least_seven(default):
    """Chuỗi tiên quyết dài ít nhất 7 tầng (DAG đủ sâu cho benchmark của M2)."""
    and_map, or_map = _requirements(default.prereqs)
    depth: dict[str, int] = {}

    def d(code: str) -> int:
        if code in depth:
            return depth[code]
        parents = list(and_map.get(code, [])) + [o for opts in or_map.get(code, {}).values() for o in opts]
        depth[code] = 1 + max((d(p) for p in parents), default=0)
        return depth[code]

    assert max(d(c.code) for c in default.courses) >= 7


def test_has_or_groups_and_diamonds(default):
    assert sum(1 for p in default.prereqs if p.type == "OR") > 30
    assert find_cycle([(p.course_code, p.prereq_code) for p in default.prereqs]) is None


def test_cycle_detection_finds_cycles():
    assert find_cycle([("A", "B"), ("B", "C"), ("C", "A")]) is not None
    assert find_cycle([("A", "A")]) is not None
    assert find_cycle([("A", "B"), ("B", "C"), ("A", "C")]) is None


# ------------------------------------------------------------------ kit tiên quyết
def test_kit_chain_and_or_structure(minimal):
    and_map, or_map = _requirements(minimal.prereqs)
    assert and_map["INT431"] == ["INT331"] and and_map["INT331"] == ["INT231"]
    assert and_map["INT231"] == ["INT131"] and and_map["INT131"] == ["INT101"]
    assert sorted(and_map["INT321"]) == ["INT221", "INT222"]  # kim cương
    assert and_map["INT221"] == and_map["INT222"] == ["INT131"]
    assert or_map["INT341"] == {1: ["MAT201", "MAT202"]}
    assert or_map["INT451"] == {1: ["MAT201", "MAT202"], 2: ["INT221", "INT222"]}


def test_sv0001_eligible_for_int341(minimal):
    and_map, or_map = _requirements(minimal.prereqs)
    assert satisfies("INT341", _completed(minimal, "sv0001@uni.edu.vn"), and_map, or_map)


def test_sv0002_missing_transitive_for_int431(minimal):
    missing, _ = _missing(minimal, "sv0002@uni.edu.vn", "INT431")
    assert missing == ["INT331", "INT231", "INT131"]  # chuỗi bắc cầu, theo độ sâu tăng dần


def test_sv0002_int231_missing_only_int131(minimal):
    assert _missing(minimal, "sv0002@uni.edu.vn", "INT231")[0] == ["INT131"]


def test_sv0003_unmet_or_group_int341(minimal):
    missing, unmet = _missing(minimal, "sv0003@uni.edu.vn", "INT341")
    assert missing == []
    assert unmet == [("INT341", 1, ["MAT201", "MAT202"])]


def test_sv0009_sv0010_eligible_for_one_seat_class(minimal):
    and_map, or_map = _requirements(minimal.prereqs)
    for n in (9, 10):
        assert satisfies("INT341", _completed(minimal, f"sv{n:04d}@uni.edu.vn"), and_map, or_map)
    assert minimal.offering("INT341").capacity == 1
    assert minimal.offering("INT341").enrolled_count == 0


# ------------------------------------------------------------------ kit lớp / đăng ký
def test_kit_class_states(minimal):
    full = minimal.offering("INT331")
    assert (full.capacity, full.enrolled_count) == (15, 15)
    almost = minimal.offering("INT231")
    assert (almost.capacity, almost.enrolled_count) == (30, 29)
    assert len(minimal.offering("INT101").schedule) == 2  # nhiều buổi/tuần


def test_waitlist_of_full_class(minimal):
    rows = sorted((w for w in minimal.waitlist if w.offering_key == ("INT331", "01")), key=lambda w: w.position)
    assert [w.student_email for w in rows] == [f"sv{n:04d}@uni.edu.vn" for n in (6, 7, 8)]
    assert [w.position for w in rows] == [1, 2, 3]
    assert len(rows) == math.ceil(15 * 0.2)


def test_sv0004_has_24_credits_and_will_hit_credit_limit_not_conflict(minimal):
    credits = {c.code: c.credits for c in minimal.courses}
    offs = [minimal.offering(*e.offering_key) for e in minimal.enrollments if e.student_email == "sv0004@uni.edu.vn"]
    assert sum(credits[o.course_code] for o in offs) == 24
    target = minimal.offering("INT221")  # sv0004 đã học INT131 nên đủ tiên quyết
    assert credits["INT221"] == 3  # 24 + 3 > 25
    assert not any(_overlap(target.schedule, o.schedule) for o in offs)  # lỗi phải là CREDIT_LIMIT, không phải SCHEDULE_CONFLICT


def test_conflict_and_adjacent_classes(minimal):
    i221, i222, m201 = (minimal.offering(c).schedule for c in ("INT221", "INT222", "MAT201"))
    assert _overlap(i221, i222)  # trùng thật sự
    assert not _overlap(i221, m201)  # liền kề (kết thúc 09:30 = bắt đầu 09:30) KHÔNG trùng
    assert _overlap(i222, m201)
    sv5 = [e.offering_key for e in minimal.enrollments if e.student_email == "sv0005@uni.edu.vn"]
    assert sv5 == [("INT221", "01")]


def test_enrolled_counts_match_active_enrollments(default):
    counts: dict = {}
    for e in default.enrollments:
        counts[e.offering_key] = counts.get(e.offering_key, 0) + 1
    for o in default.offerings:
        assert o.enrolled_count == counts.get(o.key, 0)


def test_all_schedules_inside_grid_hours(default):
    for o in default.offerings:
        for s in o.schedule:
            assert 1 <= s["day"] <= 7
            assert _to_min("07:00") <= _to_min(s["start"]) < _to_min(s["end"]) <= _to_min("21:00")


def test_term_is_current(default):
    assert {o.term for o in default.offerings} == {TERM}
