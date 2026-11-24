"""Unit tests cho quy tắc tính học phí tạm tính theo tín chỉ (Tuition Estimator)."""

import pytest

from app.core.tuition import (
    BUSINESS_UNIT_PRICE,
    DEFAULT_UNIT_PRICE,
    GENERAL_UNIT_PRICE,
    TECH_LAB_FEE,
    TECH_UNIT_PRICE,
    calculate_tuition_estimate,
    classify_tuition_rate,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("code", "expected_unit", "expected_lab"),
    [
        ("INT131", TECH_UNIT_PRICE, TECH_LAB_FEE),
        ("ELE201", TECH_UNIT_PRICE, TECH_LAB_FEE),
        ("BAS101", GENERAL_UNIT_PRICE, 0),
        ("MAT208", GENERAL_UNIT_PRICE, 0),
        ("MAN101", BUSINESS_UNIT_PRICE, 0),
        ("LAW101", DEFAULT_UNIT_PRICE, 0),
    ],
)
def test_classify_tuition_rate_by_course_prefix(code, expected_unit, expected_lab):
    category, unit_price, lab_fee = classify_tuition_rate(code)
    assert category
    assert unit_price == expected_unit
    assert lab_fee == expected_lab


def test_calculate_tuition_estimate_empty():
    res = calculate_tuition_estimate("2026-2", [])
    assert res["term"] == "2026-2"
    assert res["currency"] == "VND"
    assert res["total_courses"] == 0
    assert res["total_credits"] == 0
    assert res["tuition_subtotal"] == 0
    assert res["lab_fee_total"] == 0
    assert res["total_amount"] == 0
    assert res["items"] == []


def test_calculate_tuition_estimate_mixed_courses():
    rows = [
        {
            "enrollment_id": 10,
            "course_code": "INT131",
            "course_name": "Lập trình hướng đối tượng",
            "section": "01",
            "credits": 3,
        },
        {
            "enrollment_id": 11,
            "course_code": "BAS101",
            "course_name": "Kỹ năng bổ trợ 1",
            "section": "02",
            "credits": 3,
        },
    ]
    res = calculate_tuition_estimate("2026-2", rows)
    assert res["total_courses"] == 2
    assert res["total_credits"] == 6
    expected_tuition = 3 * TECH_UNIT_PRICE + 3 * GENERAL_UNIT_PRICE
    assert res["tuition_subtotal"] == expected_tuition
    assert res["lab_fee_total"] == TECH_LAB_FEE
    assert res["total_amount"] == expected_tuition + TECH_LAB_FEE
    assert [it["course_code"] for it in res["items"]] == ["BAS101", "INT131"]
