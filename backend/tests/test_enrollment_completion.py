"""Regression coverage for M3 transaction, queue and idempotency boundaries."""

import asyncio
import json

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core import redis as core_redis
from app.core.config import get_settings
from app.models import CourseOffering, Enrollment
from app.services import enrollment_service as service
from app.services import waitlist_service as queue
from app.tools.invariants import find_invariant_violations

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("gate", [False, True])
async def test_pool_exhaustion_returns_retryable_conflict(
    test_engine, world, monkeypatch, gate
):
    from sqlalchemy.ext.asyncio import create_async_engine

    sid, oid = world[0][0].id, world[1].id
    monkeypatch.setattr(get_settings(), "enrollment_db_lock_timeout_ms", 30)
    monkeypatch.setattr(get_settings(), "enrollment_redis_lock_enabled", gate)
    monkeypatch.setattr(get_settings(), "enrollment_db_admission_timeout_sec", 0.1)
    engine = create_async_engine(test_engine.url, pool_size=1, max_overflow=0)
    try:
        async with engine.connect(), async_sessionmaker(engine)() as session:
            with pytest.raises(HTTPException) as caught:
                await asyncio.wait_for(service.enroll(session, sid, oid), 2)
            assert caught.value.detail["code"] == "CONCURRENT_UPDATE"
            assert not session.in_transaction()
    finally:
        await engine.dispose()


@pytest.fixture(autouse=True)
async def redis_lifecycle():
    core_redis._redis_client = None
    yield
    await core_redis.close_redis()


@pytest.fixture
async def world(test_session, make_student, make_course, make_offering):
    students = [await make_student(test_session) for _ in range(5)]
    offering = await make_offering(
        test_session, await make_course(test_session), capacity=1
    )
    await test_session.commit()
    return students, offering


async def test_lock_timeout_retries_then_returns_conflict(
    test_engine, test_session, world, monkeypatch
):
    student_id, oid = world[0][0].id, world[1].id
    monkeypatch.setattr(get_settings(), "enrollment_db_lock_timeout_ms", 30)
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with factory() as holder, factory() as contender:
        await service.lock_students(holder, {student_id})
        with pytest.raises(HTTPException) as caught:
            await asyncio.wait_for(service.enroll(contender, student_id, oid), 3)
        assert caught.value.detail["code"] == "CONCURRENT_UPDATE"
        assert not contender.in_transaction()
        await holder.rollback()
        assert (await service.enroll(contender, student_id, oid))["status"] == "ACTIVE"
    test_session.expire_all()
    assert not await find_invariant_violations(test_session)


async def test_changed_queue_retries_from_fresh_transaction(
    test_session, world, monkeypatch
):
    student_id, oid = world[0][0].id, world[1].id
    original = service.ensure_eligible
    calls = 0

    async def changed_once(*args):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise service.QueueChanged()
        await original(*args)

    monkeypatch.setattr(service, "ensure_eligible", changed_once)
    assert (await service.enroll(test_session, student_id, oid))["status"] == "ACTIVE"
    assert calls == 2
    assert not await find_invariant_violations(test_session)


async def test_cancel_rolls_back_when_promotion_fails(test_session, world, monkeypatch):
    ids, oid = [s.id for s in world[0]], world[1].id
    active = await service.enroll(test_session, ids[0], oid)
    await service.enroll(test_session, ids[1], oid)

    async def fail(*args):
        raise RuntimeError("promotion failed")

    monkeypatch.setattr(queue, "promote_next", fail)
    with pytest.raises(RuntimeError, match="promotion failed"):
        await service.cancel(test_session, ids[0], active["id"])
    enrollment = await test_session.get(Enrollment, active["id"])
    assert enrollment.status == "ACTIVE" and enrollment.version == 0
    assert (await test_session.get(CourseOffering, oid)).enrolled_count == 1
    assert len(await queue.queue_rows(test_session, oid)) == 1
    assert not await find_invariant_violations(test_session)


@pytest.mark.parametrize("block", [None, "credits", "prerequisite"])
async def test_fifo_skips_ineligible_and_reindexes(
    test_session, world, monkeypatch, make_course, add_prereq, block
):
    monkeypatch.setattr(get_settings(), "waitlist_max_ratio", 4.0)
    ids, oid = [s.id for s in world[0]], world[1].id
    active = await service.enroll(test_session, ids[0], oid)
    waiting = [await service.enroll(test_session, sid, oid) for sid in ids[1:]]
    if block == "credits":
        from app.models import Student

        (await test_session.get(Student, ids[1])).max_credits = 1
    if block == "prerequisite":
        from app.models import CompletedCourse

        offering = await test_session.get(CourseOffering, oid)
        course = await make_course(test_session)
        from app.models import Course

        await add_prereq(
            test_session, await test_session.get(Course, offering.course_id), course
        )
        for sid in ids[2:]:
            test_session.add(
                CompletedCourse(student_id=sid, course_id=course.id, grade=8)
            )
        # Keep the current enrollment valid when the admin adds a prerequisite.
        test_session.add(
            CompletedCourse(student_id=ids[0], course_id=course.id, grade=8)
        )
        from app.services.prerequisite_cache import invalidate_graph

        await invalidate_graph()
    await test_session.commit()
    if block:
        listed = await queue.list_waitlist(test_session, ids[1], 1, 20)
        assert listed["items"][0]["blocked_reason"] == (
            "CREDIT_LIMIT_EXCEEDED" if block == "credits" else "PREREQ_NOT_MET"
        )
    await queue.leave(test_session, ids[3], waiting[2]["id"])
    await service.cancel(test_session, ids[0], active["id"])
    expected = ids[1] if block is None else ids[2]
    enrollment = await test_session.scalar(
        select(Enrollment).where(
            Enrollment.offering_id == oid, Enrollment.status == "ACTIVE"
        )
    )
    assert enrollment.student_id == expected
    rows = await queue.queue_rows(test_session, oid)
    assert [r.position for r in rows] == list(range(1, len(rows) + 1))
    await service.cancel(test_session, expected, enrollment.id)
    next_id = ids[2] if block is None else ids[4]
    assert (
        await test_session.scalar(
            select(Enrollment.student_id).where(
                Enrollment.offering_id == oid, Enrollment.status == "ACTIVE"
            )
        )
        == next_id
    )
    assert not await find_invariant_violations(test_session)


async def test_cache_finalizer_cannot_overwrite_reused_key(clean_test_data):
    key = "idem:enroll:1:regression"
    old = {"id": 1, "offering_id": 1, "status": "ACTIVE", "version": 0}
    newer = old | {"id": 2, "offering_id": 2}
    await service.cache_result(key, newer)
    await service.cache_result(key, old, committed=True)
    assert json.loads(await core_redis.get_redis().get(key)) == newer


@pytest.mark.parametrize("raw", ["[]", "null", "42", '{"status":"ACTIVE"}'])
async def test_malformed_cache_falls_back_to_db(test_session, world, raw):
    sid, oid = world[0][0].id, world[1].id
    await core_redis.get_redis().set(f"idem:enroll:{sid}:malformed", raw)
    assert (await service.enroll(test_session, sid, oid, "malformed"))[
        "status"
    ] == "ACTIVE"
