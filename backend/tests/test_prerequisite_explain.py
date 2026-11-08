"""Explain (Tuần 2): đường suy diễn, kind, required_by, suggested_order, can_take_now."""

import pytest

from app.services.prerequisite_engine import (
    PrerequisiteGraph,
    evaluate,
    explain,
    suggested_order,
)
from tests.prereq_cases import ACCEPTANCE_CASES, ACCEPTANCE_EDGES, ACCEPTANCE_IDS

pytestmark = pytest.mark.unit


@pytest.fixture
def graph():
    return PrerequisiteGraph.from_edges(ACCEPTANCE_EDGES)


def _missing(exp):
    return [(m.course_id, m.kind, m.required_by, m.path) for m in exp.missing]


@pytest.mark.parametrize(
    "number,done,course,eligible,missing,groups", ACCEPTANCE_CASES, ids=ACCEPTANCE_IDS
)
def test_explain_agrees_with_evaluate(
    graph, number, done, course, eligible, missing, groups
):
    exp = explain(graph, course, done)
    res = evaluate(graph, course, done)
    assert exp.eligible is res.eligible is eligible
    assert [m.course_id for m in exp.missing] == res.missing_courses
    assert exp.total_missing == len(missing)
    target_groups = {
        g.group_no: {o.course_id for o in g.options}
        for g in exp.unmet_or_groups
        if g.required_by == course
    }
    assert target_groups == groups
    assert sorted(exp.suggested_order) == sorted(res.missing_courses)
    assert exp.truncated is False


def test_transitive_chain_case4(graph):
    exp = explain(graph, "C1", set())
    assert _missing(exp) == [
        ("B1", "DIRECT", "C1", ["C1", "B1"]),
        ("A1", "TRANSITIVE", "B1", ["C1", "B1", "A1"]),
    ]
    assert exp.suggested_order == ["A1", "B1"]


def test_diamond_case8_lists_shared_course_once_with_shortest_path(graph):
    exp = explain(graph, "D1", set())
    assert _missing(exp) == [
        ("B1", "DIRECT", "D1", ["D1", "B1"]),
        ("B2", "DIRECT", "D1", ["D1", "B2"]),
        ("A1", "TRANSITIVE", "B1", ["D1", "B1", "A1"]),
    ]
    assert exp.suggested_order == ["A1", "B1", "B2"]


def test_case13_or_satisfied_but_chain_missing(graph):
    exp = explain(graph, "F1", {"A2"})
    assert [m.course_id for m in exp.missing] == ["C1", "B1", "A1"]
    assert exp.unmet_or_groups == []
    assert exp.suggested_order == ["A1", "B1", "C1"]


def test_case16_or_options_cannot_be_taken_yet(graph):
    exp = explain(graph, "G1", {"A2"})
    assert exp.missing == []
    [group] = exp.unmet_or_groups
    assert (group.group_no, group.required_by) == (2, "G1")
    assert [
        (o.course_id, o.can_take_now, o.missing_courses) for o in group.options
    ] == [
        ("B1", False, ["A1"]),
        ("B2", False, ["A1"]),
    ]


def test_or_option_can_take_now_when_its_prereqs_done(graph):
    exp = explain(graph, "G1", {"A1", "A2"})
    [group] = exp.unmet_or_groups
    assert all(o.can_take_now and o.missing_courses == [] for o in group.options)


def test_case10_options_without_prereqs_are_takeable(graph):
    [group] = explain(graph, "E1", set()).unmet_or_groups
    assert [(o.course_id, o.can_take_now) for o in group.options] == [
        ("A2", True),
        ("A3", True),
    ]


def test_case_h1_or_group_with_mixed_options(graph):
    # H1 cần OR {C1, E1}: C1 thiếu chuỗi B1 -> A1; E1 thiếu nhóm OR riêng (A2/A3)
    [group] = explain(graph, "H1", set()).unmet_or_groups
    options = {o.course_id: o for o in group.options}
    assert options["C1"].can_take_now is False
    assert options["C1"].missing_courses == ["B1", "A1"]
    assert options["E1"].can_take_now is False
    assert options["E1"].missing_courses == []  # thiếu nhóm "hoặc", không thiếu môn AND


