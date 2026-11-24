"""Quy tắc tính học phí tạm tính theo tín chỉ cho từng nhóm học phần (VND)."""

from __future__ import annotations

DEFAULT_PAYMENT_DEADLINE = "2027-01-15"

# Đơn giá VND / tín chỉ và phụ phí thực hành / phòng máy theo nhóm mã học phần
_GENERAL_PREFIXES = frozenset({"BAS", "MAT", "PHY", "GEN"})
_TECH_PREFIXES = frozenset({"INT", "ELE", "ENG"})
_BUSINESS_PREFIXES = frozenset({"MAN", "ECO", "BUS"})

GENERAL_UNIT_PRICE = 950_000
TECH_UNIT_PRICE = 1_150_000
TECH_LAB_FEE = 150_000
BUSINESS_UNIT_PRICE = 1_050_000
DEFAULT_UNIT_PRICE = 1_000_000


def _course_prefix(code: str) -> str:
    return "".join(ch for ch in code if ch.isalpha())[:3].upper()


def classify_tuition_rate(course_code: str) -> tuple[str, int, int]:
    """Trả về (tên_nhóm_học_phí, đơn_giá_tín_chỉ_vnd, phụ_phí_phòng_máy_vnd)."""
    prefix = _course_prefix(course_code)
    if prefix in _GENERAL_PREFIXES:
        return ("Đại cương & Khoa học cơ bản", GENERAL_UNIT_PRICE, 0)
    if prefix in _TECH_PREFIXES:
        return ("Chuyên ngành Công nghệ & Kỹ thuật", TECH_UNIT_PRICE, TECH_LAB_FEE)
    if prefix in _BUSINESS_PREFIXES:
        return ("Kinh tế & Quản trị", BUSINESS_UNIT_PRICE, 0)
    return ("Học phần tiêu chuẩn", DEFAULT_UNIT_PRICE, 0)


def calculate_tuition_estimate(
    term: str,
    enrolled_rows: list[dict],
    *,
    payment_deadline: str = DEFAULT_PAYMENT_DEADLINE,
) -> dict:
    """Tổng hợp bảng kê học phí tạm tính từ danh sách lớp học phần đang ACTIVE."""
    items: list[dict] = []
    total_credits = 0
    tuition_subtotal = 0
    lab_fee_total = 0

    for row in enrolled_rows:
        code = str(row["course_code"])
        credits = int(row["credits"])
        category, unit_price, lab_fee = classify_tuition_rate(code)
        credit_cost = credits * unit_price
        subtotal = credit_cost + lab_fee

        total_credits += credits
        tuition_subtotal += credit_cost
        lab_fee_total += lab_fee

        items.append(
            {
                "enrollment_id": int(row["enrollment_id"]),
                "course_code": code,
                "course_name": str(row["course_name"]),
                "section": str(row["section"]),
                "credits": credits,
                "category": category,
                "unit_price": unit_price,
                "lab_fee": lab_fee,
                "subtotal": subtotal,
            }
        )

    items.sort(key=lambda it: (it["course_code"], it["section"]))

    return {
        "term": term,
        "currency": "VND",
        "status": "ESTIMATED",
        "payment_deadline": payment_deadline,
        "total_courses": len(items),
        "total_credits": total_credits,
        "tuition_subtotal": tuition_subtotal,
        "lab_fee_total": lab_fee_total,
        "total_amount": tuition_subtotal + lab_fee_total,
        "items": items,
    }
