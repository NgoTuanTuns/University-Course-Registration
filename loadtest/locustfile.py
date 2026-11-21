"""Repeatable M5 baseline scenarios for the isolated load-test profile."""

from __future__ import annotations

import csv
import json
import math
import os
import random
import time
from collections import Counter
from pathlib import Path

import gevent
from locust import HttpUser, LoadTestShape, between, events, task

TOKEN_FILE = Path(os.getenv("LOADTEST_TOKENS_FILE", "/data/tokens.csv"))
SCENARIO = os.getenv("LOADTEST_SCENARIO", "mixed").lower()
TERM = os.getenv("LOADTEST_TERM", "2026-1")
MAX_USERS = int(os.getenv("LOADTEST_USERS", "2000"))
RAMP_SECONDS = int(os.getenv("LOADTEST_RAMP_SECONDS", "30"))
HOLD_SECONDS = int(os.getenv("LOADTEST_HOLD_SECONDS", "150"))
RUN_ID = os.getenv("LOADTEST_RUN_ID", "manual")
HOT_CODES = tuple(
    code.strip()
    for code in os.getenv(
        "LOADTEST_HOT_COURSE_CODES", "BAS101,BAS102,BAS103,BAS104,BAS105"
    ).split(",")
    if code.strip()
)
BUSINESS_CODES = {
    "ALREADY_ENROLLED",
    "ALREADY_COMPLETED",
    "ALREADY_WAITLISTED",
    "CONCURRENT_UPDATE",
    "CREDIT_LIMIT_EXCEEDED",
    "MIN_ACCUMULATED_CREDITS_NOT_MET",
    "PREREQ_NOT_MET",
    "SCHEDULE_CONFLICT",
    "WAITLIST_FULL",
}
OUTCOMES: Counter[str] = Counter()
TEST_STARTED_AT = 0.0
if MAX_USERS < 1 or RAMP_SECONDS < 1 or HOLD_SECONDS < 1:
    raise RuntimeError(
        "LOADTEST_USERS, ramp seconds, and hold seconds must be positive."
    )
if (
    not RUN_ID
    or RUN_ID in {".", ".."}
    or any(
        char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
        for char in RUN_ID
    )
):
    raise RuntimeError(
        "LOADTEST_RUN_ID may contain only letters, digits, dot, dash, underscore."
    )
if SCENARIO not in {"mixed", "registration", "cancellation", "read", "hot5"}:
    raise RuntimeError(f"Unsupported LOADTEST_SCENARIO: {SCENARIO}")
if len(set(HOT_CODES)) != 5:
    raise RuntimeError(
        "LOADTEST_HOT_COURSE_CODES must contain five unique course codes."
    )


