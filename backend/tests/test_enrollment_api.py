"""M3 API and business rules against real PostgreSQL and Redis."""

import pytest

from app.core import redis as core_redis
from app.models import Enrollment
from app.tools.invariants import find_invariant_violations

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
async def fresh_redis():
    core_redis._redis_client = None
    yield
    await core_redis.close_redis()


@pytest.fixture
async def world(test_session, make_student, make_course, make_offering):
    students = [await make_student(test_session) for _ in range(5)]
    course = await make_course(
        test_session, code="M3_100%", name="Enrollment", credits=3
    )
    offering = await make_offering(test_session, course, capacity=2)
    offering.instructor = "Teacher M3"
    offering.section = "01"
    await test_session.commit()
    return students, course, offering


async def post(client, student, login_as, offering, key=None):
    headers = login_as(student)
    if key:
        headers["Idempotency-Key"] = key
    return await client.post(
        "/api/v1/enroll", json={"offering_id": offering.id}, headers=headers
    )


async def test_enroll_cancel_reenroll_and_ownership(
    async_client, test_session, world, login_as
):
    students, _, offering = world
    response = await post(async_client, students[0], login_as, offering, "first")
    assert response.status_code == 201, response.text
    eid = response.json()["id"]
    assert (
        await post(async_client, students[0], login_as, offering, "first")
    ).json() == response.json()
    assert (await post(async_client, students[0], login_as, offering)).json()["detail"][
        "code"
    ] == "ALREADY_ENROLLED"
    path = f"/api/v1/enroll/{eid}"
    assert (
        await async_client.delete(path, headers=login_as(students[1]))
    ).status_code == 404
    assert (
        await async_client.delete(path + "?version=99", headers=login_as(students[0]))
    ).status_code == 409
    for _ in range(2):
        assert (
            await async_client.delete(path, headers=login_as(students[0]))
        ).status_code == 200
    assert (
        await post(async_client, students[0], login_as, offering)
    ).status_code == 201
    timetable = (
        await async_client.get("/api/v1/timetable", headers=login_as(students[0]))
    ).json()
    assert timetable["total_credits"] == 3
    assert timetable["max_credits"] == 25
    test_session.expire_all()
    assert not await find_invariant_violations(test_session)


async def test_waitlist_limit_leave_and_promotion(
    async_client, test_session, world, login_as
):
    students, _, offering = world
    results = [await post(async_client, s, login_as, offering) for s in students[:3]]
    assert [r.status_code for r in results] == [201, 201, 200]
    assert results[2].json()["position"] == 1
    assert (await post(async_client, students[2], login_as, offering)).json()["detail"][
        "code"
    ] == "ALREADY_WAITLISTED"
    assert (await post(async_client, students[3], login_as, offering)).json()["detail"][
        "code"
    ] == "WAITLIST_FULL"
    wid = results[2].json()["id"]
    assert (
        await async_client.delete(
            f"/api/v1/waitlist/{wid}", headers=login_as(students[0])
        )
    ).status_code == 404
    assert (
        await async_client.delete(
            f"/api/v1/waitlist/{wid}", headers=login_as(students[2])
        )
    ).status_code == 200
    queued = await post(async_client, students[3], login_as, offering)
    assert queued.json()["position"] == 1
    assert (
        await async_client.delete(
            f"/api/v1/enroll/{results[0].json()['id']}", headers=login_as(students[0])
        )
    ).status_code == 200
    assert (
        await async_client.get("/api/v1/timetable", headers=login_as(students[3]))
    ).json()["total_credits"] == 3
    test_session.expire_all()
    assert not await find_invariant_violations(test_session)


@pytest.mark.parametrize(
    "params,expected",
    [
        ({"q": "M3_100%"}, 1),
        ({"q": "nomatch"}, 0),
        ({"section": "01"}, 1),
        ({"credits": 3}, 1),
        ({"credits": 4}, 0),
        ({"instructor": "M3"}, 1),
        ({"day": 2, "from": "07:00", "to": "09:30"}, 1),
        ({"day": 2, "from": "07:30", "to": "09:30"}, 0),
        ({"day": 3}, 0),
        (
            {
                "q": "M3_100%",
                "section": "01",
                "credits": 3,
                "instructor": "M3",
                "day": 2,
            },
            1,
        ),
        ({"page": 2, "page_size": 1}, 0),
    ],
)
async def test_search_filters(async_client, world, login_as, params, expected):
    response = await async_client.get(
        "/api/v1/courses", params=params, headers=login_as(world[0][0])
    )
    assert response.status_code == 200, response.text
    assert len(response.json()["items"]) == expected


