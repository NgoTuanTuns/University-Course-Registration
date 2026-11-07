"""Đo hiệu năng engine: python -m benchmarks.run [--profile realistic|large|extreme|all]

In p50/p95/max (ms) cho evaluate/explain, bộ nhớ đỉnh, và so sánh có/không memo trên
lưới kim cương. Phần so sánh SQL/cache nằm ở --db (cần PostgreSQL + Redis đang chạy).
"""

from __future__ import annotations

import argparse
import random
import statistics
import time
import tracemalloc

from app.services.prerequisite_engine import PrerequisiteGraph, evaluate, explain
from benchmarks.dag_gen import PROFILES, dense_diamond, generate, random_completed


def _pct(values: list[float], q: float) -> float:
    values = sorted(values)
    return values[min(len(values) - 1, int(q * len(values)))]


def _time(fn, args_list) -> list[float]:
    out = []
    for a in args_list:
        t = time.perf_counter()
        fn(*a)
        out.append((time.perf_counter() - t) * 1000)
    return out


def bench_profile(name: str, samples: int = 500) -> None:
    spec = PROFILES[name]
    edges = generate(spec)
    rng = random.Random(spec.seed)
    tracemalloc.start()
    t0 = time.perf_counter()
    graph = PrerequisiteGraph.from_edges(edges)
    build_ms = (time.perf_counter() - t0) * 1000
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    cases = [
        (graph, rng.randrange(spec.courses), random_completed(edges, rng, rng.random()))
        for _ in range(samples)
    ]
    print(f"[{name}] courses={spec.courses} edges={len(edges)} layers={spec.layers}")
    print(f"  build graph {build_ms:.2f} ms, peak mem {peak / 1024:.0f} KiB")
    limited = [(*c, 50) for c in cases]  # đúng như API (PREREQ_EXPLAIN_MAX_ITEMS=50)
    for label, fn, data in (
        ("evaluate", evaluate, cases),
        ("explain50", explain, limited),
        ("explain", explain, cases),
    ):
        ms = _time(fn, data)
        print(
            f"  {label:9s} p50={statistics.median(ms):.3f} "
            f"p95={_pct(ms, 0.95):.3f} max={max(ms):.3f} ms (n={samples})"
        )


def bench_diamond() -> None:
    print("[diamond] lưới kim cương, môn đích ở tầng trên cùng, chưa học gì")
    for layers in (10, 20, 40, 80):
        graph = PrerequisiteGraph.from_edges(dense_diamond(layers, width=3))
        target = "0" + str(layers - 1)
        ms = _time(evaluate, [(graph, target, set())] * 20)
        paths = 3 ** (layers - 1)
        print(
            f"  layers={layers:3d}: memo {statistics.median(ms):.3f} ms "
            f"(không memo ~{paths:.2e} đường đi)"
        )


async def bench_db() -> None:
    """Số truy vấn SQL và độ trễ: cache lạnh / graph đã cache / kết quả đã cache."""
    from sqlalchemy import event

    from app.core.db import _get_session_factory
    from app.services import prerequisite_engine as engine

    async with _get_session_factory()() as session:
        count = {"n": 0}

        @event.listens_for(session.sync_session.get_bind(), "before_cursor_execute")
        def _count(*_a, **_k):
            count["n"] += 1

        await engine.invalidate_graph()
        for label, use_cache in (("cold", True), ("graph-warm", True), ("hit", True)):
            count["n"] = 0
            t = time.perf_counter()
            try:
                await engine.check_eligibility(session, 1, 1, use_cache=use_cache)
            except engine.CourseNotFoundError:
                print("  không có môn id=1: chạy seed trước")
                return
            print(
                f"  {label:10s} {(time.perf_counter() - t) * 1000:.2f} ms, "
                f"{count['n']} truy vấn SQL"
            )
            if label == "cold":
                await engine.invalidate_student(1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="all", choices=[*PROFILES, "all"])
    parser.add_argument("--db", action="store_true")
    args = parser.parse_args()
    for name in PROFILES if args.profile == "all" else [args.profile]:
        bench_profile(name)
    bench_diamond()
    if args.db:
        import asyncio

        asyncio.run(bench_db())


if __name__ == "__main__":
    main()
