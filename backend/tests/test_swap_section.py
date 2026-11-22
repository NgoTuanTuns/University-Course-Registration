"""Integration & concurrency tests cho tính năng Đổi lớp nguyên tử (Atomic Section Swap)."""

import asyncio

import pytest

from app.core import redis as core_redis
from app.models import CourseOffering, Enrollment, TermRegistrationSetting
from app.tools.invariants import find_invariant_violations

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
async def fresh_redis():
    core_redis._redis_client = None
    yield
    await core_redis.close_redis()


async def test_swap_section_success_and_promotes_waitlist(
    async_client, test_session, make_student, make_course, make_offering, login_as
):
    s1 = await make_student(test_session)
    s2 = await make_student(test_session)
    course = await make_course(test_session, code="INT131", name="OOP", credits=3)
    sec1 = await make_offering(
        test_session,
        course,
        capacity=1,
        schedule=[{"day": 1, "start": "06:50", "end": "09:20"}],
    )
    sec2 = await make_offering(
        test_session,
        course,
        capacity=2,
        schedule=[{"day": 3, "start": "09:30", "end": "12:00"}],
    )
    await test_session.commit()

    # s1 đăng ký lớp 01 (đầy 1/1), s2 vào hàng chờ lớp 01
    r1 = await async_client.post(
        "/api/v1/enroll", json={"offering_id": sec1.id}, headers=login_as(s1)
    )
    assert r1.status_code == 201
    enr1_id = r1.json()["id"]

    r2 = await async_client.post(
        "/api/v1/enroll", json={"offering_id": sec1.id}, headers=login_as(s2)
    )
    assert r2.status_code == 200
    assert r2.json()["status"] == "WAITLISTED"

    # s1 đổi lớp 01 -> lớp 02: s1 sang lớp 02 và s2 tự động được đôn vào lớp 01!
    swap_res = await async_client.post(
        "/api/v1/enroll/swap",
        json={"from_enrollment_id": enr1_id, "to_offering_id": sec2.id},
        headers={**login_as(s1), "Idempotency-Key": "swap-1"},
    )
    assert swap_res.status_code == 200, swap_res.text
    body = swap_res.json()
    assert body["status"] == "SWAPPED"
    assert body["from_offering_id"] == sec1.id
    assert body["to_offering_id"] == sec2.id
    assert body["promoted_student_id"] == s2.id

    # Kiểm tra lại sĩ số và toàn vẹn DB
    sec1_id, sec2_id = sec1.id, sec2.id
    test_session.expire_all()
    refreshed_sec1 = await test_session.get(CourseOffering, sec1_id)
    refreshed_sec2 = await test_session.get(CourseOffering, sec2_id)
    assert refreshed_sec1.enrolled_count == 1
    assert refreshed_sec2.enrolled_count == 1
    assert await find_invariant_violations(test_session) == []


async def test_swap_preserves_old_seat_when_target_full_or_conflicting(
    async_client, test_session, make_student, make_course, make_offering, login_as
):
    s1 = await make_student(test_session)
    s2 = await make_student(test_session)
    c1 = await make_course(test_session, code="INT201", name="Cloud", credits=3)
    c2 = await make_course(test_session, code="BAS101", name="Skills", credits=3)

    sec1 = await make_offering(
        test_session,
        c1,
        capacity=2,
        schedule=[{"day": 1, "start": "06:50", "end": "09:20"}],
    )
    sec_full = await make_offering(
        test_session,
        c1,
        capacity=1,
        schedule=[{"day": 2, "start": "09:30", "end": "12:00"}],
    )
    sec_conflict = await make_offering(
        test_session,
        c1,
        capacity=2,
        schedule=[{"day": 4, "start": "12:45", "end": "15:15"}],
    )
    other_course_off = await make_offering(
        test_session,
        c2,
        capacity=5,
        schedule=[{"day": 4, "start": "12:45", "end": "15:15"}],
    )
    await test_session.commit()

    # s1 đăng ký c1-01 và c2-01 (T5 Ca 3); s2 lấp đầy c1-02
    r1 = await async_client.post(
        "/api/v1/enroll", json={"offering_id": sec1.id}, headers=login_as(s1)
    )
    enr1_id = r1.json()["id"]
    await async_client.post(
        "/api/v1/enroll",
        json={"offering_id": other_course_off.id},
        headers=login_as(s1),
    )
    await async_client.post(
        "/api/v1/enroll", json={"offering_id": sec_full.id}, headers=login_as(s2)
    )

    # 1. Đổi sang lớp đầy -> 409 SECTION_FULL và giữ nguyên lớp cũ
    res_full = await async_client.post(
        "/api/v1/enroll/swap",
        json={"from_enrollment_id": enr1_id, "to_offering_id": sec_full.id},
        headers=login_as(s1),
    )
    assert res_full.status_code == 409
    assert res_full.json()["detail"]["code"] == "SECTION_FULL"

    # 2. Đổi sang lớp trùng lịch với BAS101 -> 409 SCHEDULE_CONFLICT và giữ nguyên lớp cũ
    res_conflict = await async_client.post(
        "/api/v1/enroll/swap",
        json={"from_enrollment_id": enr1_id, "to_offering_id": sec_conflict.id},
        headers=login_as(s1),
    )
    assert res_conflict.status_code == 409
    assert res_conflict.json()["detail"]["code"] == "SCHEDULE_CONFLICT"

    # Lớp cũ của s1 vẫn nguyên trạng ACTIVE
    test_session.expire_all()
    old_enr = await test_session.get(Enrollment, enr1_id)
    assert old_enr is not None and old_enr.status == "ACTIVE"
    assert await find_invariant_violations(test_session) == []


