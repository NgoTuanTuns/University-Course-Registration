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
from tests.prereq_cases import (
    ACCEPTANCE_CASES,
    ACCEPTANCE_EDGES,
    ACCEPTANCE_IDS,
    CYCLE_CASES,
    CYCLE_IDS,
)

pytestmark = pytest.mark.unit




@pytest.fixture
def graph():
    return PrerequisiteGraph.from_edges(ACCEPTANCE_EDGES)


@pytest.mark.parametrize(
    "number,done,course,eligible,missing,groups", ACCEPTANCE_CASES, ids=ACCEPTANCE_IDS
)
def test_evaluate(graph, number, done, course, eligible, missing, groups):
    r = evaluate(graph, course, done)
    assert r.eligible is eligible
    assert set(r.missing_courses) == missing
    assert len(r.missing_courses) == len(missing)  # mỗi môn chỉ xuất hiện 1 lần
    assert {g.group_no: set(g.options) for g in r.unmet_or_groups} == groups


def test_missing_order_is_deterministic(graph):
    assert evaluate(graph, "D1", set()).missing_courses == ["B1", "B2", "A1"]


def test_find_cycle_none_on_valid_graph(graph):
    assert find_cycle(graph) is None


@pytest.mark.parametrize("number,course,prereq,expected", CYCLE_CASES, ids=CYCLE_IDS)
def test_would_create_cycle(graph, number, course, prereq, expected):
    assert would_create_cycle(graph, course, prereq) == expected


def test_find_cycle_detects_loop_with_path():
    g = PrerequisiteGraph.from_edges(
        [("X", "Y", "AND", 0), ("Y", "Z", "AND", 0), ("Z", "X", "AND", 0)]
    )
    cycle = find_cycle(g)
    assert cycle[0] == cycle[-1] and set(cycle) == {"X", "Y", "Z"}


def test_find_cycle_through_or_edge():
    # Cạnh OR cũng là "cần" -> vòng qua nhóm "hoặc" vẫn bị phát hiện.
    g = PrerequisiteGraph.from_edges([("X", "Y", "OR", 1), ("Y", "X", "AND", 0)])
    assert find_cycle(g) is not None


def test_assert_acyclic_rejects_cycle():
    with pytest.raises(PrerequisiteCycleError) as e:
        assert_acyclic([("X", "Y", "AND", 0), ("Y", "X", "AND", 0)])
    assert e.value.path[0] == e.value.path[-1]


def test_from_edges_rejects_bad_rows():
    with pytest.raises(ValueError):
        PrerequisiteGraph.from_edges([("X", "Y", "OR", 0)])
    with pytest.raises(ValueError):
        PrerequisiteGraph.from_edges([("X", "Y", "XOR", 0)])


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


# --------------------------------------------------------------------------- OR-group (Tuần 2)
def test_single_member_or_group_behaves_like_and():
    g_or = PrerequisiteGraph.from_edges([("X", "Y", "OR", 1)])
    g_and = PrerequisiteGraph.from_edges([("X", "Y", "AND", 0)])
    for done in (set(), {"Y"}):
        assert evaluate(g_or, "X", done).eligible == evaluate(g_and, "X", done).eligible


def test_single_member_or_group_is_reported_as_group_not_missing():
    r = evaluate(PrerequisiteGraph.from_edges([("X", "Y", "OR", 1)]), "X", set())
    assert r.missing_courses == []
    assert [(g.group_no, g.options) for g in r.unmet_or_groups] == [(1, ["Y"])]


@pytest.mark.parametrize(
    "done,eligible,unmet",
    [
        (set(), False, [1, 2, 3]),
        ({"P1"}, False, [2, 3]),
        ({"P1", "Q2"}, False, [3]),
        ({"P2", "Q1", "R1"}, True, []),
        ({"P1", "P2", "Q1", "Q2", "R1", "R2"}, True, []),  # thỏa hết mọi lựa chọn
    ],
)
def test_independent_or_groups(done, eligible, unmet):
    g = PrerequisiteGraph.from_edges(
        [
            ("X", "P1", "OR", 1),
            ("X", "P2", "OR", 1),
            ("X", "Q1", "OR", 2),
            ("X", "Q2", "OR", 2),
            ("X", "R1", "OR", 3),
            ("X", "R2", "OR", 3),
        ]
    )
    r = evaluate(g, "X", done)
    assert r.eligible is eligible
    assert [grp.group_no for grp in r.unmet_or_groups] == unmet


@pytest.mark.parametrize(
    "done,eligible,missing,unmet",
    [
        (set(), False, ["A"], [1]),
        ({"A"}, False, [], [1]),
        ({"O1"}, False, ["A"], []),
        ({"A", "O2"}, True, [], []),
    ],
)
def test_and_combined_with_or(done, eligible, missing, unmet):
    g = PrerequisiteGraph.from_edges(
        [("X", "A", "AND", 0), ("X", "O1", "OR", 1), ("X", "O2", "OR", 1)]
    )
    r = evaluate(g, "X", done)
    assert (r.eligible, r.missing_courses) == (eligible, missing)
    assert [grp.group_no for grp in r.unmet_or_groups] == unmet


def test_or_option_prereqs_are_not_counted_as_missing():
    # Lựa chọn trong nhóm "hoặc" có tiên quyết riêng: không bắt buộc học -> không
    # được gộp vào missing_courses (explain mới cho biết lựa chọn nào học được ngay).
    g = PrerequisiteGraph.from_edges(
        [("X", "O1", "OR", 1), ("X", "O2", "OR", 1), ("O2", "Z", "AND", 0)]
    )
    r = evaluate(g, "X", set())
    assert r.missing_courses == []
    assert r.unmet_or_groups[0].options == ["O1", "O2"]


def test_integer_ids_work_like_codes():
    g = PrerequisiteGraph.from_edges([(3, 2, "AND", 0), (2, 1, "AND", 0)])
    assert evaluate(g, 3, set()).missing_courses == [2, 1]
    assert evaluate(g, 3, {2}).eligible is True
