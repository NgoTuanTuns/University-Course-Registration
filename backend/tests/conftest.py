"""Shared fixtures for backend integration and concurrency tests."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

import pytest

backend_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_root))

test_database_url = os.environ.get("TEST_DATABASE_URL", "")
if urlparse(test_database_url).path.lstrip("/") != "course_reg_test":
    raise RuntimeError("Tests must use the isolated course_reg_test database")

os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = test_database_url
os.environ["ALEMBIC_DATABASE_URL"] = test_database_url
os.environ["REDIS_URL"] = os.environ.get(
    "TEST_REDIS_URL",
    "redis://redis:6379/1",
)

from alembic.config import Config  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from redis.asyncio import Redis  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    async_sessionmaker,
    create_async_engine,
)

from alembic import command  # noqa: E402
from app.core.db import get_session  # noqa: E402
from app.core.tokens import create_access_token  # noqa: E402
from app.main import app  # noqa: E402
from app.models import (  # noqa: E402
    CompletedCourse,
    Course,
    CourseOffering,
    Prerequisite,
    Student,
)


def pytest_sessionstart(session: pytest.Session) -> None:
    del session
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "alembic"))
    command.upgrade(config, "head")


@pytest.fixture
async def test_engine():
    engine = create_async_engine(test_database_url, pool_pre_ping=True)
    yield engine
    await engine.dispose()


@pytest.fixture
async def clean_test_data(test_engine):
    async with test_engine.begin() as connection:
        await connection.execute(
            text(
                "TRUNCATE TABLE waitlist, enrollments, completed_courses, "
                "prerequisites, course_offerings, courses, students "
                "RESTART IDENTITY CASCADE"
            )
        )
    redis = Redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
    await redis.flushdb()
    await redis.aclose()


@pytest.fixture
async def test_session(test_engine, clean_test_data):
    del clean_test_data
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest.fixture
async def async_client(test_engine, clean_test_data):
    del clean_test_data
    factory = async_sessionmaker(test_engine, expire_on_commit=False)

    async def override_get_session():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
    app.dependency_overrides.pop(get_session, None)


@pytest.fixture
def make_student():
    async def factory(session, role="student", max_credits=25):
        from uuid import uuid4

        suffix = uuid4().hex[:10]
        item = Student(
            mssv=f"S{suffix}" if role == "student" else None,
            email=f"{suffix}@example.test",
            password_hash="test-placeholder-hash",
            full_name=f"Test {suffix}",
            role=role,
            max_credits=max_credits,
        )
        session.add(item)
        await session.flush()
        return item

    return factory


@pytest.fixture
def make_course():
    async def factory(session, code=None, name="Test course", credits=3):
        from uuid import uuid4

        item = Course(
            code=code or f"T{uuid4().hex[:8].upper()}",
            name=name,
            credits=credits,
        )
        session.add(item)
        await session.flush()
        return item

    return factory


@pytest.fixture
def make_offering():
    async def factory(session, course, capacity=30, schedule=None):
        from uuid import uuid4

        item = CourseOffering(
            course_id=course.id,
            term="2026-1",
            section=uuid4().hex[:8].upper(),
            capacity=capacity,
            enrolled_count=0,
            schedule=schedule or [{"day": 2, "start": "07:00", "end": "09:30"}],
        )
        session.add(item)
        await session.flush()
        return item

    return factory


@pytest.fixture
def add_prereq():
    async def factory(session, course, prereq, prerequisite_type="AND", group_no=0):
        item = Prerequisite(
            course_id=course.id,
            prereq_course_id=prereq.id,
            type=prerequisite_type,
            group_no=group_no,
        )
        session.add(item)
        await session.flush()
        return item

    return factory


@pytest.fixture
def complete():
    async def factory(session, student, course, grade=8.0, term="2025-1"):
        item = CompletedCourse(
            student_id=student.id,
            course_id=course.id,
            grade=grade,
            term=term,
        )
        session.add(item)
        await session.flush()
        return item

    return factory


@pytest.fixture
def login_as():
    def factory(student):
        token = create_access_token(student.id, student.role, student.email)
        return {"Authorization": f"Bearer {token}"}

    return factory


@pytest.fixture
def run_concurrently(test_engine, clean_test_data):
    async def run(task_count, operation):
        barrier = asyncio.Barrier(task_count)
        factory = async_sessionmaker(test_engine, expire_on_commit=False)

        async def worker(index):
            async with factory() as session:
                await barrier.wait()
                return await operation(session, index)

        return await asyncio.gather(*(worker(index) for index in range(task_count)))

    return run
