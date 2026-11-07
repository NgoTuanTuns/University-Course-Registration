"""Nghiệm thu qua API thật (Tuần 6): 20 ca + ca 404, xác thực/phân quyền, hợp đồng
OpenAPI, rate-limit, giới hạn explain và lỗi PREREQ_CYCLE.

Chạy với PostgreSQL thật (course_reg_test) và Redis database 1; token thật của M4.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.core import redis as core_redis
from app.core.config import get_settings
from app.services import prerequisite_engine as engine
from tests.prereq_cases import (
    ACCEPTANCE_CASES,
    ACCEPTANCE_IDS,
    CYCLE_CASES,
    CYCLE_IDS,
    mark_completed,
    seed_acceptance_graph,
)

pytestmark = pytest.mark.integration

CHECK = "/api/v1/prerequisites/check"
EXPLAIN = "/api/v1/prerequisites/explain"
OPENAPI_PATH = Path(__file__).resolve().parents[2] / "docs" / "openapi.json"


@pytest.fixture(autouse=True)
async def fresh_redis_client():
    core_redis._redis_client = None
    yield
    await core_redis.close_redis()


@pytest.fixture
async def acceptance(test_session):
    courses = await seed_acceptance_graph(test_session)
    await test_session.commit()
    return courses


def _codes(names):
    return {f"ACC{n}" for n in names}


# --------------------------------------------------------------------- 20 ca nghiệm thu
@pytest.mark.parametrize(
    "number,done,course,eligible,missing,groups", ACCEPTANCE_CASES, ids=ACCEPTANCE_IDS
)
async def test_acceptance_case_via_api(
    async_client,
    test_session,
    acceptance,
    make_student,
    login_as,
    number,
    done,
    course,
    eligible,
    missing,
    groups,
):
    student = await make_student(test_session)
    await mark_completed(test_session, student.id, [acceptance[c] for c in done])
    await test_session.commit()
    headers = login_as(student)
    course_id = acceptance[course].id

    check = await async_client.get(
        CHECK, params={"course_id": course_id}, headers=headers
    )
    assert check.status_code == 200, check.text
    body = check.json()
    assert body["course_code"] == f"ACC{course}"
    assert body["eligible"] is eligible
    assert set(body["missing_courses"]) == _codes(missing)
    assert len(body["missing_courses"]) == len(missing)
    assert {g["group_no"]: set(g["options"]) for g in body["unmet_or_groups"]} == {
        k: _codes(v) for k, v in groups.items()
    }

    explain = await async_client.post(
        EXPLAIN, json={"course_id": course_id}, headers=headers
    )
    assert explain.status_code == 200, explain.text
    exp = explain.json()
    assert exp["eligible"] is eligible
    assert {m["course_code"] for m in exp["missing"]} == _codes(missing)
    assert set(exp["suggested_order"]) == _codes(missing)
    for m in exp["missing"]:
        assert m["path"][0] == f"ACC{course}" and m["path"][-1] == m["course_code"]
        assert m["required_by"] == m["path"][-2]
        assert m["kind"] == ("DIRECT" if len(m["path"]) == 2 else "TRANSITIVE")


async def test_case21_nonexistent_course_returns_404(
    async_client, test_session, make_student, login_as
):
    student = await make_student(test_session)
    await test_session.commit()
    headers = login_as(student)
    check = await async_client.get(
        CHECK, params={"course_id": 2_000_000_000}, headers=headers
    )
    explain = await async_client.post(
        EXPLAIN, json={"course_id": 2_000_000_000}, headers=headers
    )
    for response in (check, explain):
        assert response.status_code == 404
        assert response.json()["detail"]["code"] == "NOT_FOUND"


async def test_explain_case16_reports_or_options_for_ui(
    async_client, test_session, acceptance, make_student, login_as
):
    student = await make_student(test_session)
    await mark_completed(test_session, student.id, [acceptance["A2"]])
    await test_session.commit()
    res = await async_client.post(
        EXPLAIN, json={"course_id": acceptance["G1"].id}, headers=login_as(student)
    )
    assert res.json()["unmet_or_groups"] == [
        {
            "group_no": 2,
            "required_by": "ACCG1",
            "options": [
                {
                    "course_code": "ACCB1",
                    "course_name": "Môn B1",
                    "can_take_now": False,
                    "missing_courses": ["ACCA1"],
                },
                {
                    "course_code": "ACCB2",
                    "course_name": "Môn B2",
                    "can_take_now": False,
                    "missing_courses": ["ACCA1"],
                },
            ],
        }
    ]


async def test_explain_transitive_chain_matches_agreed_schema(
    async_client, test_session, acceptance, make_student, login_as
):
    student = await make_student(test_session)
    await test_session.commit()
    res = await async_client.post(
        EXPLAIN, json={"course_id": acceptance["C1"].id}, headers=login_as(student)
    )
    assert res.json() == {
        "course_id": acceptance["C1"].id,
        "course_code": "ACCC1",
        "course_name": "Môn C1",
        "eligible": False,
        "missing": [
            {
                "course_code": "ACCB1",
                "course_name": "Môn B1",
                "kind": "DIRECT",
                "required_by": "ACCC1",
                "path": ["ACCC1", "ACCB1"],
            },
            {
                "course_code": "ACCA1",
                "course_name": "Môn A1",
                "kind": "TRANSITIVE",
                "required_by": "ACCB1",
                "path": ["ACCC1", "ACCB1", "ACCA1"],
            },
        ],
        "unmet_or_groups": [],
        "suggested_order": ["ACCA1", "ACCB1"],
        "total_missing": 2,
        "truncated": False,
    }


async def test_explain_is_truncated_by_config(
    async_client, test_session, acceptance, make_student, login_as, monkeypatch
):
    monkeypatch.setattr(get_settings(), "prereq_explain_max_items", 1)
    student = await make_student(test_session)
    await test_session.commit()
    body = (
        await async_client.post(
            EXPLAIN, json={"course_id": acceptance["D1"].id}, headers=login_as(student)
        )
    ).json()
    assert len(body["missing"]) == 1 and body["total_missing"] == 3
    assert body["suggested_order"] == ["ACCA1"]
    assert body["truncated"] is True


# --------------------------------------------------------------------- xác thực / phân quyền
async def test_requires_login(async_client, acceptance):
    check = await async_client.get(CHECK, params={"course_id": acceptance["A1"].id})
    explain = await async_client.post(EXPLAIN, json={"course_id": acceptance["A1"].id})
    for response in (check, explain):
        assert response.status_code == 401
        assert response.json()["detail"]["code"] == "UNAUTHENTICATED"


async def test_student_cannot_ask_for_another_student(
    async_client, test_session, acceptance, make_student, login_as
):
    me = await make_student(test_session)
    other = await make_student(test_session)
    await test_session.commit()
    check = await async_client.get(
        CHECK,
        params={"course_id": acceptance["A1"].id, "student_id": other.id},
        headers=login_as(me),
    )
    explain = await async_client.post(
        EXPLAIN,
        json={"course_id": acceptance["A1"].id, "student_id": other.id},
        headers=login_as(me),
    )
    for response in (check, explain):
        assert response.status_code == 403
        assert response.json()["detail"]["code"] == "FORBIDDEN"


async def test_student_may_pass_own_id(
    async_client, test_session, acceptance, make_student, login_as
):
    me = await make_student(test_session)
    await test_session.commit()
    res = await async_client.get(
        CHECK,
        params={"course_id": acceptance["A1"].id, "student_id": me.id},
        headers=login_as(me),
    )
    assert res.status_code == 200


async def test_admin_can_check_any_student(
    async_client, test_session, acceptance, make_student, login_as
):
    admin = await make_student(test_session, role="admin")
    student = await make_student(test_session)
    await mark_completed(test_session, student.id, [acceptance["A1"]])
    await test_session.commit()
    check = await async_client.get(
        CHECK,
        params={"course_id": acceptance["C1"].id, "student_id": student.id},
        headers=login_as(admin),
    )
    explain = await async_client.post(
        EXPLAIN,
        json={"course_id": acceptance["C1"].id, "student_id": student.id},
        headers=login_as(admin),
    )
    assert check.json()["missing_courses"] == ["ACCB1"]
    assert explain.json()["suggested_order"] == ["ACCB1"]


@pytest.mark.parametrize(
    "params", [{"course_id": 0}, {"course_id": -5}, {"course_id": "abc"}, {}]
)
async def test_invalid_course_id_is_rejected(
    async_client, test_session, make_student, login_as, params
):
    student = await make_student(test_session)
    await test_session.commit()
    res = await async_client.get(CHECK, params=params, headers=login_as(student))
    assert res.status_code == 422
    assert res.json()["detail"]["code"] == "VALIDATION_ERROR"


async def test_explain_rejects_invalid_body(
    async_client, test_session, make_student, login_as
):
    student = await make_student(test_session)
    await test_session.commit()
    res = await async_client.post(
        EXPLAIN, json={"course_id": 0}, headers=login_as(student)
    )
    assert res.status_code == 422


# --------------------------------------------------------------------- rate-limit
async def test_rate_limit_applies_per_user(
    async_client, test_session, acceptance, make_student, login_as, monkeypatch
):
    monkeypatch.setattr(get_settings(), "prereq_rate_limit_per_min", 2)
    me = await make_student(test_session)
    other = await make_student(test_session)
    await test_session.commit()
    params = {"course_id": acceptance["A1"].id}
    statuses = [
        (await async_client.get(CHECK, params=params, headers=login_as(me))).status_code
        for _ in range(3)
    ]
    assert statuses == [200, 200, 429]
    res = await async_client.get(CHECK, params=params, headers=login_as(other))
    assert res.status_code == 200  # người khác không bị ảnh hưởng


# --------------------------------------------------------------------- cache qua API
async def test_admin_change_is_seen_through_api_after_invalidation(
    async_client, test_session, acceptance, make_student, login_as, add_prereq
):
    student = await make_student(test_session)
    await test_session.commit()
    params = {"course_id": acceptance["A3"].id}
    first = await async_client.get(CHECK, params=params, headers=login_as(student))
    assert first.json()["eligible"] is True

    await add_prereq(test_session, acceptance["A3"], acceptance["A2"])
    await test_session.commit()
    await engine.invalidate_graph()

    second = await async_client.get(CHECK, params=params, headers=login_as(student))
    assert second.json()["missing_courses"] == ["ACCA2"]


# --------------------------------------------------------------------- chặn chu trình (cho M4)
@pytest.mark.parametrize("number,course,prereq,expected", CYCLE_CASES, ids=CYCLE_IDS)
async def test_ensure_edge_allowed_on_database(
    test_session, acceptance, number, course, prereq, expected
):
    call = engine.ensure_edge_allowed(
        test_session, acceptance[course].id, acceptance[prereq].id
    )
    if expected is None:
        await call
    else:
        with pytest.raises(engine.PrerequisiteCycleError) as exc_info:
            await call
        assert exc_info.value.path == [f"ACC{c}" for c in expected]
    await test_session.rollback()  # nhả advisory lock


async def test_cycle_http_error_shape(test_session, acceptance):
    with pytest.raises(engine.PrerequisiteCycleError) as exc_info:
        await engine.ensure_edge_allowed(
            test_session, acceptance["A1"].id, acceptance["C1"].id
        )
    await test_session.rollback()
    err = engine.cycle_http_error(exc_info.value)
    assert err.status_code == 422
    assert err.detail["code"] == "PREREQ_CYCLE"
    assert err.detail["cycle_path"] == ["ACCA1", "ACCC1", "ACCB1", "ACCA1"]
    assert "ACCA1 → ACCC1 → ACCB1 → ACCA1" in err.detail["message"]


# --------------------------------------------------------------------- hợp đồng OpenAPI
def _resolve(schema: dict, spec: dict) -> dict:
    while "$ref" in schema:
        name = schema["$ref"].rsplit("/", 1)[-1]
        schema = spec["components"]["schemas"][name]
    return schema


def _contract_errors(value, schema: dict, spec: dict, where: str = "$") -> list[str]:
    """Kiểm tra JSON theo đúng phần JSON Schema mà FastAPI sinh ra cho các endpoint này.
    Báo lỗi khi thiếu trường bắt buộc, THỪA trường lạ hoặc sai kiểu."""
    schema = _resolve(schema, spec)
    if "anyOf" in schema:
        options = [_contract_errors(value, s, spec, where) for s in schema["anyOf"]]
        return [] if any(not o for o in options) else options[0]
    if "enum" in schema and value not in schema["enum"]:
        return [f"{where}: {value!r} không thuộc {schema['enum']}"]
    kind = schema.get("type")
    checks = {
        "object": dict,
        "array": list,
        "string": str,
        "boolean": bool,
        "null": type(None),
    }
    if kind == "integer":
        ok = isinstance(value, int) and not isinstance(value, bool)
        return [] if ok else [f"{where}: cần integer"]
    if kind in checks and not isinstance(value, checks[kind]):
        return [f"{where}: cần {kind}"]
    errors: list[str] = []
    if kind == "object":
        props = schema.get("properties", {})
        errors += [
            f"{where}: thiếu {k}" for k in schema.get("required", []) if k not in value
        ]
        errors += [f"{where}: thừa {k}" for k in value if k not in props]
        for k, v in value.items():
            if k in props:
                errors += _contract_errors(v, props[k], spec, f"{where}.{k}")
    if kind == "array":
        for i, item in enumerate(value):
            errors += _contract_errors(item, schema["items"], spec, f"{where}[{i}]")
    return errors


def _response_schema(spec: dict, path: str, method: str) -> dict:
    content = spec["paths"][path][method]["responses"]["200"]["content"]
    return content["application/json"]["schema"]


async def test_responses_match_frozen_openapi_contract(
    async_client, test_session, acceptance, make_student, login_as
):
    spec = json.loads(OPENAPI_PATH.read_text(encoding="utf-8-sig"))
    student = await make_student(test_session)
    await mark_completed(test_session, student.id, [acceptance["A2"]])
    await test_session.commit()
    headers = login_as(student)
    for code in ("A1", "C1", "D1", "F1", "G1", "H1"):
        course_id = acceptance[code].id
        check = await async_client.get(
            CHECK, params={"course_id": course_id}, headers=headers
        )
        explain = await async_client.post(
            EXPLAIN, json={"course_id": course_id}, headers=headers
        )
        assert not _contract_errors(
            check.json(), _response_schema(spec, CHECK, "get"), spec
        )
        assert not _contract_errors(
            explain.json(), _response_schema(spec, EXPLAIN, "post"), spec
        )


def test_contract_checker_detects_drift():
    spec = json.loads(OPENAPI_PATH.read_text(encoding="utf-8-sig"))
    schema = _response_schema(spec, CHECK, "get")
    good = {
        "course_id": 1,
        "course_code": "X",
        "eligible": True,
        "missing_courses": [],
        "unmet_or_groups": [],
    }
    assert _contract_errors(good, schema, spec) == []
    renamed = {**good, "missing": good["missing_courses"]}
    del renamed["missing_courses"]
    assert _contract_errors(renamed, schema, spec)
    assert _contract_errors({**good, "eligible": "yes"}, schema, spec)
