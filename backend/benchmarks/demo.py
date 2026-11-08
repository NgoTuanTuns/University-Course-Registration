"""Demo Tuần 7 (không cần DB): python -m benchmarks.demo

Chạy lõi engine trên bộ môn mẫu của kit: check, explain, chặn vòng, tốc độ.
"""

from __future__ import annotations

import json
import time

from app.seed_data import build_dataset
from app.services.prerequisite_engine import (
    PrerequisiteGraph,
    evaluate,
    explain,
    would_create_cycle,
)


def _show(title: str, payload) -> None:
    print(f"\n== {title}")
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=list))


def main() -> None:
    ds = build_dataset("minimal")
    graph = PrerequisiteGraph.from_edges(
        (p.course_code, p.prereq_code, p.type, p.group_no) for p in ds.prereqs
    )
    done = {}
    for row in ds.completed:
        done.setdefault(row.student_email, set()).add(row.course_code)

    for email, target in (
        ("sv0001", "INT341"),
        ("sv0002", "INT431"),
        ("sv0003", "INT341"),
    ):
        key = next(k for k in done if k.startswith(email))
        res = evaluate(graph, target, done[key])
        _show(
            f"check {email} -> {target}",
            {
                "eligible": res.eligible,
                "missing_courses": res.missing_courses,
                "unmet_or_groups": [
                    {"group_no": g.group_no, "options": g.options}
                    for g in res.unmet_or_groups
                ],
            },
        )
        exp = explain(graph, target, done[key], max_items=50)
        print("suggested_order:", exp.suggested_order)
        for m in exp.missing:
            print(f"  {m.kind:10s} {' -> '.join(map(str, m.path))}")

    some = next(iter(graph.and_prereqs))
    prereq = next(iter(graph.and_prereqs[some]))
    print(
        f"\nThêm '{prereq} cần {some}' tạo vòng:",
        would_create_cycle(graph, prereq, some),
    )
    t = time.perf_counter()
    for _ in range(1000):
        evaluate(graph, "INT431", set())
    print(f"1000 lần check INT431: {(time.perf_counter() - t) * 1000:.1f} ms")


if __name__ == "__main__":
    main()
