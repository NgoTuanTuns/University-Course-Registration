"""T1–T12 acceptance: separate committed PostgreSQL sessions, invariants after races."""

import asyncio

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core import redis as core_redis
from app.core.config import get_settings
from app.models import Enrollment, Waitlist
from app.services.enrollment_service import cancel, enroll
from app.tools.invariants import find_invariant_violations

pytestmark = pytest.mark.concurrency


@pytest.fixture(autouse=True)
async def fresh_redis():
    core_redis._redis_client = None
    yield
    await core_redis.close_redis()


async def race(test_engine, jobs):
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    barrier = asyncio.Barrier(len(jobs))

    async def worker(job):
        async with factory() as session:
            await barrier.wait()
            try:
                return await job(session)
            except HTTPException as exc:
                return exc.detail["code"]

    results = await asyncio.gather(*(worker(job) for job in jobs))
    async with factory() as session:
        assert not await find_invariant_violations(session)
    return results


@pytest.fixture
async def data(test_session, make_student, make_course, make_offering):
    students = [await make_student(test_session) for _ in range(8)]
    courses = [await make_course(test_session) for _ in range(2)]
    offerings = [await make_offering(test_session, c, capacity=2) for c in courses]
    await test_session.commit()
    return students, offerings


@pytest.mark.parametrize("redis_mode", ["off", "on", "down", "expired"])
async def test_last_seat_T1_T10_T11(
    test_engine, test_session, data, monkeypatch, redis_mode
):
    students, offerings = data
    offering = offerings[0]
    offering.capacity = 1
    await test_session.commit()
    settings = get_settings()
    monkeypatch.setattr(settings, "enrollment_redis_lock_enabled", redis_mode != "off")
    if redis_mode == "expired":
        monkeypatch.setattr(settings, "enrollment_lock_ttl_ms", 1)
    if redis_mode == "down":
        from redis.exceptions import ConnectionError

        async def unavailable(*args, **kwargs):
            raise ConnectionError("test outage")

        monkeypatch.setattr(core_redis.get_redis(), "set", unavailable)
    results = await race(
        test_engine, [lambda s, sid=u.id: enroll(s, sid, offering.id) for u in students]
    )
    assert sum(isinstance(r, dict) and r["status"] == "ACTIVE" for r in results) == 1
    assert (
        sum(isinstance(r, dict) and r["status"] == "WAITLISTED" for r in results) == 1
    )
    assert results.count("WAITLIST_FULL") == len(students) - 2


@pytest.mark.parametrize("key", ["same-key", None])
async def test_double_submit_T2_T3(test_engine, data, key):
    students, offerings = data
    results = await race(
        test_engine, [lambda s: enroll(s, students[0].id, offerings[0].id, key)] * 2
    )
    if key:
        assert results[0] == results[1]
    else:
        assert results.count("ALREADY_ENROLLED") == 1


@pytest.mark.parametrize("rule", ["credits", "schedule"])
async def test_student_serialization_T4_T5(test_engine, test_session, data, rule):
    students, offerings = data
    if rule == "credits":
        students[0].max_credits = 3
        offerings[1].schedule = [{"day": 3, "start": "07:00", "end": "09:30"}]
    await test_session.commit()
    results = await race(
        test_engine,
        [lambda s, oid=o.id: enroll(s, students[0].id, oid) for o in offerings],
    )
    assert sum(isinstance(r, dict) for r in results) == 1
    assert (
        "CREDIT_LIMIT_EXCEEDED" if rule == "credits" else "SCHEDULE_CONFLICT"
    ) in results


async def test_double_cancel_T6(test_engine, test_session, data):
    students, offerings = data
    result = await enroll(test_session, students[0].id, offerings[0].id)
    results = await race(
        test_engine, [lambda s: cancel(s, students[0].id, result["id"])] * 2
    )
    assert all(r["status"] == "CANCELLED" for r in results)


async def test_two_cancel_two_promote_T7(test_engine, test_session, data, monkeypatch):
    monkeypatch.setattr(get_settings(), "waitlist_max_ratio", 1.0)
    students, offerings = data
    oid = offerings[0].id
    enrolled = [await enroll(test_session, students[i].id, oid) for i in range(2)]
    for i in (2, 3):
        assert (await enroll(test_session, students[i].id, oid))[
            "status"
        ] == "WAITLISTED"
    await race(
        test_engine,
        [lambda s, i=i: cancel(s, students[i].id, enrolled[i]["id"]) for i in range(2)],
    )
    async with async_sessionmaker(test_engine)() as session:
        active = set(
            await session.scalars(
                select(Enrollment.student_id).where(
                    Enrollment.offering_id == oid, Enrollment.status == "ACTIVE"
                )
            )
        )
        assert active == {students[2].id, students[3].id}


async def test_cancel_vs_direct_T8(test_engine, test_session, data):
    students, offerings = data
    offerings[0].capacity = 1
    await test_session.commit()
    oid = offerings[0].id
    result = await enroll(test_session, students[0].id, oid)
    await enroll(test_session, students[1].id, oid)
    await race(
        test_engine,
        [
            lambda s: cancel(s, students[0].id, result["id"]),
            lambda s: enroll(s, students[2].id, oid),
        ],
    )
    async with async_sessionmaker(test_engine)() as session:
        assert (
            await session.scalar(
                select(Enrollment.student_id).where(
                    Enrollment.offering_id == oid, Enrollment.status == "ACTIVE"
                )
            )
            == students[1].id
        )


async def test_blocked_head_T9(test_engine, test_session, data, monkeypatch):
    monkeypatch.setattr(get_settings(), "waitlist_max_ratio", 2.0)
    students, offerings = data
    offerings[0].capacity = 1
    await test_session.commit()
    oid = offerings[0].id
    result = await enroll(test_session, students[0].id, oid)
    for i in (1, 2):
        await enroll(test_session, students[i].id, oid)
    await enroll(test_session, students[1].id, offerings[1].id)
    await race(test_engine, [lambda s: cancel(s, students[0].id, result["id"])])
    async with async_sessionmaker(test_engine)() as session:
        assert (
            await session.scalar(
                select(Enrollment.student_id).where(
                    Enrollment.offering_id == oid, Enrollment.status == "ACTIVE"
                )
            )
            == students[2].id
        )
        waiting = await session.scalar(
            select(Waitlist).where(Waitlist.offering_id == oid)
        )
        assert waiting.student_id == students[1].id and waiting.position == 1


@pytest.mark.timeout(120)
async def test_http_spike_200_T12(
    async_client, test_session, make_student, make_course, make_offering, login_as
):
    students = [await make_student(test_session) for _ in range(200)]
    offering = await make_offering(
        test_session, await make_course(test_session), capacity=1
    )
    await test_session.commit()
    results = await asyncio.gather(
        *(
            async_client.post(
                "/api/v1/enroll", json={"offering_id": offering.id}, headers=login_as(u)
            )
            for u in students
        )
    )
    assert sum(r.status_code == 201 for r in results) == 1
    assert sum(r.status_code == 200 for r in results) == 1
    assert all(r.status_code in {200, 201, 409} for r in results)
    test_session.expire_all()
    assert not await find_invariant_violations(test_session)