def test_or_groups_of_missing_courses_are_reported_with_required_by():
    # X cần Y; Y cần OR {P, Q}: muốn học X phải học Y, mà Y lại cần một trong P/Q.
    g = PrerequisiteGraph.from_edges(
        [("X", "Y", "AND", 0), ("Y", "P", "OR", 1), ("Y", "Q", "OR", 1)]
    )
    exp = explain(g, "X", set())
    assert [m.course_id for m in exp.missing] == ["Y"]
    [group] = exp.unmet_or_groups
    assert (group.required_by, [o.course_id for o in group.options]) == (
        "Y",
        ["P", "Q"],
    )
    # nhóm của môn trung gian không làm đổi kết quả check của môn đích
    assert evaluate(g, "X", set()).unmet_or_groups == []


def test_eligible_explanation_is_empty(graph):
    exp = explain(graph, "D1", {"A1", "B1", "B2"})
    assert exp.eligible is True
    assert (exp.missing, exp.unmet_or_groups, exp.suggested_order) == ([], [], [])


def test_shortest_path_is_chosen_among_many():
    # T cần L (dài: L -> M -> Z) và cần Z trực tiếp: Z phải là DIRECT với path ngắn nhất
    g = PrerequisiteGraph.from_edges(
        [
            ("T", "L", "AND", 0),
            ("L", "M", "AND", 0),
            ("M", "Z", "AND", 0),
            ("T", "Z", "AND", 0),
        ]
    )
    by_id = {m.course_id: m for m in explain(g, "T", set()).missing}
    assert by_id["Z"].path == ["T", "Z"] and by_id["Z"].kind == "DIRECT"
    assert by_id["M"].path == ["T", "L", "M"]


def test_suggested_order_is_topological():
    edges = [
        ("T", "A", "AND", 0),
        ("T", "B", "AND", 0),
        ("A", "C", "AND", 0),
        ("B", "C", "AND", 0),
        ("C", "D", "AND", 0),
        ("B", "E", "AND", 0),
    ]
    g = PrerequisiteGraph.from_edges(edges)
    order = explain(g, "T", set()).suggested_order
    pos = {c: i for i, c in enumerate(order)}
    for course, prereq, _, _ in edges:
        if course in pos and prereq in pos:
            assert pos[prereq] < pos[course], (prereq, course, order)
    assert order == ["D", "C", "A", "E", "B"]


def test_suggested_order_ignores_completed_courses():
    g = PrerequisiteGraph.from_edges([("T", "A", "AND", 0), ("A", "B", "AND", 0)])
    assert suggested_order(g, ["A"]) == ["A"]
    assert explain(g, "T", {"B"}).suggested_order == ["A"]


def test_max_items_truncates_but_reports_totals():
    n = 200
    g = PrerequisiteGraph.from_edges([(i, i + 1, "AND", 0) for i in range(n)])
    exp = explain(g, 0, set(), max_items=10)
    assert len(exp.missing) == 10 and exp.total_missing == n
    assert exp.truncated is True
    assert exp.suggested_order[0] == n  # môn sâu nhất phải học đầu tiên
    assert len(exp.suggested_order) == 10
    assert exp.missing[-1].path == list(range(11))


def test_deep_chain_explain_with_limit_is_fast():
    n = 5000
    g = PrerequisiteGraph.from_edges([(i, i + 1, "AND", 0) for i in range(n)])
    exp = explain(g, 0, set(), max_items=50)
    assert exp.total_missing == n and len(exp.missing) == 50


def test_diamond_lattice_explain_does_not_blow_up():
    edges = []
    for layer in range(1, 40):
        for a in "ab":
            for b in "ab":
                edges.append((f"{a}{layer}", f"{b}{layer - 1}", "AND", 0))
    exp = explain(PrerequisiteGraph.from_edges(edges), "a39", set())
    assert exp.total_missing == 78
    assert max(len(m.path) for m in exp.missing) == 40  # một đường/môn, không bùng nổ


def test_or_groups_are_limited_by_max_items():
    edges = [("X", f"P{i}", "OR", i) for i in range(1, 21)]
    exp = explain(PrerequisiteGraph.from_edges(edges), "X", set(), max_items=5)
    assert len(exp.unmet_or_groups) == 5
    assert exp.total_unmet_or_groups == 20
    assert exp.truncated is True
