import json
from pathlib import Path

import pytest

from app.services.schedule_conflict import find_schedule_conflicts

pytestmark = pytest.mark.unit
VECTORS = json.loads(
    (
        Path(__file__).resolve().parents[2] / "docs/schedule-test-vectors.json"
    ).read_text()
)


@pytest.mark.parametrize("case", VECTORS, ids=[v["name"] for v in VECTORS])
def test_shared_schedule_vectors(case):
    assert (
        bool(
            find_schedule_conflicts(case["candidate"], [{"schedule": case["existing"]}])
        )
        == case["conflict"]
    )


def test_minimum_break():
    case = next(c for c in VECTORS if c["name"] == "adjacent")
    assert find_schedule_conflicts(
        case["candidate"], [{"schedule": case["existing"]}], 5
    )