def _load_tokens() -> list[dict[str, str]]:
    if not TOKEN_FILE.is_file():
        raise RuntimeError(
            f"Missing {TOKEN_FILE}; reset the load-test DB and pre-login first."
        )
    with TOKEN_FILE.open(newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != MAX_USERS or any(not row.get("access_token") for row in rows):
        raise RuntimeError(
            f"Expected {MAX_USERS} student access tokens in {TOKEN_FILE}; "
            f"found {len(rows)}."
        )
    return rows


TOKENS = _load_tokens()
_next_token = 0


class RegistrationUser(HttpUser):
    """One pre-authenticated, unique student account per virtual user."""

    wait_time = between(0.2, 1.0)
    network_timeout = 10
    connection_timeout = 5

    def on_start(self) -> None:
        global _next_token
        if _next_token >= len(TOKENS):
            raise RuntimeError(
                "More Locust users than pre-authenticated student tokens."
            )
        token = TOKENS[_next_token]["access_token"]
        _next_token += 1
        self.headers = {"Authorization": f"Bearer {token}"}
        self.scenario_completed = False

    def _get_json(self, path: str, *, params: dict, name: str) -> dict | None:
        with self.client.get(
            path, params=params, headers=self.headers, name=name, catch_response=True
        ) as response:
            if response.status_code != 200:
                response.failure(f"unexpected HTTP {response.status_code}")
                return None
            try:
                body = response.json()
            except ValueError:
                response.failure("response was not JSON")
                return None
            response.success()
            return body

    def _search(self, query: str) -> list[dict]:
        payload = self._get_json(
            "/api/v1/courses",
            params={"q": query, "term": TERM, "page": 1, "page_size": 100},
            name="GET /courses (search)",
        )
        if payload is None:
            return []
        items = payload.get("items", [])
        if not items:
            OUTCOMES["LOADTEST_NO_COURSE_MATCH"] += 1
        return items

    def _get_timetable(self) -> None:
        self._get_json(
            "/api/v1/timetable",
            params={"term": TERM},
            name="GET /timetable",
        )

    def _registration_flow(self, query: str, cancel_after: bool = False) -> None:
        offerings = self._search(query)
        if not offerings:
            self._get_timetable()
            return
        offering = random.choice(offerings)
        course_id = offering.get("course_id")
        offering_id = offering.get("id")
        if not isinstance(course_id, int) or not isinstance(offering_id, int):
            OUTCOMES["LOADTEST_BAD_COURSE_RESPONSE"] += 1
            self._get_timetable()
            return

        self._get_json(
            "/api/v1/prerequisites/check",
            params={"course_id": course_id},
            name="GET /prerequisites/check",
        )

        enrollment: dict | None = None
        with self.client.post(
            "/api/v1/enroll",
            json={"offering_id": offering_id},
            headers=self.headers,
            name="POST /enroll",
            catch_response=True,
        ) as response:
            if response.status_code in (200, 201):
                try:
                    enrollment = response.json()
                except ValueError:
                    response.failure("enrollment response was not JSON")
                else:
                    outcome = enrollment.get("status", "UNKNOWN")
                    if outcome not in {"ACTIVE", "WAITLISTED"}:
                        response.failure(f"unexpected enrollment status {outcome!r}")
                        enrollment = None
                    else:
                        OUTCOMES[outcome] += 1
                        response.success()
            elif 400 <= response.status_code < 500:
                try:
                    code = response.json().get("detail", {}).get("code")
                except (ValueError, AttributeError):
                    code = None
                if code in BUSINESS_CODES:
                    OUTCOMES[code] += 1
                    response.success()
                else:
                    OUTCOMES[f"UNEXPECTED_4XX_{response.status_code}"] += 1
                    response.failure(f"unexpected business response {code!r}")
            else:
                OUTCOMES[f"HTTP_{response.status_code}"] += 1
                response.failure(f"unexpected HTTP {response.status_code}")

        if enrollment is None:
            self._get_timetable()
            return
        if cancel_after:
            # Hold successful registrations and release their cancellations together
            # after the arrival ramp, creating a reproducible cancellation wave.
            cancellation_deadline = TEST_STARTED_AT + RAMP_SECONDS + 10
            gevent.sleep(max(0, cancellation_deadline - time.time()))

        if cancel_after and enrollment.get("status") == "ACTIVE":
            self._cancel_enrollment(enrollment.get("id"))
        elif cancel_after and enrollment.get("status") == "WAITLISTED":
            self._cancel_waitlist(offering_id)

        self._get_timetable()

    def _cancel_enrollment(self, enrollment_id: int | None) -> None:
        if not isinstance(enrollment_id, int):
            return
        with self.client.delete(
            f"/api/v1/enroll/{enrollment_id}",
            headers=self.headers,
            name="DELETE /enroll/{enrollment_id} (cancellation)",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                OUTCOMES["CANCELLED_ACTIVE"] += 1
                response.success()
            elif 400 <= response.status_code < 500:
                try:
                    code = response.json().get("detail", {}).get("code")
                except (ValueError, AttributeError):
                    code = None
                if code in BUSINESS_CODES:
                    OUTCOMES[code] += 1
                    response.success()
                else:
                    response.failure(f"unexpected cancellation response {code!r}")
            else:
                response.failure(f"unexpected HTTP {response.status_code}")

    def _cancel_waitlist(self, offering_id: int) -> None:
        payload = self._get_json(
            "/api/v1/waitlist",
            params={"page": 1, "page_size": 100},
            name="GET /waitlist (cancellation lookup)",
        )
        if payload is None:
            return
        row = next(
            (
                item
                for item in payload.get("items", [])
                if item.get("id") == offering_id
            ),
            None,
        )
        if row is None:
            return
        waitlist_id = row.get("waitlist_id")
        if not isinstance(waitlist_id, int):
            return
        with self.client.delete(
            f"/api/v1/waitlist/{waitlist_id}",
            headers=self.headers,
            name="DELETE /waitlist/{waitlist_id} (cancellation)",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                OUTCOMES["CANCELLED_WAITLIST"] += 1
                response.success()
            else:
                response.failure(f"unexpected HTTP {response.status_code}")

    @task
    def exercise_scenario(self) -> None:
        scenario = SCENARIO
        if scenario == "mixed":
            scenario = random.choices(
                ["registration", "cancellation", "read", "hot5"],
                weights=[60, 20, 15, 5],
                k=1,
            )[0]

        # Registration scenarios model one student making one registration attempt.
        # Only read-heavy mode deliberately loops to generate sustained query traffic.
        if self.scenario_completed:
            return

        if scenario == "read":
            offerings = self._search(random.choice(["BAS", "MAT"]))
            if offerings:
                course_id = random.choice(offerings).get("course_id")
                if isinstance(course_id, int):
                    self._get_json(
                        "/api/v1/prerequisites/check",
                        params={"course_id": course_id},
                        name="GET /prerequisites/check",
                    )
            self._get_json(
                "/api/v1/timetable",
                params={"term": TERM},
                name="GET /timetable",
            )
        elif scenario == "hot5":
            if len(HOT_CODES) != 5:
                OUTCOMES["LOADTEST_INVALID_HOT_CODE_CONFIG"] += 1
                return
            self.scenario_completed = True
            self._registration_flow(random.choice(HOT_CODES))
        elif scenario == "cancellation":
            self.scenario_completed = True
            self._registration_flow(random.choice(HOT_CODES), cancel_after=True)
        elif scenario == "registration":
            self.scenario_completed = True
            self._registration_flow("BAS")
        else:
            OUTCOMES["LOADTEST_INVALID_SCENARIO"] += 1


class RegistrationSpikeShape(LoadTestShape):
    """Ramp to 2,000 users over 30 seconds, then hold for a repeatable period."""

    def tick(self) -> tuple[int, float] | None:
        elapsed = self.get_run_time()
        if elapsed >= RAMP_SECONDS + HOLD_SECONDS:
            return None
        spawn_rate = MAX_USERS / RAMP_SECONDS
        if elapsed < RAMP_SECONDS:
            return max(1, math.ceil(MAX_USERS * elapsed / RAMP_SECONDS)), spawn_rate
        return MAX_USERS, spawn_rate


@events.test_start.add_listener
def mark_test_start(**_kwargs) -> None:
    global TEST_STARTED_AT
    TEST_STARTED_AT = time.time()


@events.test_stop.add_listener
def write_business_outcomes(environment, **_kwargs) -> None:
    reports_dir = Path("/reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    report = reports_dir / f"{RUN_ID}_business_outcomes.json"
    report.write_text(json.dumps(dict(OUTCOMES), indent=2), encoding="utf-8")
    if any(name.startswith(("LOADTEST_", "UNEXPECTED_", "HTTP_")) for name in OUTCOMES):
        environment.process_exit_code = 1
