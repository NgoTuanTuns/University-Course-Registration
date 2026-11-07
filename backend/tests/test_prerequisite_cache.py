"""Cache Redis + invalidation (Tuần 3) và số truy vấn cố định (Tuần 5).

Chạy với PostgreSQL thật (course_reg_test) và Redis database 1.
"""

from __future__ import annotations

import asyncio

import pytest
from redis.asyncio import Redis
from sqlalchemy import event
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core import redis as core_redis
from app.core.config import get_settings
from app.services import prerequisite_cache as cache
from app.services import prerequisite_engine as engine
from app.services import prerequisite_repository as repo
from tests.prereq_cases import mark_completed, seed_acceptance_graph

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
async def fresh_redis_client():
    """Client Redis dùng chung gắn với event loop; mỗi test dùng client mới."""
    core_redis._redis_client = None
    yield
    await core_redis.close_redis()


@pytest.fixture
def sql_counter(test_engine):
    statements: list[str] = []

    def before(conn, cursor, statement, params, context, executemany):
        statements.append(statement)

    event.listen(test_engine.sync_engine, "before_cursor_execute", before)
    yield statements
    event.remove(test_engine.sync_engine, "before_cursor_execute", before)


@pytest.fixture
async def world(test_session, make_student):
    courses = await seed_acceptance_graph(test_session)
    alice = await make_student(test_session)
    bob = await make_student(test_session)
    await mark_completed(test_session, alice.id, [courses["A1"]])
    await test_session.commit()
    return {"courses": courses, "alice": alice, "bob": bob}


def _ids(world, *codes):
    return [world["courses"][c].id for c in codes]


async def _check(session, student, course):
    return await engine.check_eligibility(session, student.id, course.id)


# --------------------------------------------------------------------- trúng / trượt
async def test_second_call_hits_cache_with_zero_queries(
    test_session, world, sql_counter
):
    c1 = world["courses"]["C1"]
    first = await _check(test_session, world["alice"], c1)
    assert len(sql_counter) == 3  # cạnh + danh mục + completed (đồ thị chưa có)

    sql_counter.clear()
    second = await _check(test_session, world["alice"], c1)
    assert sql_counter == []  # cache trúng -> 0 truy vấn DB
    assert second == first
    assert (second.eligible, second.missing_courses) == (False, ["ACCB1"])
    assert await get_metrics_pair() == (1, 1)


async def test_miss_with_cached_graph_costs_one_query(test_session, world, sql_counter):
    await _check(test_session, world["alice"], world["courses"]["C1"])
    sql_counter.clear()
    await _check(test_session, world["alice"], world["courses"]["D1"])
    assert len(sql_counter) == 1 and "completed_courses" in sql_counter[0]


async def test_query_count_does_not_grow_with_dag_size(
    test_session, world, sql_counter, make_course, add_prereq
):
    # Thêm một chuỗi dài 60 môn rồi đo lại: số truy vấn vẫn như cũ.
    chain = [await make_course(test_session) for _ in range(60)]
    for upper, lower in zip(chain, chain[1:], strict=False):
        await add_prereq(test_session, upper, lower)
    await test_session.commit()
    await engine.invalidate_graph()

    sql_counter.clear()
    res = await engine.check_eligibility(test_session, world["alice"].id, chain[0].id)
    assert len(res.missing_courses) == 59
    assert len(sql_counter) == 3
    sql_counter.clear()
    await engine.check_eligibility(test_session, world["bob"].id, chain[0].id)
    assert len(sql_counter) == 1


async def get_metrics_pair():
    metrics = await cache.get_metrics()
    return metrics["hit"], metrics["miss"]


async def test_metrics_count_hits_and_misses(test_session, world):
    await cache.reset_metrics()
    for _ in range(4):
        await _check(test_session, world["alice"], world["courses"]["B1"])
    metrics = await cache.get_metrics()
    assert (metrics["hit"], metrics["miss"]) == (3, 1)
    assert metrics["hit_ratio"] == pytest.approx(0.75)


async def test_result_key_has_configured_ttl(test_session, world):
    await _check(test_session, world["alice"], world["courses"]["C1"])
    ttl = await core_redis.get_redis().ttl(
        cache.result_key(world["alice"].id, world["courses"]["C1"].id)
    )
    assert 0 < ttl <= get_settings().prereq_cache_ttl_sec


