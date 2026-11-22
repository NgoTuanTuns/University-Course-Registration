"""Unit test cho dịch vụ quản lý giai đoạn đợt đăng ký (Registration Phase Control)."""

from datetime import UTC, datetime, timedelta

import pytest

from app.services.phase_service import (
    PHASE_METADATA,
    VALID_PHASES,
    build_phase_payload,
    phase_permissions,
)

pytestmark = pytest.mark.unit


def test_valid_phases_have_complete_metadata():
    assert set(VALID_PHASES) == {
        "STUDY_PLAN_OPEN",
        "CLASS_OPENING_REVIEW",
        "ENROLLMENT_OPEN",
        "LOCKED",
    }
    for phase in VALID_PHASES:
        assert PHASE_METADATA[phase]["label"]
        assert PHASE_METADATA[phase]["description"]


@pytest.mark.parametrize(
    ("phase", "expected_sp", "expected_enroll"),
    [
        ("STUDY_PLAN_OPEN", True, False),
        ("CLASS_OPENING_REVIEW", False, False),
        ("ENROLLMENT_OPEN", False, True),
        ("LOCKED", False, False),
    ],
)
def test_phase_permissions_matrix(phase, expected_sp, expected_enroll):
    assert phase_permissions(phase) == (expected_sp, expected_enroll)


def test_phase_permissions_rejects_unknown_phase():
    with pytest.raises(ValueError, match="không hợp lệ"):
        phase_permissions("UNKNOWN_PHASE")


def test_build_phase_payload_includes_deadline_and_flags():
    ends = datetime.now(UTC) + timedelta(days=5)
    payload = build_phase_payload(
        "2026-2",
        "ENROLLMENT_OPEN",
        phase_ends_at=ends,
        note="Mở đăng ký chính thức",
    )
    assert payload["term"] == "2026-2"
    assert payload["phase"] == "ENROLLMENT_OPEN"
    assert payload["can_edit_study_plan"] is False
    assert payload["can_enroll"] is True
    assert payload["phase_ends_at"] == ends
    assert payload["note"] == "Mở đăng ký chính thức"
