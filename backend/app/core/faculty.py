"""Ánh xạ Khoa (faculty) -> danh sách tiền tố học phần được phép hiển thị và đăng ký."""

from __future__ import annotations

GENERAL_COURSE_PREFIXES: tuple[str, ...] = ("BAS", "MAT", "PHY", "ENG")

FACULTY_CNTT = "Khoa Công nghệ thông tin"
FACULTY_DIEN = "Khoa Điện - Điện tử"
FACULTY_QTKD = "Khoa Quản trị kinh doanh"

FACULTY_ALLOWED_PREFIXES: dict[str, tuple[str, ...]] = {
    FACULTY_CNTT: ("INT", *GENERAL_COURSE_PREFIXES),
    FACULTY_DIEN: ("ELE", *GENERAL_COURSE_PREFIXES),
    FACULTY_QTKD: ("MAN", "BAS", "MAT", "ENG"),
}

PREFIX_TO_FACULTY: dict[str, str] = {
    "INT": FACULTY_CNTT,
    "ELE": FACULTY_DIEN,
    "MAN": FACULTY_QTKD,
}


def allowed_prefixes_for_faculty(faculty: str | None) -> tuple[str, ...] | None:
    """Trả về tuple tiền tố môn được phép cho khoa. None nếu không giới hạn (admin / chưa gán khoa)."""
    if not faculty:
        return None
    return FACULTY_ALLOWED_PREFIXES.get(faculty)


def course_allowed_for_faculty(course_code: str, faculty: str | None) -> bool:
    prefixes = allowed_prefixes_for_faculty(faculty)
    if prefixes is None:
        return True
    upper = course_code.upper()
    return any(upper.startswith(p) for p in prefixes)
