"""M3 local ASGI benchmark/demo on course_reg_test only; never a production load claim."""

import argparse
import asyncio
import json
import math
from collections import Counter
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.db import get_session
from app.core.redis import close_redis
from app.core.tokens import create_access_token
from app.main import app
from app.models import Course, CourseOffering, Enrollment, Student, Waitlist
from app.tools.invariants import find_invariant_violations


async def seed(factory, count: int) -> tuple[list[int], int, int]:
    prefix = uuid4().hex[:8]
    async with factory() as session:
        course = Course(code=f"M3{prefix}", name="M3 demo", credits=3)
        session.add(course)
        await session.flush()
        offering = CourseOffering(
            course_id=course.id,
            term="2026-1",
            section="M3",
            capacity=1,
            enrolled_count=0,
            schedule=[{"day": 7, "start": "18:00", "end": "19:00"}],
        )
        students = [
            Student(
                mssv=f"M3{prefix}{i}",
                email=f"m3-{prefix}-{i}@example.test",
                full_name=f"M3 demo {i}",
                password_hash="not-a-login-account",
                role="student",
                max_credits=25,
            )
            for i in range(count)
        ]
        session.add_all([offering, *students])
        await session.commit()
        return [s.id for s in students], offering.id, course.id


async def cleanup(factory, ids: list[int], oid: int, cid: int) -> None:
    async with factory() as session:
        await session.execute(delete(Waitlist).where(Waitlist.offering_id == oid))
        await session.execute(delete(Enrollment).where(Enrollment.offering_id == oid))
        await session.execute(delete(CourseOffering).where(CourseOffering.id == oid))
        await session.execute(delete(Student).where(Student.id.in_(ids)))
        await session.execute(delete(Course).where(Course.id == cid))
        await session.commit()


async def run_round(factory, count: int) -> dict:
    ids, oid, cid = await seed(factory, count)

    async def session_override():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://m3.test"
        ) as client:
            barrier = asyncio.Barrier(count)

            async def request(sid):
                token = create_access_token(sid, "student", f"m3-{sid}@example.test")
                await barrier.wait()
                start = perf_counter()
                response = await client.post(
                    "/api/v1/enroll",
                    json={"offering_id": oid},
                    headers={"Authorization": f"Bearer {token}"},
                )
                return sid, response, (perf_counter() - start) * 1000

            start = perf_counter()
            rows = await asyncio.gather(*(request(sid) for sid in ids))
            elapsed = perf_counter() - start
            active = [(sid, r) for sid, r, _ in rows if r.status_code == 201]
            waiting = [(sid, r) for sid, r, _ in rows if r.status_code == 200]
            assert len(active) == 1 and len(waiting) == 1
            assert all(r.status_code in {200, 201, 409} for _, r, _ in rows)
            owner, enrollment = active[0]
            token = create_access_token(owner, "student", "m3-demo@example.test")
            response = await client.delete(
                f"/api/v1/enroll/{enrollment.json()['id']}",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200
        async with factory() as session:
            violations = await find_invariant_violations(session)
            promoted = await session.scalar(
                select(Enrollment.student_id).where(
                    Enrollment.offering_id == oid, Enrollment.status == "ACTIVE"
                )
            )
            assert promoted == waiting[0][0] and not violations
        latencies = sorted(ms for _, _, ms in rows)
        return {
            "requests": count,
            "elapsed_sec": round(elapsed, 3),
            "p50_ms": round(latencies[math.ceil(count * 0.5) - 1], 2),
            "p95_ms": round(latencies[math.ceil(count * 0.95) - 1], 2),
            "http_statuses": dict(Counter(str(r.status_code) for _, r, _ in rows)),
            "business_errors": dict(
                Counter(
                    r.json()["detail"]["code"]
                    for _, r, _ in rows
                    if r.status_code >= 400
                )
            ),
            "active_before_cancel": len(active),
            "waitlisted_before_cancel": len(waiting),
            "promoted_correctly": True,
            "invariant_violations": len(violations),
        }
    finally:
        app.dependency_overrides.pop(get_session, None)
        await cleanup(factory, ids, oid, cid)


async def main(args: argparse.Namespace) -> None:
    settings = get_settings()
    if (
        settings.app_env != "test"
        or make_url(settings.database_url).database != "course_reg_test"
    ):
        raise SystemExit(
            "APP_ENV=test and DATABASE_URL ending in /course_reg_test are required"
        )
    settings.enrollment_redis_lock_enabled = args.redis_lock
    engine = create_async_engine(settings.database_url, pool_size=5, max_overflow=10)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        rounds = [await run_round(factory, args.students) for _ in range(args.rounds)]
        result = {
            "scope": "Local ASGI + PostgreSQL, not a network/2000-user load acceptance",
            "redis_lock": args.redis_lock,
            "db_pool_size": 5,
            "db_max_overflow": 10,
            "rounds": rounds,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    finally:
        await close_redis()
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--students", type=int, default=4, choices=range(2, 2001), metavar="2..2000"
    )
    parser.add_argument(
        "--rounds", type=int, default=1, choices=range(1, 21), metavar="1..20"
    )
    parser.add_argument("--redis-lock", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    asyncio.run(main(parser.parse_args()))
