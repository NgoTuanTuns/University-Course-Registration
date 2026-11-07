"""Sinh DAG tiên quyết giả lập theo tầng (có seed) và bản "oracle" đệ quy ngây thơ."""

from __future__ import annotations

import random
from dataclasses import dataclass

Edge = tuple[int, int, str, int]


@dataclass(frozen=True)
class DagSpec:
    courses: int
    layers: int
    fan_in: int  # số tiên quyết AND tối đa mỗi môn
    or_ratio: float = 0.2  # tỉ lệ môn có nhóm OR
    or_size: int = 3
    seed: int = 1


PROFILES = {
    "realistic": DagSpec(courses=200, layers=8, fan_in=3, seed=11),
    "large": DagSpec(courses=1000, layers=20, fan_in=4, seed=12),
    "extreme": DagSpec(courses=3000, layers=80, fan_in=6, or_ratio=0.1, seed=13),
}


def generate(spec: DagSpec) -> list[Edge]:
    """Cạnh (môn, tiên quyết, loại, nhóm). Tiên quyết luôn ở tầng thấp hơn -> không chu trình."""
    rng = random.Random(spec.seed)
    per_layer = max(1, spec.courses // spec.layers)
    layer_of = {c: min(c // per_layer, spec.layers - 1) for c in range(spec.courses)}
    by_layer: dict[int, list[int]] = {}
    for c, layer in layer_of.items():
        by_layer.setdefault(layer, []).append(c)
    edges: list[Edge] = []
    for c in range(spec.courses):
        layer = layer_of[c]
        if layer == 0:
            continue
        pool = [x for lower in range(max(0, layer - 3), layer) for x in by_layer[lower]]
        for p in rng.sample(pool, min(len(pool), rng.randint(1, spec.fan_in))):
            edges.append((c, p, "AND", 0))
        if rng.random() < spec.or_ratio:
            for p in rng.sample(pool, min(len(pool), spec.or_size)):
                edges.append((c, p, "OR", 1))
    return edges


def dense_diamond(layers: int, width: int = 2) -> list[Edge]:
    """Mỗi môn cần mọi môn ở tầng dưới: số đường đi tăng theo lũy thừa."""
    return [
        (f"{a}{lv}", f"{b}{lv - 1}", "AND", 0)  # type: ignore[misc]
        for lv in range(1, layers)
        for a in range(width)
        for b in range(width)
    ]


def random_completed(edges: list[Edge], rng: random.Random, ratio: float) -> set:
    nodes = sorted({e[0] for e in edges} | {e[1] for e in edges}, key=str)
    return {n for n in nodes if rng.random() < ratio}


def oracle(edges: list[Edge], course, completed) -> tuple[bool, set, dict[int, set]]:
    """Cài đặt đệ quy ngây thơ theo đúng định nghĩa D04 để đối chiếu engine.

    Trả về (eligible, tập môn AND thiếu, {nhóm: lựa chọn} của môn đích chưa đạt)."""
    and_of: dict = {}
    or_of: dict = {}
    for c, p, t, g in edges:
        if t == "AND":
            and_of.setdefault(c, []).append(p)
        else:
            or_of.setdefault(c, {}).setdefault(g, []).append(p)

    missing: set = set()

    def need(c):
        for p in and_of.get(c, []):
            if p not in completed:
                missing.add(p)
                need(p)

    need(course)
    groups = {
        g: set(opts)
        for g, opts in or_of.get(course, {}).items()
        if not any(o in completed for o in opts)
    }
    return (not missing and not groups), missing, groups
