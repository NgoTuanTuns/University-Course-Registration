"""Pre-authenticate load-test students at a controlled rate and save access tokens."""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import math
import os
import time
from collections import Counter
from pathlib import Path

import httpx


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    index = max(
        0,
        min(len(ordered) - 1, math.ceil(percentile / 100 * len(ordered)) - 1),
    )
    return ordered[index]


def _student_account_order(row: dict[str, str]) -> tuple[int, int]:
    """Prefer generated students; keep M4's pre-enrolled edge-case kit as fallback."""
    mssv = row.get("mssv", "")
    try:
        number = int(mssv.removeprefix("SV"))
    except ValueError:
        number = 0
    return (0 if number >= 55 else 1, number)


async def _login_one(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    row: dict[str, str],
    scheduled_at: float,
    started_at: float,
) -> tuple[str, float, str | None, str | None]:
    await asyncio.sleep(max(0, scheduled_at - (time.monotonic() - started_at)))
    async with semaphore:
        began = time.monotonic()
        try:
            response = await client.post(
                "/api/v1/auth/login",
                json={"email": row["email"], "password": row["password"]},
            )
            elapsed = time.monotonic() - began
            if response.status_code != 200:
                return row["email"], elapsed, None, f"HTTP {response.status_code}"
            payload = response.json()
            token = payload.get("access_token") if isinstance(payload, dict) else None
            if not isinstance(token, str) or not token:
                return row["email"], elapsed, None, "missing access token"
            return row["email"], elapsed, token, None
        except (httpx.HTTPError, ValueError) as exc:
            return row["email"], time.monotonic() - began, None, type(exc).__name__


async def prepare_users(
    api_url: str,
    users_file: Path,
    tokens_file: Path,
    expected_users: int,
    rate_per_second: float,
    concurrency: int,
    summary_file: Path,
) -> int:
    with users_file.open(newline="", encoding="utf-8-sig") as stream:
        rows = [row for row in csv.DictReader(stream) if row.get("role") == "student"]
    rows.sort(key=_student_account_order)
    if len(rows) < expected_users:
        raise ValueError(
            f"Expected at least {expected_users} student accounts; found {len(rows)}."
        )
    rows = rows[:expected_users]
    if any(not row.get("email") or not row.get("password") for row in rows):
        raise ValueError("The user export contains an empty email or password.")

    semaphore = asyncio.Semaphore(concurrency)
    timeout = httpx.Timeout(15.0, connect=5.0)
    started_at = time.monotonic()
    async with httpx.AsyncClient(
        base_url=api_url.rstrip("/"), timeout=timeout
    ) as client:
        results = await asyncio.gather(
            *(
                _login_one(
                    client,
                    semaphore,
                    row,
                    index / rate_per_second,
                    started_at,
                )
                for index, row in enumerate(rows)
            )
        )

    failures = [error for _, _, _, error in results if error]
    if failures:
        tokens_file.unlink(missing_ok=True)
        print(
            f"Pre-login failed for {len(failures)} accounts; "
            "token file was not written."
        )
        print("Failure categories (no account values): " + str(dict(Counter(failures))))
        print("Inspect API health and rerun; the local credential CSV was retained.")
        return 1

    tokens_file.parent.mkdir(parents=True, exist_ok=True)
    temporary = tokens_file.with_suffix(tokens_file.suffix + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["email", "access_token"])
        for email, _, token, _ in results:
            writer.writerow([email, token])
    os.replace(temporary, tokens_file)

    durations = [elapsed for _, elapsed, _, _ in results]
    summary_file.parent.mkdir(parents=True, exist_ok=True)
    summary_file.write_text(
        json.dumps(
            {
                "students": len(results),
                "rate_per_second": rate_per_second,
                "concurrency": concurrency,
                "p50_seconds": _percentile(durations, 50),
                "p95_seconds": _percentile(durations, 95),
                "elapsed_seconds": round(time.monotonic() - started_at, 3),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        f"Pre-login completed: {len(results)} students; "
        f"P50={_percentile(durations, 50):.3f}s, "
        f"P95={_percentile(durations, 95):.3f}s; "
        f"duration={time.monotonic() - started_at:.1f}s."
    )
    print(f"Tokens saved to {tokens_file}; credential values were not printed.")
    users_file.unlink(missing_ok=True)
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", default="http://api-loadtest:8000")
    parser.add_argument("--users-file", default="/data/users.csv", type=Path)
    parser.add_argument("--tokens-file", default="/data/tokens.csv", type=Path)
    parser.add_argument(
        "--summary-file",
        default=f"/reports/{os.getenv('LOADTEST_RUN_ID', 'manual')}_login.json",
        type=Path,
    )
    parser.add_argument("--expected-users", type=int, default=2000)
    parser.add_argument("--rate", type=float, default=20.0, help="logins per second")
    parser.add_argument("--concurrency", type=int, default=20)
    args = parser.parse_args()
    if args.expected_users < 1 or args.rate <= 0 or args.concurrency < 1:
        parser.error("expected-users, rate, and concurrency must be positive")
    raise SystemExit(
        asyncio.run(
            prepare_users(
                args.api_url,
                args.users_file,
                args.tokens_file,
                args.expected_users,
                args.rate,
                args.concurrency,
                args.summary_file,
            )
        )
    )


if __name__ == "__main__":
    main()
