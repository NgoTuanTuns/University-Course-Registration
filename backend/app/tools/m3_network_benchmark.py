"""M3 TCP acceptance harness, using an owned loopback server and test DB only.

Creates synthetic students, sends arrivals over a fixed window, verifies database
invariants and promotion, then removes only its own rows. Never targets a remote API.
"""

import argparse
import asyncio
import json
import math
import os
import socket
import subprocess
import sys
from collections import Counter
from pathlib import Path
from time import perf_counter
from uuid import uuid4

import httpx
from sqlalchemy import select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.tokens import create_access_token
from app.models import Enrollment
from app.tools.invariants import find_invariant_violations
from app.tools.m3_benchmark import cleanup, seed


async def measure(
    factory, client: httpx.AsyncClient, count: int, window: float
) -> dict:
    ids, oid, cid = await seed(factory, count)
    try:
        headers = {
            sid: {
                "Authorization": "Bearer "
                + create_access_token(sid, "student", f"m3-{sid}@example.test"),
                "Idempotency-Key": f"m3-bench-{uuid4().hex}-{sid}",
            }
            for sid in ids
        }
        start = perf_counter()
        retry_errors = Counter()

        async def request(index: int, sid: int):
            delay = start + index * window / count - perf_counter()
            if delay > 0:
                await asyncio.sleep(delay)
            sent = perf_counter()
            for attempt in range(2):
                try:
                    response = await client.post(
                        "/api/v1/enroll",
                        json={"offering_id": oid},
                        headers=headers[sid],
                    )
                    break
                except httpx.TransportError as exc:
                    if attempt == 0:
                        retry_errors[type(exc).__name__] += 1
                        await asyncio.sleep(0.05)
                        continue
                    response = httpx.Response(
                        599,
                        json={
                            "detail": {
                                "code": "NETWORK_ERROR",
                                "error_type": type(exc).__name__,
                            }
                        },
                    )
            return sid, response, (perf_counter() - sent) * 1000, sent - start

        rows = await asyncio.gather(*(request(i, sid) for i, sid in enumerate(ids)))
        elapsed = perf_counter() - start
        active = [(sid, r) for sid, r, _, _ in rows if r.status_code == 201]
        waiting = [(sid, r) for sid, r, _, _ in rows if r.status_code == 200]
        statuses = Counter(str(r.status_code) for _, r, _, _ in rows)
        errors = Counter(
            r.json()["detail"]["code"] for _, r, _, _ in rows if r.status_code == 409
        )
        async with factory() as session:
            before = await find_invariant_violations(session)
        promoted = False
        if len(active) == 1 and len(waiting) == 1:
            sid, response = active[0]
            cancelled = await client.delete(
                f"/api/v1/enroll/{response.json()['id']}", headers=headers[sid]
            )
            async with factory() as session:
                promoted_id = await session.scalar(
                    select(Enrollment.student_id).where(
                        Enrollment.offering_id == oid, Enrollment.status == "ACTIVE"
                    )
                )
                promoted = cancelled.status_code == 200 and promoted_id == waiting[0][0]
        async with factory() as session:
            after = await find_invariant_violations(session)
        latencies = sorted(ms for _, _, ms, _ in rows)
        result = {
            "requests": count,
            "http_attempts": count + sum(retry_errors.values()),
            "network_retries": dict(retry_errors),
            "arrival_window_sec": window,
            "last_arrival_sec": round(max(t for _, _, _, t in rows), 3),
            "elapsed_sec": round(elapsed, 3),
            "http_statuses": dict(statuses),
            "transport_errors": statuses.get("599", 0),
            "transport_error_types": dict(
                Counter(
                    r.json()["detail"]["error_type"]
                    for _, r, _, _ in rows
                    if r.status_code == 599
                )
            ),
            "business_errors": dict(errors),
            "p50_ms": round(latencies[math.ceil(count * 0.5) - 1], 2),
            "p95_ms": round(latencies[math.ceil(count * 0.95) - 1], 2),
            "invariant_violations_before_cancel": len(before),
            "invariant_violations_after_cancel": len(after),
            "promoted_correctly": promoted,
        }
        result["passed"] = (
            len(active) == len(waiting) == 1
            and not before
            and not after
            and promoted
            and sum(statuses.get(str(s), 0) for s in (200, 201, 409)) == count
        )
        return result
    finally:
        await cleanup(factory, ids, oid, cid)


async def main(args: argparse.Namespace) -> None:
    settings = get_settings()
    url = make_url(settings.database_url)
    if (
        settings.app_env != "test"
        or url.database != "course_reg_test"
        or url.host not in {"localhost", "127.0.0.1"}
    ):
        raise SystemExit("Requires APP_ENV=test and local course_reg_test DATABASE_URL")
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    env = os.environ | {
        "DATABASE_URL": settings.database_url,
        "APP_ENV": "test",
        "ENROLLMENT_REDIS_LOCK_ENABLED": str(args.redis_lock).lower(),
    }
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--no-access-log",
            "--log-level",
            "error",
        ],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    engine = create_async_engine(
        settings.database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with httpx.AsyncClient(
            base_url=f"http://127.0.0.1:{port}",
            timeout=120,
            limits=httpx.Limits(max_connections=2000, max_keepalive_connections=200),
        ) as client:
            for _ in range(100):
                if process.poll() is not None:
                    raise RuntimeError("Owned uvicorn exited before readiness")
                try:
                    if (await client.get("/openapi.json")).status_code == 200:
                        break
                except httpx.TransportError:
                    pass
                await asyncio.sleep(0.1)
            else:
                raise RuntimeError("Owned uvicorn did not become ready")
            rounds = [
                await measure(factory, client, args.students, args.window)
                for _ in range(args.rounds)
            ]
        result = {
            "scope": "loopback TCP HTTP to owned uvicorn; synthetic students; no nginx or login load",
            "redis_lock": args.redis_lock,
            "db_pool_size": settings.db_pool_size,
            "db_max_overflow": settings.db_max_overflow,
            "rounds": rounds,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        if not all(r["passed"] for r in rounds):
            raise RuntimeError("Acceptance failed; inspect output JSON")
    finally:
        process.terminate()
        await asyncio.to_thread(process.wait, timeout=10)
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--students", type=int, choices=range(2, 2001), default=2000)
    parser.add_argument("--window", type=float, default=30)
    parser.add_argument("--rounds", type=int, choices=range(1, 21), default=3)
    parser.add_argument("--redis-lock", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.window < 0:
        parser.error("window must be nonnegative")
    asyncio.run(main(args))
