"""Đối chiếu engine với oracle đệ quy trên hàng nghìn cặp (DAG, sinh viên) có seed."""

import random

import pytest

from app.services.prerequisite_engine import (
    PrerequisiteGraph,
    evaluate,
    explain,
    find_cycle,
)
from benchmarks.dag_gen import DagSpec, generate, oracle, random_completed

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("seed", range(40))
def test_engine_matches_oracle_on_random_dags(seed):
    rng = random.Random(seed)
    spec = DagSpec(
        courses=rng.randint(5, 60),
        layers=rng.randint(2, 8),
        fan_in=rng.randint(1, 4),
        or_ratio=rng.choice([0, 0.2, 0.5]),
        or_size=rng.randint(1, 4),
        seed=seed,
    )
    edges = generate(spec)
    graph = PrerequisiteGraph.from_edges(edges)
    assert find_cycle(graph) is None
    for _ in range(60):  # 40 x 60 = 2400 cặp
        done = random_completed(edges, rng, rng.choice([0, 0.1, 0.3, 0.6]))
        course = rng.randrange(spec.courses)
        eligible, missing, groups = oracle(edges, course, done)
        got = evaluate(graph, course, done)
        assert got.eligible is eligible
        assert set(got.missing_courses) == missing
        assert len(got.missing_courses) == len(missing)
        assert {g.group_no: set(g.options) for g in got.unmet_or_groups} == groups
        exp = explain(graph, course, done)
        assert exp.eligible is eligible
        assert {m.course_id for m in exp.missing} == missing
        order = {c: i for i, c in enumerate(exp.suggested_order)}
        for c, p, t, _ in edges:
            if t == "AND" and c in order and p in order:
                assert order[p] < order[c]


def test_evaluate_scales_linearly_not_exponentially():
    from benchmarks.dag_gen import dense_diamond

    for layers in (20, 40, 80):
        g = PrerequisiteGraph.from_edges(dense_diamond(layers, width=3))
        r = evaluate(g, "0" + str(layers - 1), set())
        assert len(r.missing_courses) == 3 * (layers - 1)
