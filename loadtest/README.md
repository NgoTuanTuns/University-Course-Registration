# M5 load-test environment

This profile is isolated from the normal `course_reg` database and Redis DB 0. It uses the dedicated PostgreSQL database `course_reg_loadtest`, Redis DB 2, and an API process without `--reload`. The reset command refuses to run unless `APP_ENV=loadtest`, the DB host/name match the dedicated target, and Redis DB 2 is selected.

## One-time setup (PowerShell)

From the repository root, make sure Docker Desktop is running and `.env` exists. The `db` service creates `course_reg_loadtest` automatically only when PostgreSQL initializes a new volume. For an existing `postgres_data` volume, create it explicitly; the command is idempotent:

```powershell
docker compose up -d db redis
docker compose exec db sh /docker-entrypoint-initdb.d/20-create-loadtest-db.sh
```

Start the load-test API only after the reset tool has applied migrations and seeded the dedicated database, as shown below.

The locust image is the official `locustio/locust` image pinned to 2.47.0. A custom shape ramps toward 2,000 users at about 67 users/second over 30 seconds, then holds for 150 seconds. Locust documents this image and its `LoadTestShape` API in [Running Locust in Docker](https://docs.locust.io/en/stable/running-in-docker.html) and [Custom load shapes](https://docs.locust.io/en/stable/custom-load-shape.html).

## Before each run

This reset is destructive to `course_reg_loadtest` by design. It does not touch `course_reg` or `course_reg_test`. Stop only the prior load-test services before resetting; do not use `docker compose down -v`.

```powershell
$env:LOADTEST_RUN_ID = Get-Date -Format 'yyyyMMdd-HHmmss'
$env:LOADTEST_USERS = '2000'
docker compose --profile loadtest stop locust api-loadtest
docker compose --profile loadtest run --rm api-loadtest python -m app.tools.reset_loadtest
docker compose --profile loadtest up -d api-loadtest
docker compose --profile loadtest run --rm api-loadtest python -m app.tools.prepare_loadtest_users --expected-users 2000 --rate 20 --concurrency 20
```

The reset creates M4's loadtest seed and writes a CSV containing passwords to ignored local path `loadtest/data/users.csv`. The pre-login step prefers generated students without pre-seeded active registrations; M4's 54 special kit accounts remain fallback so a 2,000-user run still receives 2,000 unique accounts. It runs at a controlled rate, reports login P50/P95 separately, writes only access tokens to `loadtest/data/tokens.csv`, and deletes the password CSV after all logins succeed. Do not copy these files into a report or commit them. Access tokens live for a limited time; prepare them immediately before each run.

For a smoke run, set both the pre-login count and Locust user count to the same small number (for example 50). The seed still has 2,000 students; the pre-login tool uses only the first N student rows. A smoke run is for checking wiring, not baseline evidence.

## Baseline scenarios

`LOADTEST_SCENARIO` can be `mixed`, `registration`, `cancellation`, `read`, or `hot5`. `mixed` distributes virtual users across the registration flow, cancellation, read-heavy requests, and five shared offerings. `hot5` and `cancellation` use `BAS101` through `BAS105` by default. BAS is available to all seeded faculties; in the loadtest profile these five offerings have capacity 5 each (other profiles keep their original capacity), so all users can create real contention without faculty-filter false failures.

```powershell
$env:LOADTEST_SCENARIO = 'mixed'
$env:LOADTEST_RAMP_SECONDS = '30'
$env:LOADTEST_HOLD_SECONDS = '150'
docker compose --profile loadtest up --abort-on-container-exit --exit-code-from locust locust
docker compose --profile loadtest run --rm api-loadtest python -m app.tools.invariants
```

Repeat the reset, pre-login, run, and invariant check at least three times with a distinct `LOADTEST_RUN_ID`. Compare medians and ranges, not one run. Preserve Locust CSV/HTML and business-outcome JSON under ignored `loadtest/reports/`.

For the hot5 registration flow, verify each run records 2,000 requests for `GET /courses`, `GET /prerequisites/check`, `POST /enroll`, and `GET /timetable`. Any lower count means the user flow ended early and the run is not comparable to the specified acceptance path.

Record the machine CPU/RAM, Docker Desktop resource limits, image/container versions, scenario, user count, ramp/hold duration, login P50/P95, endpoint P50/P95/P99, requests/second, HTTP 2xx, expected business 4xx, unexpected 4xx/5xx/timeouts, `CONCURRENT_UPDATE`, `WAITLISTED`, `WAITLIST_FULL`, PostgreSQL activity/lock waits, and `docker stats`. Each run must finish with zero I1–I9 invariant violations and 100% seat-count consistency. Do not choose an acceptance P95 threshold until the baseline exists and the team agrees on D28.

## Safety and interpretation

- A reset truncates data. The guard allows only `APP_ENV=loadtest`, PostgreSQL host `db` / database `course_reg_loadtest`, and Redis host `redis` / DB 2.
- The load-test API sets `APP_ENV=loadtest`, which disables rate limiting. That environment is profile-only and must not be used for ordinary development or deployment.
- Seeded business rejections such as `PREREQ_NOT_MET`, `SCHEDULE_CONFLICT`, `ALREADY_ENROLLED`, `WAITLIST_FULL`, and `CONCURRENT_UPDATE` are counted as business outcomes, not transport failures. Unexpected 4xx, 5xx, timeouts, and missing test data are failures.
- Pre-login is measured separately; the spike begins with already-held access tokens so bcrypt login cost does not distort the registration window.
- Do not run the 2,000-user profile on a machine whose available CPU/RAM cannot sustain it. Record resource pressure and stop if Docker Desktop or the host becomes unresponsive.
- The 60–90 minute bug bash and review #2 require all five members. Their status remains pending until they participate.