async def test_expired_result_is_recomputed(
    test_session, world, sql_counter, monkeypatch
):
    monkeypatch.setattr(get_settings(), "prereq_cache_ttl_sec", 1)
    await _check(test_session, world["alice"], world["courses"]["C1"])
    await asyncio.sleep(1.2)
    sql_counter.clear()
    await _check(test_session, world["alice"], world["courses"]["C1"])
    assert len(sql_counter) == 1  # hết hạn -> tính lại (đồ thị vẫn còn trong cache)


async def test_students_do_not_share_keys(test_session, world):
    c1 = world["courses"]["C1"]
    alice = await _check(test_session, world["alice"], c1)
    bob = await _check(test_session, world["bob"], c1)
    assert alice.missing_courses == ["ACCB1"]
    assert bob.missing_courses == ["ACCB1", "ACCA1"]


# --------------------------------------------------------------------- invalidation
async def test_dag_change_is_visible_immediately_after_invalidate_graph(
    test_session, world, add_prereq
):
    a2, b1 = world["courses"]["A2"], world["courses"]["B1"]
    assert (await _check(test_session, world["alice"], b1)).eligible is True

    await add_prereq(test_session, b1, a2)  # admin thêm: B1 cần thêm A2
    await test_session.commit()
    stale = await _check(test_session, world["alice"], b1)
    assert (
        stale.eligible is True
    )  # chưa invalidation -> còn kết quả cũ (lý do phải gọi)

    await engine.invalidate_graph()
    fresh = await _check(test_session, world["alice"], b1)
    assert (fresh.eligible, fresh.missing_courses) == (False, ["ACCA2"])


async def test_completed_change_is_visible_after_invalidate_student(
    test_session, world
):
    c1 = world["courses"]["C1"]
    assert (await _check(test_session, world["alice"], c1)).eligible is False
    await mark_completed(test_session, world["alice"].id, [world["courses"]["B1"]])
    await test_session.commit()
    await engine.invalidate_student(world["alice"].id)
    assert (await _check(test_session, world["alice"], c1)).eligible is True


async def test_invalidate_student_keeps_other_students_and_graph(test_session, world):
    c1 = world["courses"]["C1"]
    await _check(test_session, world["alice"], c1)
    await _check(test_session, world["bob"], c1)
    redis = core_redis.get_redis()
    # khóa trông "giống" của alice nhưng thuộc sinh viên khác (id có cùng tiền tố số)
    lookalike = cache.result_key(int(f"{world['alice'].id}9"), c1.id)
    await redis.set(lookalike, "x")

    await engine.invalidate_student(world["alice"].id)

    assert not await redis.exists(cache.result_key(world["alice"].id, c1.id))
    assert await redis.exists(cache.result_key(world["bob"].id, c1.id))
    assert await redis.exists(lookalike)
    assert await redis.exists(cache.GRAPH_KEY)


async def test_invalidate_graph_clears_results_but_not_metrics(test_session, world):
    await _check(test_session, world["alice"], world["courses"]["C1"])
    await _check(test_session, world["bob"], world["courses"]["D1"])
    redis = core_redis.get_redis()
    await engine.invalidate_graph()
    assert await redis.keys("prereq:*") == []
    assert not await redis.exists(cache.GRAPH_KEY)
    assert await redis.exists(cache.METRIC_MISS_KEY)


async def test_write_after_invalidation_is_rejected(test_session, world):
    """Request đọc trước khi admin sửa, ghi sau khi admin đã xóa cache: phải bị từ chối."""
    alice, c1 = world["alice"], world["courses"]["C1"]
    lookup = await cache.read_results(alice.id, [c1.id])
    stale = await engine.check_eligibility(
        test_session, alice.id, c1.id, use_cache=False
    )
    await engine.invalidate_graph()

    assert await cache.store_results(alice.id, [stale], lookup.generation) is False
    assert not await core_redis.get_redis().exists(cache.result_key(alice.id, c1.id))
    graph = await repo.load_graph_snapshot(test_session)
    assert await cache.store_graph(graph, lookup.generation) is False


