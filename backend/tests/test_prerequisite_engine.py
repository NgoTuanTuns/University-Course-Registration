"""Test lõi engine trên DAG mẫu trong bộ nhớ (bảng ca nghiệm thu Mục 6.1)."""

import pytest

from app.services.prerequisite_engine import (
    PrerequisiteCycleError,
    PrerequisiteGraph,
    assert_acyclic,
    evaluate,
    find_cycle,
    would_create_cycle,
)

EDGES = [
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


@pytest.fixture
def graph():
    return PrerequisiteGraph.from_edges(EDGES)


# (đã học, môn xét, eligible, tập môn thiếu, {group_no: lựa chọn} chưa đạt)
CASES = [
    (set(), "A1", True, set(), {}),  # 1
    (set(), "B1", False, {"A1"}, {}),  # 2
    ({"A1"}, "B1", True, set(), {}),  # 3
    (set(), "C1", False, {"B1", "A1"}, {}),  # 4 bắc cầu
    ({"A1"}, "C1", False, {"B1"}, {}),  # 5
    ({"B1"}, "C1", True, set(), {}),  # 6 (phụ thuộc điểm 1)
    ({"A1"}, "D1", False, {"B1", "B2"}, {}),  # 7
    (set(), "D1", False, {"B1", "B2", "A1"}, {}),  # 8 kim cương
    ({"A1", "B1", "B2"}, "D1", True, set(), {}),  # 9
    (set(), "E1", False, set(), {1: {"A2", "A3"}}),  # 10
    ({"A3"}, "E1", True, set(), {}),  # 11
    ({"A2", "A3"}, "E1", True, set(), {}),  # 12
    ({"A2"}, "F1", False, {"C1", "B1", "A1"}, {}),  # 13
    ({"A1", "B1", "C1"}, "F1", False, set(), {1: {"A2", "A3"}}),  # 14
    ({"A1", "B1", "C1", "A2"}, "F1", True, set(), {}),  # 15
    ({"A2"}, "G1", False, set(), {2: {"B1", "B2"}}),  # 16
    ({"A2", "B2"}, "G1", True, set(), {}),  # 17
    ({"B1"}, "G1", False, set(), {1: {"A2", "A3"}}),  # 18
    ({"C1"}, "H1", True, set(), {}),  # 19
    ({"E1"}, "H1", True, set(), {}),  # 20
]


@pytest.mark.parametrize("done,course,eligible,missing,groups", CASES)
def test_evaluate(graph, done, course, eligible, missing, groups):
    r = evaluate(graph, course, done)
    assert r.eligible is eligible
    assert set(r.missing_courses) == missing
    assert len(r.missing_courses) == len(missing)  # mỗi môn chỉ xuất hiện 1 lần
    assert {g.group_no: set(g.options) for g in r.unmet_or_groups} == groups


def test_missing_order_is_deterministic(graph):
    assert evaluate(graph, "D1", set()).missing_courses == ["B1", "B2", "A1"]


def test_find_cycle_none_on_valid_graph(graph):
    assert find_cycle(graph) is None


@pytest.mark.parametrize(
    "course,prereq,expected",
    [
        ("A1", "B1", ["A1", "B1", "A1"]),  # C1
        ("A1", "C1", ["A1", "C1", "B1", "A1"]),  # C2
        ("B1", "B1", ["B1", "B1"]),  # C3 tự trỏ
        ("D1", "A2", None),  # C4
        ("C1", "A1", None),  # C5 dư thừa nhưng hợp lệ
    ],
)
def test_would_create_cycle(graph, course, prereq, expected):
    assert would_create_cycle(graph, course, prereq) == expected


def test_find_cycle_detects_loop_with_path():
    g = PrerequisiteGraph.from_edges(
        [("X", "Y", "AND", 0), ("Y", "Z", "AND", 0), ("Z", "X", "AND", 0)]
    )
    cycle = find_cycle(g)
    assert cycle[0] == cycle[-1] and set(cycle) == {"X", "Y", "Z"}


def test_assert_acyclic_rejects_cycle():
    with pytest.raises(PrerequisiteCycleError) as e:
        assert_acyclic([("X", "Y", "AND", 0), ("Y", "X", "AND", 0)])
    assert e.value.path[0] == e.value.path[-1]


def test_diamond_lattice_does_not_blow_up():
    # 40 tầng x 2 môn, mỗi môn cần cả 2 môn tầng dưới: 2^40 đường đi nếu không nhớ.
    edges = []
    for layer in range(1, 40):
        for a in "ab":
            for b in "ab":
                edges.append((f"{a}{layer}", f"{b}{layer - 1}", "AND", 0))
    r = evaluate(PrerequisiteGraph.from_edges(edges), "a39", set())
    assert len(r.missing_courses) == 78  # tầng 0..38 x 2 môn


def test_deep_chain_no_recursion_error():
    n = 5000  # sâu hơn giới hạn đệ quy mặc định của Python
    g = PrerequisiteGraph.from_edges([(i, i + 1, "AND", 0) for i in range(n)])
    assert len(evaluate(g, 0, set()).missing_courses) == n
    assert find_cycle(g) is None
