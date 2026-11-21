import pytest

from app.tools.reset_loadtest import validate_loadtest_target

pytestmark = pytest.mark.unit

SAFE_DB = "postgresql+asyncpg://course_user@db:5432/course_reg_loadtest"
SAFE_REDIS = "redis://redis:6379/2"


def test_accepts_only_the_dedicated_loadtest_targets():
    validate_loadtest_target("loadtest", SAFE_DB, SAFE_REDIS)


@pytest.mark.parametrize(
    ("app_env", "database_url", "redis_url"),
    [
        ("dev", SAFE_DB, SAFE_REDIS),
        ("loadtest", SAFE_DB.replace("course_reg_loadtest", "course_reg"), SAFE_REDIS),
        ("loadtest", SAFE_DB.replace("@db:", "@localhost:"), SAFE_REDIS),
        ("loadtest", SAFE_DB, SAFE_REDIS.replace("/2", "/0")),
    ],
)
def test_refuses_any_nonisolated_reset_target(app_env, database_url, redis_url):
    with pytest.raises(ValueError, match="Refusing reset"):
        validate_loadtest_target(app_env, database_url, redis_url)