# --------------------------------------------------------------------- Redis gặp sự cố
async def test_redis_down_falls_back_to_database(test_session, world, sql_counter):
    dead = Redis.from_url(
        "redis://127.0.0.1:1/1", socket_connect_timeout=0.2, decode_responses=True
    )
    core_redis._redis_client = dead
    for _ in range(2):
        sql_counter.clear()
        res = await _check(test_session, world["alice"], world["courses"]["C1"])
        assert (res.eligible, res.missing_courses) == (False, ["ACCB1"])
        assert len(sql_counter) == 3  # không cache, tính trực tiếp mỗi lần
    assert await engine.invalidate_graph() == 0  # không ném lỗi
    assert await engine.warm_graph_cache(test_session) is False


async def test_corrupted_cache_entry_is_ignored(test_session, world):
    alice, c1 = world["alice"], world["courses"]["C1"]
    await core_redis.get_redis().set(cache.result_key(alice.id, c1.id), "{not json")
    res = await _check(test_session, alice, c1)
    assert res.missing_courses == ["ACCB1"]


# --------------------------------------------------------------------- đồ thị + stampede
async def test_warm_graph_cache_preloads_graph(test_session, world, sql_counter):
    assert await engine.warm_graph_cache(test_session) is True
    assert await core_redis.get_redis().exists(cache.GRAPH_KEY)
    sql_counter.clear()
    await _check(test_session, world["alice"], world["courses"]["C1"])
    assert len(sql_counter) == 1


async def test_graph_key_does_not_use_result_prefix():
    for key in (cache.GRAPH_KEY, cache.GEN_KEY, cache.GRAPH_LOCK_KEY):
        assert not key.startswith(f"{cache.RESULT_PREFIX}:")
    assert cache.METRIC_HIT_KEY.startswith("metrics:prereq:")


async def test_concurrent_cold_requests_build_graph_once(
    test_engine, world, monkeypatch
):
    calls = 0
    original = repo.load_graph_snapshot

    async def counting(session):
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.05)  # giả lập DB chậm để các request chồng lên nhau
        return await original(session)

    monkeypatch.setattr(repo, "load_graph_snapshot", counting)
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    students = [world["alice"], world["bob"]] * 10
    course = world["courses"]["D1"]

    async def one(student):
        async with factory() as session:
            return await engine.check_eligibility(session, student.id, course.id)

    results = await asyncio.gather(*(one(s) for s in students))
    assert calls == 1
    assert {tuple(r.missing_courses) for r in results} == {
        ("ACCB1", "ACCB2"),
        ("ACCB1", "ACCB2", "ACCA1"),
    }


# --------------------------------------------------------------------- nhiều môn một lần
async def test_check_many_uses_one_graph_and_one_completed_load(
    test_session, world, sql_counter
):
    ids = _ids(world, "A1", "B1", "C1", "D1", "E1")
    results = await engine.check_eligibility_many(
        test_session, world["alice"].id, ids + [2_000_000_000]
    )
    assert sorted(results) == sorted(ids)  # môn không tồn tại bị bỏ qua
    assert len(sql_counter) == 4  # cạnh + danh mục + 1 truy vấn id lạ + completed
    sql_counter.clear()
    again = await engine.check_eligibility_many(test_session, world["alice"].id, ids)
    assert sql_counter == [] and again == results


async def test_missing_course_raises_not_found(test_session, world):
    with pytest.raises(engine.CourseNotFoundError):
        await engine.check_eligibility(test_session, world["alice"].id, 2_000_000_000)


async def test_new_course_created_after_graph_cached_is_found(
    test_session, world, make_course
):
    await _check(test_session, world["alice"], world["courses"]["C1"])  # dựng đồ thị
    fresh = await make_course(test_session, code="ACCNEW")
    await test_session.commit()
    res = await engine.check_eligibility(test_session, world["alice"].id, fresh.id)
    assert (res.course_code, res.eligible) == ("ACCNEW", True)


# --------------------------------------------------------------------- chiến lược WITH RECURSIVE
async def test_subgraph_query_matches_full_graph(test_session, world):
    full = engine.PrerequisiteGraph.from_edges(await repo.load_edges(test_session))
    for code in ("C1", "D1", "F1", "G1", "H1"):
        cid = world["courses"][code].id
        sub = engine.PrerequisiteGraph.from_edges(
            await repo.load_subgraph_edges(test_session, cid)
        )
        for done in (set(), {world["courses"]["A1"].id}):
            assert engine.evaluate(sub, cid, done) == engine.evaluate(full, cid, done)
