"""Seed phải từ chối dữ liệu tiên quyết có vòng (M2 × M4)."""

import pytest

from app.seed import _check_acyclic
from app.seed_data import PrereqRow, build_dataset

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("profile", ["minimal", "default"])
def test_seed_profiles_are_acyclic(profile):
    assert _check_acyclic(build_dataset(profile)) == []


def test_seed_with_cycle_is_rejected():
    ds = build_dataset("minimal")
    # INT131 vốn là tiên quyết gốc của chuỗi; thêm "INT131 cần INT341" tạo vòng
    ds.prereqs.append(PrereqRow("INT131", "INT341", "AND", 0))
    errors = _check_acyclic(ds)
    assert len(errors) == 1 and "vòng" in errors[0]
    assert "INT131" in errors[0] and "INT341" in errors[0]
