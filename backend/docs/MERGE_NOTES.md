# Merge notes — Prerequisite Engine

## Integrated files

- `app/services/prerequisite_engine.py` — prerequisite graph and eligibility engine.
- `app/api/v1/prerequisites.py` — `GET /prerequisites/check` router.
- `app/schemas/prerequisite.py` — response schemas.
- `app/core/database.py` — lazy async SQLAlchemy session dependency required by the router.
- `tests/test_prerequisite_engine.py` — engine unit tests.
- `docs/prerequisite-engine.md` — design notes.

## Existing files reused

The backend already contained:
- `app/models/prerequisite.py`
- `app/models/completed_course.py`
- `app/models/course.py`
- `app/core/security.py`

These were not overwritten. The existing prerequisite model already matches the engine's expected columns:
`course_id`, `prereq_course_id`, `type`, and `group_no`.

No Alembic migration was added because the `prerequisites` and `completed_courses` tables are already present in the initial migration.

## API wiring

The supplied backend archive did not contain an application entry point (`main.py`) or an existing router aggregator. Therefore, the new router is placed alongside the existing `app/api/v1/auth.py` and is not auto-registered.

When the FastAPI application is created, include it under the existing `/api/v1` prefix, for example:

```python
from app.api.v1.prerequisites import router as prerequisites_router

app.include_router(prerequisites_router, prefix="/api/v1")
```

The resulting endpoint is:
`GET /api/v1/prerequisites/check?course_id=<id>`

## Database configuration

Set `DATABASE_URL` to an async SQLAlchemy URL, e.g.:

`postgresql+asyncpg://user:password@localhost:5432/university`

The dependency also converts a standard `postgresql://` URL to the asyncpg dialect.
Ensure `asyncpg` is installed in the project's runtime dependencies. The existing
`app/core/security.py` also imports `bcrypt`, which must already be installed by the project.

## Verification

From the `backend` directory:

`python -m pytest -q`

Result in the merge environment: **58 passed**.

Python compilation check: passed.

The tests do not require a live PostgreSQL database. Database-backed endpoint behavior still needs an integration test against the project's configured database.