async def test_swap_blocked_when_phase_locked(
    async_client, test_session, make_student, make_course, make_offering, login_as
):
    s1 = await make_student(test_session)
    course = await make_course(test_session, code="INT202", name="DB", credits=3)
    sec1 = await make_offering(
        test_session,
        course,
        capacity=5,
        schedule=[{"day": 1, "start": "06:50", "end": "09:20"}],
    )
    sec2 = await make_offering(
        test_session,
        course,
        capacity=5,
        schedule=[{"day": 2, "start": "09:30", "end": "12:00"}],
    )
    await test_session.commit()

    r1 = await async_client.post(
        "/api/v1/enroll", json={"offering_id": sec1.id}, headers=login_as(s1)
    )
    enr1_id = r1.json()["id"]

    # Khóa sổ học kỳ
    test_session.add(TermRegistrationSetting(term=sec1.term, phase="LOCKED"))
    await test_session.commit()

    res = await async_client.post(
        "/api/v1/enroll/swap",
        json={"from_enrollment_id": enr1_id, "to_offering_id": sec2.id},
        headers=login_as(s1),
    )
    assert res.status_code == 403
    assert res.json()["detail"]["code"] == "REGISTRATION_PHASE_CLOSED"


async def test_concurrent_cross_swap_no_deadlock(
    async_client, test_session, make_student, make_course, make_offering, login_as
):
    s1 = await make_student(test_session)
    s2 = await make_student(test_session)
    course = await make_course(test_session, code="INT203", name="Net", credits=3)
    sec1 = await make_offering(
        test_session,
        course,
        capacity=2,
        schedule=[{"day": 1, "start": "06:50", "end": "09:20"}],
    )
    sec2 = await make_offering(
        test_session,
        course,
        capacity=2,
        schedule=[{"day": 3, "start": "09:30", "end": "12:00"}],
    )
    await test_session.commit()

    e1 = (
        await async_client.post(
            "/api/v1/enroll", json={"offering_id": sec1.id}, headers=login_as(s1)
        )
    ).json()["id"]
    e2 = (
        await async_client.post(
            "/api/v1/enroll", json={"offering_id": sec2.id}, headers=login_as(s2)
        )
    ).json()["id"]

    # s1 đổi 01->02 và s2 đổi 02->01 đồng thời: khóa theo ID tăng dần nên không deadlock
    res1, res2 = await asyncio.gather(
        async_client.post(
            "/api/v1/enroll/swap",
            json={"from_enrollment_id": e1, "to_offering_id": sec2.id},
            headers=login_as(s1),
        ),
        async_client.post(
            "/api/v1/enroll/swap",
            json={"from_enrollment_id": e2, "to_offering_id": sec1.id},
            headers=login_as(s2),
        ),
    )
    assert res1.status_code == 200, res1.text
    assert res2.status_code == 200, res2.text
    test_session.expire_all()
    assert await find_invariant_violations(test_session) == []