@pytest.mark.parametrize(
    "case,code",
    [
        ("prereq", "PREREQ_NOT_MET"),
        ("schedule", "SCHEDULE_CONFLICT"),
        ("credits", "CREDIT_LIMIT_EXCEEDED"),
        ("same_course", "ALREADY_ENROLLED"),
        ("completed", "ALREADY_COMPLETED"),
    ],
)
async def test_business_errors(
    async_client,
    test_session,
    world,
    login_as,
    make_course,
    make_offering,
    add_prereq,
    complete,
    case,
    code,
):
    students, course, offering = world
    student = students[0]
    if case == "prereq":
        pre = await make_course(test_session)
        await add_prereq(test_session, course, pre)
    elif case == "completed":
        await complete(test_session, student, course)
    elif case == "credits":
        student.max_credits = 2
    else:
        other = course if case == "same_course" else await make_course(test_session)
        other_offering = await make_offering(test_session, other)
        test_session.add(
            Enrollment(
                student_id=student.id, offering_id=other_offering.id, status="ACTIVE"
            )
        )
        other_offering.enrolled_count = 1
    await test_session.commit()
    response = await post(async_client, student, login_as, offering)
    assert response.json()["detail"]["code"] == code, response.text
    if case == "prereq":
        assert response.json()["detail"]["missing_courses"] == [pre.code]


async def test_auth_and_validation(async_client, world, login_as):
    student = world[0][0]
    for path in ("/courses", "/timetable", "/waitlist"):
        assert (await async_client.get("/api/v1" + path)).status_code == 401
    headers = login_as(student)
    assert (
        await async_client.get("/api/v1/courses?page_size=101", headers=headers)
    ).status_code == 422
    assert (
        await async_client.get("/api/v1/courses?from=10:00&to=07:00", headers=headers)
    ).status_code == 422
    assert (
        await async_client.post(
            "/api/v1/enroll", json={"offering_id": 99999}, headers=headers
        )
    ).status_code == 404


async def test_search_literal_wildcards_and_query_count(
    async_client, test_session, world, login_as, make_course, make_offering, test_engine
):
    from sqlalchemy import event

    students, _, offering = world
    other = await make_offering(
        test_session, await make_course(test_session, code="M3X100Z")
    )
    await test_session.commit()
    statements = []

    def record(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(test_engine.sync_engine, "before_cursor_execute", record)
    try:
        for q in ("_", "%"):
            response = await async_client.get(
                "/api/v1/courses", params={"q": q}, headers=login_as(students[0])
            )
            assert [i["id"] for i in response.json()["items"]] == [offering.id]
        assert (
            len(statements) == 6
        )  # latest term + count + joined page, independent of rows
    finally:
        event.remove(test_engine.sync_engine, "before_cursor_execute", record)
    assert other.id != offering.id


async def test_term_isolation_and_adjacent_meetings(
    async_client, test_session, world, login_as, make_course, make_offering
):
    students, _, offering = world
    student = students[0]
    student.max_credits = 3
    old = await make_offering(test_session, await make_course(test_session))
    old.term = "2025-1"
    await test_session.commit()
    assert (await post(async_client, student, login_as, old)).status_code == 201
    assert (await post(async_client, student, login_as, offering)).status_code == 201
    path = "/api/v1/timetable?term=2025-1"
    result = (await async_client.get(path, headers=login_as(student))).json()
    assert result["total_credits"] == 3 and len(result["items"]) == 1
    student.max_credits = 6
    adjacent = await make_offering(
        test_session,
        await make_course(test_session),
        schedule=[{"day": 2, "start": "09:30", "end": "10:30"}],
    )
    await test_session.commit()
    assert (await post(async_client, student, login_as, adjacent)).status_code == 201


async def test_waitlist_replay_after_promotion(
    async_client, test_session, world, login_as
):
    students, _, offering = world
    enrolled = [await post(async_client, s, login_as, offering) for s in students[:2]]
    queued = await post(async_client, students[2], login_as, offering, "queue-key")
    await async_client.delete(
        f"/api/v1/enroll/{enrolled[0].json()['id']}", headers=login_as(students[0])
    )
    assert (
        await post(async_client, students[2], login_as, offering, "queue-key")
    ).json() == queued.json()
    assert (
        await async_client.get("/api/v1/waitlist", headers=login_as(students[2]))
    ).json()["items"] == []


async def test_actual_redis_connection_refused(
    async_client, world, login_as, monkeypatch
):
    from redis.asyncio import Redis

    from app.services import enrollment_lock, enrollment_service, prerequisite_cache

    unavailable = Redis(
        host="127.0.0.1",
        port=1,
        socket_connect_timeout=0.05,
        socket_timeout=0.05,
        decode_responses=True,
    )
    for module in (enrollment_lock, enrollment_service, prerequisite_cache):
        monkeypatch.setattr(module, "get_redis", lambda: unavailable)
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "enrollment_redis_lock_enabled", True)
    try:
        students, _, offering = world
        response = await post(
            async_client, students[0], login_as, offering, "network-down"
        )
        assert response.status_code == 201, response.text
        response = await post(
            async_client, students[0], login_as, offering, "network-down"
        )
        assert response.json()["detail"]["code"] == "ALREADY_ENROLLED"
    finally:
        await unavailable.aclose()
