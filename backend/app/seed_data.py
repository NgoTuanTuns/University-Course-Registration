"""Bộ sinh dữ liệu mẫu THUẦN PYTHON (không cần DB, không cần thư viện ngoài).

Tách riêng khỏi seed.py để:
  - kiểm thử được ngay (tests/test_seed_data.py) mà không cần PostgreSQL;
  - M2/M3/M5 có thể dùng `build_dataset("minimal")` làm "nguồn sự thật" cho test.

Theo quy ước nhóm (Mục 6) và dùng chung cho cả nhóm:
  - ngày trong tuần: day 1 = Thứ Hai ... day 6 = Thứ Bảy, 7 = Chủ nhật;
  - lịch chỉ nằm trong khung 07:00-21:00;
  - hạt giống cố định => cùng profile luôn cho đúng cùng dữ liệu;
  - dữ liệu NHẤT QUÁN: enrolled_count = số đăng ký ACTIVE, position hàng chờ liên tục từ 1,
    completed_courses "đóng" theo tiên quyết (ai đã học Y thì cũng đã học các môn Y cần).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from app.core.faculty import (
    FACULTY_CNTT,
    FACULTY_DIEN,
    FACULTY_QTKD,
    PREFIX_TO_FACULTY,
    course_allowed_for_faculty,
)

TERM = "2026-1"
STUDY_PLAN_TERM = "2026-2"
MIN_PLAN_STUDENTS_TO_OPEN = 15
SEED = 20261
ADMIN_EMAIL = "admin@uni.edu.vn"
ADMIN_PASSWORD = "Admin@123"
STUDENT_PASSWORD = "Student@123"
EMAIL_DOMAIN = "uni.edu.vn"

DEFAULT_STUDENT_COUNT = 1000  # sv0001 ... sv1000
GENERATED_COURSE_COUNT = 180  # + 12 kit + 8 BAS = 200 học phần ở profile default

# 5 Ca học chuẩn Đại học Tôn Đức Thắng (mỗi ca 3 tiết = 2 giờ 30 phút)
# Tập trung vào 4 ca đầu (Ca 1–Ca 4); Ca 5 (buổi tối) chỉ dành cho môn đặc biệt
MAIN_SHIFTS = [
    ("06:50", "09:20"),  # Ca 1 (Tiết 1–3)
    ("09:30", "12:00"),  # Ca 2 (Tiết 4–6)
    ("12:45", "15:15"),  # Ca 3 (Tiết 7–9)
    ("15:25", "17:55"),  # Ca 4 (Tiết 10–12)
]
SHIFT_5 = ("18:05", "20:35")  # Ca 5 (Tiết 13–15, chỉ áp dụng môn đặc biệt)
SLOTS = [*MAIN_SHIFTS, SHIFT_5]
_BASE_ENROLL = datetime(2026, 8, 1, tzinfo=UTC)
_BASE_WAIT = datetime(2026, 8, 2, tzinfo=UTC)

# --------------------------------------------------------------------------- kiểu dữ liệu


_MIN_CREDITS_BY_LEVEL: dict[int, int] = {
    1: 0,
    2: 3,
    3: 6,
    4: 15,
    5: 24,
    6: 36,
    7: 48,
}


@dataclass
class CourseRow:
    code: str
    name: str
    credits: int
    level: int  # tầng trong DAG (chỉ để sinh dữ liệu; không lưu DB)
    description: str | None = None
    min_accumulated_credits: int = 0


@dataclass
class PrereqRow:
    course_code: str
    prereq_code: str
    type: str  # 'AND' | 'OR'
    group_no: int


@dataclass
class OfferingRow:
    course_code: str
    section: str
    instructor: str | None
    capacity: int
    schedule: list[dict]
    room: str | None
    enrolled_count: int = 0
    term: str = TERM

    @property
    def key(self) -> tuple[str, str]:
        return (self.course_code, self.section)


@dataclass
class StudentRow:
    email: str
    mssv: str | None
    full_name: str
    role: str = "student"
    program: str | None = None
    max_credits: int = 25
    accumulated_credits: int = 0
    faculty: str | None = None


@dataclass
class CompletedRow:
    student_email: str
    course_code: str
    grade: float
    term: str


@dataclass
class EnrollmentRow:
    student_email: str
    offering_key: tuple[str, str]
    enrolled_at: datetime
    status: str = "ACTIVE"


@dataclass
class WaitlistRow:
    student_email: str
    offering_key: tuple[str, str]
    position: int
    enqueued_at: datetime


@dataclass
class StudyPlanRow:
    student_email: str
    course_code: str
    term: str = STUDY_PLAN_TERM


@dataclass
class TermCourseOpeningRow:
    term: str
    course_code: str
    planned_count: int
    min_required: int
    status: str  # 'PENDING' | 'OPENED' | 'NOT_OPENED'
    decided_at: datetime | None = None


@dataclass
class Dataset:
    profile: str
    courses: list[CourseRow] = field(default_factory=list)
    prereqs: list[PrereqRow] = field(default_factory=list)
    offerings: list[OfferingRow] = field(default_factory=list)
    students: list[StudentRow] = field(default_factory=list)
    completed: list[CompletedRow] = field(default_factory=list)
    enrollments: list[EnrollmentRow] = field(default_factory=list)
    waitlist: list[WaitlistRow] = field(default_factory=list)
    study_plans: list[StudyPlanRow] = field(default_factory=list)
    course_openings: list[TermCourseOpeningRow] = field(default_factory=list)

    # tiện ích tra cứu
    def course(self, code: str) -> CourseRow:
        return next(c for c in self.courses if c.code == code)

    def offering(self, code: str, section: str = "01") -> OfferingRow:
        return next(o for o in self.offerings if o.key == (code, section))


# --------------------------------------------------------------------------- KIT bắt buộc
# (mã, tên, tầng, [AND], [nhóm OR...])  -- tất cả 3 tín chỉ
KIT_COURSES = [
    ("INT101", "Nhập môn lập trình", 1, [], []),
    ("MAT201", "Giải tích 2", 1, [], []),
    ("MAT202", "Đại số tuyến tính", 1, [], []),
    ("INT131", "Lập trình hướng đối tượng", 2, ["INT101"], []),
    ("INT221", "Cấu trúc dữ liệu", 3, ["INT131"], []),
    ("INT222", "Cơ sở dữ liệu", 3, ["INT131"], []),
    ("INT231", "Giải thuật", 3, ["INT131"], []),
    ("INT321", "Hệ quản trị CSDL", 4, ["INT221", "INT222"], []),  # kim cương
    ("INT331", "Phân tích thiết kế hệ thống", 4, ["INT231"], []),
    ("INT341", "Học máy", 4, ["INT231"], [["MAT201", "MAT202"]]),  # AND + OR
    (
        "INT451",
        "Chuyên đề",
        4,
        [],
        [["MAT201", "MAT202"], ["INT221", "INT222"]],
    ),  # hai nhóm OR
    ("INT431", "Đồ án chuyên ngành", 5, ["INT331"], []),  # bắc cầu 4 tầng
]

# (mã, lịch [(day, start, end)], sức chứa)
KIT_OFFERINGS = [
    ("INT101", [(1, "07:00", "09:30"), (4, "07:00", "09:30")], 60),  # nhiều buổi/tuần
    ("INT131", [(2, "07:00", "09:30")], 50),
    ("INT221", [(3, "07:00", "09:30")], 50),
    ("INT222", [(3, "08:00", "10:30")], 50),  # TRÙNG INT221-01
    ("MAT201", [(3, "09:30", "11:30")], 60),  # LIỀN KỀ INT221-01, trùng INT222-01
    ("MAT202", [(2, "13:00", "15:30")], 60),
    ("INT231", [(1, "13:00", "15:30")], 30),  # SẮP ĐẦY (29/30)
    ("INT331", [(5, "07:00", "09:30")], 15),  # ĐẦY (15/15) + hàng chờ 3
    ("INT341", [(4, "13:00", "15:30")], 1),  # 1 CHỖ: demo tranh suất
    ("INT321", [(6, "07:00", "09:30")], 40),
    ("INT431", [(6, "09:30", "12:00")], 40),
    ("INT451", [(6, "13:00", "15:30")], 40),
]

# 8 học phần đệm để sv0004 đạt đúng 24 tín chỉ; 8 khung giờ không trùng nhau và KHÔNG chiếm Thứ Tư 07:00
BAS_SLOTS = [
    (1, "09:30", "12:00"),
    (1, "15:30", "18:00"),
    (2, "09:30", "12:00"),
    (2, "13:00", "15:30"),
    (4, "09:30", "12:00"),
    (5, "13:00", "15:30"),
    (6, "07:00", "09:30"),
    (6, "13:00", "15:30"),
]

_HO = [
    "Nguyễn",
    "Trần",
    "Lê",
    "Phạm",
    "Hoàng",
    "Huỳnh",
    "Phan",
    "Vũ",
    "Võ",
    "Đặng",
    "Bùi",
    "Đỗ",
    "Hồ",
    "Ngô",
    "Dương",
    "Lý",
]
_DEM = [
    "Văn",
    "Thị",
    "Minh",
    "Quốc",
    "Hữu",
    "Ngọc",
    "Anh",
    "Thanh",
    "Đức",
    "Hoài",
    "Gia",
    "Khánh",
]
_TEN = [
    "An",
    "Bình",
    "Châu",
    "Dũng",
    "Giang",
    "Hà",
    "Hải",
    "Hiếu",
    "Hoa",
    "Hùng",
    "Khoa",
    "Lan",
    "Linh",
    "Long",
    "Mai",
    "Nam",
    "Phúc",
    "Quân",
    "Sơn",
    "Thảo",
    "Trang",
    "Tuấn",
    "Vy",
    "Yến",
]
_PROGRAMS = [
    "Công nghệ thông tin",
    "Khoa học máy tính",
    "Kỹ thuật phần mềm",
    "An toàn thông tin",
    "Hệ thống thông tin",
]
_INSTRUCTORS = [
    f"{h} {d} {t}"
    for h, d, t in zip(_HO * 2, (_DEM * 3)[:32], (_TEN * 2)[:32], strict=False)
]
_TOPICS = {
    "ELE": [
        "Mạch điện",
        "Điện tử số",
        "Vi xử lý",
        "Xử lý tín hiệu",
        "Hệ thống nhúng",
        "Đo lường",
    ],
    "PHY": ["Vật lý đại cương", "Quang học", "Cơ học", "Nhiệt học", "Điện từ học"],
    "ENG": [
        "Tiếng Anh chuyên ngành",
        "Kỹ năng nghe nói",
        "Viết học thuật",
        "Giao tiếp quốc tế",
    ],
    "MAN": [
        "Quản lý dự án",
        "Khởi nghiệp",
        "Kinh tế học",
        "Marketing số",
        "Quản trị chất lượng",
    ],
    "MAT": ["Xác suất", "Thống kê", "Toán rời rạc", "Giải tích số", "Tối ưu hóa"],
    "INT": [
        "Mạng máy tính",
        "Hệ điều hành",
        "Lập trình web",
        "Trí tuệ nhân tạo",
        "An toàn thông tin",
        "Kỹ thuật phần mềm",
        "Điện toán đám mây",
        "Xử lý ảnh",
        "Dữ liệu lớn",
        "Lập trình di động",
    ],
}
_LEVEL_LABEL = {
    1: "cơ bản",
    2: "căn bản",
    3: "nâng cao",
    4: "ứng dụng",
    5: "chuyên sâu",
    6: "chuyên đề",
    7: "tổng hợp",
}
_LEVEL_COUNTS = {1: 30, 2: 35, 3: 35, 4: 30, 5: 25, 6: 15, 7: 10}  # tổng 180
_TERMS = [
    "2022-1",
    "2022-2",
    "2023-1",
    "2023-2",
    "2024-1",
    "2024-2",
    "2025-1",
    "2025-2",
]


# --------------------------------------------------------------------------- tiện ích nhỏ


def _full_name(rng: random.Random) -> str:
    return f"{rng.choice(_HO)} {rng.choice(_DEM)} {rng.choice(_TEN)}"


def _sched(sessions: list[tuple[int, str, str]]) -> list[dict]:
    return [{"day": d, "start": s, "end": e} for d, s, e in sessions]


def _to_min(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _requirements(ds_prereqs: list[PrereqRow]) -> tuple[dict, dict]:
    """Trả (and_map, or_map): and_map[course] = [mã...]; or_map[course][group_no] = [mã...]."""
    and_map: dict[str, list[str]] = {}
    or_map: dict[str, dict[int, list[str]]] = {}
    for p in ds_prereqs:
        if p.type == "AND":
            and_map.setdefault(p.course_code, []).append(p.prereq_code)
        else:
            or_map.setdefault(p.course_code, {}).setdefault(p.group_no, []).append(
                p.prereq_code
            )
    return and_map, or_map


def satisfies(code: str, completed: set[str], and_map: dict, or_map: dict) -> bool:
    """Đạt tiên quyết trực tiếp của `code`: mọi môn AND đã học, mỗi nhóm OR có ít nhất một môn đã học."""
    if any(p not in completed for p in and_map.get(code, [])):
        return False
    return all(
        any(o in completed for o in opts) for opts in or_map.get(code, {}).values()
    )


# --------------------------------------------------------------------------- dựng dữ liệu


def _add_kit_courses(ds: Dataset) -> None:
    for code, name, level, and_list, or_groups in KIT_COURSES:
        ds.courses.append(
            CourseRow(
                code,
                name,
                3,
                level,
                min_accumulated_credits=_MIN_CREDITS_BY_LEVEL[level],
            )
        )
        for p in and_list:
            ds.prereqs.append(PrereqRow(code, p, "AND", 0))
        for g, opts in enumerate(or_groups, start=1):
            for o in opts:
                ds.prereqs.append(PrereqRow(code, o, "OR", g))


def _add_bas_courses(ds: Dataset) -> None:
    for i in range(1, 9):
        ds.courses.append(
            CourseRow(
                f"BAS{100 + i}",
                f"Kỹ năng bổ trợ {i}",
                3,
                1,
                min_accumulated_credits=0,
            )
        )


def _add_generated_courses(ds: Dataset, rng: random.Random) -> None:
    """180 học phần sinh theo tầng; cạnh tiên quyết chỉ đi từ tầng cao xuống tầng thấp => luôn không có vòng."""
    used = {c.code for c in ds.courses}
    by_level: dict[int, list[str]] = {}
    for c in ds.courses:
        if not c.code.startswith("BAS"):  # học phần đệm không làm tiên quyết
            by_level.setdefault(c.level, []).append(c.code)
    counters: dict[tuple[str, int], int] = {}
    prefixes = list(_TOPICS)

    for level in range(1, 8):
        for _ in range(_LEVEL_COUNTS[level]):
            prefix = rng.choice(prefixes)
            n = counters.get((prefix, level), 0)
            while True:
                n += 1
                code = f"{prefix}{level}{n:02d}"
                if code not in used:
                    break
            counters[(prefix, level)] = n
            used.add(code)
            name = f"{rng.choice(_TOPICS[prefix])} {_LEVEL_LABEL[level]}"
            ds.courses.append(
                CourseRow(
                    code,
                    name,
                    rng.choice([2, 3, 3, 3, 4]),
                    level,
                    min_accumulated_credits=_MIN_CREDITS_BY_LEVEL[level],
                )
            )

            if level >= 2:
                course_faculty = PREFIX_TO_FACULTY.get(prefix)
                prev_candidates = [
                    c
                    for c in by_level[level - 1]
                    if course_allowed_for_faculty(c, course_faculty)
                ] or by_level[level - 1]
                chosen: set[str] = {
                    rng.choice(prev_candidates)
                }  # đảm bảo có chuỗi sâu đủ 7 tầng và khép kín trong khoa
                lower = [
                    c
                    for lv in range(1, level)
                    for c in by_level.get(lv, [])
                    if course_allowed_for_faculty(c, course_faculty)
                ]
                if level >= 3 and lower and rng.random() < 0.45:
                    chosen.add(rng.choice(lower))
                for p in sorted(chosen):
                    ds.prereqs.append(PrereqRow(code, p, "AND", 0))
                groups = 0
                for prob in (0.35, 0.10):
                    pool = [c for c in lower if c not in chosen]
                    if len(pool) >= 2 and rng.random() < prob:
                        opts = rng.sample(pool, 2)
                        groups += 1
                        chosen.update(opts)
                        for o in sorted(opts):
                            ds.prereqs.append(PrereqRow(code, o, "OR", groups))
            by_level.setdefault(level, []).append(code)


def _is_special_shift5_course(code: str) -> bool:
    """Ca 5 (18:05–20:35) chỉ dành cho các môn đặc biệt: kỹ năng (BAS), ngoại ngữ (ENG) hoặc chuyên đề năm cuối."""
    return code.startswith(("BAS", "ENG")) or code in ("INT451",)


def _random_schedule(rng: random.Random, *, allow_shift5: bool = False) -> list[dict]:
    """1 môn học = 1 ca/tuần, tập trung 4 ca đầu (Ca 1–Ca 4); Ca 5 chỉ cho môn đặc biệt."""
    day = rng.randint(1, 6)  # Thứ Hai - Thứ Bảy
    if allow_shift5 and rng.random() < 0.25:
        slot = SHIFT_5
    else:
        slot = rng.choice(MAIN_SHIFTS)
    return _sched([(day, slot[0], slot[1])])


def _add_offerings(
    ds: Dataset,
    rng: random.Random,
    include_generated: bool,
    *,
    loadtest: bool = False,
) -> None:
    for code, sessions, cap in KIT_OFFERINGS:
        ds.offerings.append(
            OfferingRow(
                code,
                "01",
                rng.choice(_INSTRUCTORS),
                cap,
                _sched(sessions),
                f"A{rng.randint(1, 5)}-{rng.randint(101, 512)}",
            )
        )
    for i, slot in enumerate(BAS_SLOTS, start=1):
        ds.offerings.append(
            OfferingRow(
                f"BAS{100 + i}",
                "01",
                rng.choice(_INSTRUCTORS),
                5 if loadtest and i <= 5 else 60,
                _sched([slot]),
                f"B{rng.randint(1, 3)}-{rng.randint(101, 512)}",
            )
        )
    if include_generated:
        special = {c for c, _, _ in KIT_OFFERINGS} | {
            f"BAS{100 + i}" for i in range(1, 9)
        }
        for c in ds.courses:
            if c.code in special:
                continue
            for s in range(1, rng.choice([1, 2, 3]) + 1):
                ds.offerings.append(
                    OfferingRow(
                        c.code,
                        f"{s:02d}",
                        rng.choice(_INSTRUCTORS),
                        rng.choice([30, 40, 50, 60]),
                        _random_schedule(rng),
                        f"{rng.choice(['A1', 'A2', 'B1', 'B2', 'C1'])}-{rng.randint(101, 512)}",
                    )
                )


def _kit_enrollments(ds: Dataset) -> None:
    """Đăng ký và hàng chờ sẵn của kit: sv0004 (8 lớp BAS), sv0005, 15 người INT331-01, 29 người INT231-01."""

    def e(n: int) -> str:
        return f"sv{n:04d}@{EMAIL_DOMAIN}"

    plan = (
        [(e(4), (f"BAS{100 + i}", "01")) for i in range(1, 9)]
        + [(e(5), ("INT221", "01"))]
        + [(e(n), ("INT331", "01")) for n in range(11, 26)]  # lấp đầy lớp INT331-01
        + [(e(n), ("INT231", "01")) for n in range(26, 55)]  # 29 người trong INT231-01
    )
    for t, (email, key) in enumerate(plan):
        ds.enrollments.append(
            EnrollmentRow(email, key, _BASE_ENROLL + timedelta(seconds=t))
        )
    for pos, n in enumerate((6, 7, 8), start=1):  # hàng chờ INT331-01
        ds.waitlist.append(
            WaitlistRow(
                e(n), ("INT331", "01"), pos, _BASE_WAIT + timedelta(seconds=pos)
            )
        )


def _kit_students(ds: Dataset, default_max: int) -> None:
    """sv0001 ... sv0054: mỗi tài khoản phục vụ một tình huống (README mục 'Kit')."""
    rng = random.Random(f"{SEED}-kit")
    c12 = ["INT101", "INT131"]
    c123 = ["INT101", "INT131", "INT231"]
    c1234 = ["INT101", "INT131", "INT231", "MAT201"]
    completed = {
        1: c1234,
        2: ["INT101"],
        3: c123,
        4: c12,
        5: c12,
        **{n: c123 for n in (6, 7, 8)},
        9: c1234,
        10: c1234,
        **{n: c123 for n in range(11, 26)},
        **{n: c12 for n in range(26, 55)},
    }
    # 1 đủ điều kiện INT341 | 2 thiếu bắc cầu INT431 | 3 thiếu nhóm OR | 4 đủ 24 tín chỉ | 5 trùng lịch
    # 6-8 hàng chờ INT331-01 | 9-10 tranh suất INT341-01 | 11-25 lấp đầy INT331-01 | 26-54 trong INT231-01
    for n, courses in completed.items():
        email = f"sv{n:04d}@{EMAIL_DOMAIN}"
        ds.students.append(
            StudentRow(
                email,
                f"SV{n:04d}",
                _full_name(rng),
                "student",
                "Công nghệ thông tin",
                default_max,
                faculty=FACULTY_CNTT,
            )
        )
        for code in courses:
            ds.completed.append(
                CompletedRow(
                    email, code, 8.0, _TERMS[min(ds.course(code).level - 1, 7)]
                )
            )
    _kit_enrollments(ds)


def _generated_students(
    ds: Dataset, rng: random.Random, default_max: int, total: int
) -> None:
    """sv0055 ... sv{total}: sinh viên năm 1-4 với tập môn đã học 'đóng' theo tiên quyết."""
    and_map, or_map = _requirements(ds.prereqs)
    ordered = sorted(ds.courses, key=lambda c: (c.level, c.code))
    for n in range(55, total + 1):
        email = f"sv{n:04d}@{EMAIL_DOMAIN}"
        if n in (55, 587):
            faculty = FACULTY_CNTT
            program = "Công nghệ thông tin"
        else:
            roll = rng.random()
            if roll < 0.70:
                faculty = FACULTY_CNTT
                program = rng.choice(_PROGRAMS)
            elif roll < 0.85:
                faculty = FACULTY_DIEN
                program = "Kỹ thuật điện - điện tử"
            else:
                faculty = FACULTY_QTKD
                program = "Quản trị kinh doanh"
        ds.students.append(
            StudentRow(
                email,
                f"SV{n:04d}",
                _full_name(rng),
                "student",
                program,
                default_max,
                faculty=faculty,
            )
        )
        if n == 55:
            # sv0055: tân sinh viên năm nhất Khoa CNTT (0 tín chỉ tích lũy) dùng cho kịch bản demo
            continue
        year = 3 if n == 587 else rng.choice([1, 1, 2, 2, 3, 3, 4])
        reach = 1.5 * year
        done: set[str] = set()
        acc_credits = 0
        if n == 587:
            # sv0587: sinh viên năm 3 Khoa CNTT chuẩn (~50-58 TC) dùng cho kịch bản demo
            for c in ordered:
                if not course_allowed_for_faculty(c.code, faculty):
                    continue
                if c.code in ("INT101", "MAT201", "MAT202") or (
                    acc_credits < 48
                    and c.level <= 2
                    and c.code not in ("INT131", "BAS101", "BAS102")
                    and acc_credits >= c.min_accumulated_credits
                    and satisfies(c.code, done, and_map, or_map)
                ):
                    done.add(c.code)
                    acc_credits += c.credits
                    ds.completed.append(
                        CompletedRow(
                            email,
                            c.code,
                            round(rng.uniform(7.0, 9.5), 1),
                            _TERMS[min(c.level - 1 + rng.randint(0, 1), 4)],
                        )
                    )
            continue
        for c in ordered:  # theo tầng tăng dần => tiên quyết luôn được xét trước
            if not course_allowed_for_faculty(c.code, faculty):
                continue
            if c.level <= reach - 1:
                p = 0.30
            elif c.level <= reach:
                p = 0.18
            elif c.level <= reach + 1:
                p = 0.06
            else:
                continue
            if (
                acc_credits >= c.min_accumulated_credits
                and satisfies(c.code, done, and_map, or_map)
                and rng.random() < p
            ):
                done.add(c.code)
                acc_credits += c.credits
                grade = round(rng.uniform(5.0, 10.0), 1)
                ds.completed.append(
                    CompletedRow(
                        email,
                        c.code,
                        grade,
                        _TERMS[min(c.level - 1 + rng.randint(0, 1), 7)],
                    )
                )


def _add_study_plans_and_openings(
    ds: Dataset,
    rng: random.Random,
    *,
    term: str = STUDY_PLAN_TERM,
    min_required: int = MIN_PLAN_STUDENTS_TO_OPEN,
) -> None:
    """Sinh kế hoạch học tập (ĐKKHHT) kỳ sau cho từng sinh viên và chốt mở lớp theo ngưỡng."""
    and_map, or_map = _requirements(ds.prereqs)
    completed_by_email: dict[str, set[str]] = {}
    for comp in ds.completed:
        completed_by_email.setdefault(comp.student_email, set()).add(comp.course_code)

    # Bảo vệ toàn bộ môn có trong KIT_OFFERINGS hoặc đã có enrollment/waitlist không bị loại
    protected_codes = {code for code, _, _ in KIT_OFFERINGS} | {
        f"BAS{100 + i}" for i in range(1, 9)
    }
    protected_codes |= {e.offering_key[0] for e in ds.enrollments}
    protected_codes |= {w.offering_key[0] for w in ds.waitlist}

    # Chọn ~10 môn tự chọn/chuyên đề không thuộc bộ cốt lõi để mô phỏng trường hợp
    # thiếu sinh viên ĐKKHHT (< min_required -> NOT_OPENED, không mở lớp)
    sv587_student = next(
        (s for s in ds.students if s.email == "sv0587@uni.edu.vn"), None
    )
    sv587_faculty = sv587_student.faculty if sv587_student else FACULTY_CNTT
    sv587_acc = sv587_student.accumulated_credits if sv587_student else 0
    sv587_done = completed_by_email.get("sv0587@uni.edu.vn", set())
    candidate_low = [
        c.code
        for c in ds.courses
        if c.code not in protected_codes
        and c.min_accumulated_credits <= 24
        and c.code.startswith(("INT", "MAT", "ELE", "MAN"))
    ]
    sv587_low_candidates = [
        c.code
        for c in ds.courses
        if c.code in candidate_low
        and course_allowed_for_faculty(c.code, sv587_faculty)
        and sv587_acc >= c.min_accumulated_credits
        and c.code not in sv587_done
        and satisfies(c.code, sv587_done, and_map, or_map)
    ]
    low_demand_caps: dict[str, int] = {}
    low_demand_int = (
        sv587_low_candidates[:2]
        + [
            c
            for c in candidate_low
            if c.startswith("INT") and c not in sv587_low_candidates[:2]
        ][-4:]
    )
    low_demand_other = [c for c in candidate_low if not c.startswith("INT")][-4:]
    for idx, code in enumerate(low_demand_int + low_demand_other):
        low_demand_caps[code] = 4 + (idx % 7)  # 4..10 sinh viên (< 15 -> NOT_OPENED)

    demand_count: dict[str, int] = {c.code: 0 for c in ds.courses}
    planned_pairs: set[tuple[str, str]] = set()

    # Ưu tiên duyệt sinh viên demo trước để đảm bảo họ có cả môn OPENED lẫn 1 môn NOT_OPENED
    demo_priority = {
        "sv0587@uni.edu.vn": 0,
        "sv0001@uni.edu.vn": 1,
        "sv0055@uni.edu.vn": 2,
    }
    students = [s for s in ds.students if s.role == "student"]
    students.sort(key=lambda s: (demo_priority.get(s.email, 9), s.email))

    for student in students:
        done = completed_by_email.get(student.email, set())
        eligible = [
            c
            for c in ds.courses
            if c.code not in done
            and course_allowed_for_faculty(c.code, student.faculty)
            and student.accumulated_credits >= c.min_accumulated_credits
            and satisfies(c.code, done, and_map, or_map)
        ]
        if not eligible:
            continue

        target_n = rng.randint(4, 6)
        chosen: list[CourseRow] = []
        used_credits = 0

        # Đảm bảo tài khoản demo CNTT có sẵn 1 môn NOT_OPENED hợp lệ trong KHHT để trình diễn
        if student.email in ("sv0587@uni.edu.vn", "sv0001@uni.edu.vn"):
            low_elig = [
                c
                for c in eligible
                if c.code in low_demand_caps
                and demand_count[c.code] < low_demand_caps[c.code]
            ]
            if low_elig:
                pick = low_elig[0]
                chosen.append(pick)
                used_credits += pick.credits

        # Ưu tiên chọn các môn đúng tiến độ (min_accumulated_credits cao trước) + KIT
        pool = [c for c in eligible if c not in chosen]
        rng.shuffle(pool)
        pool.sort(
            key=lambda c: (
                0
                if c.code in protected_codes and demand_count[c.code] < min_required
                else 1,
                -c.min_accumulated_credits,
            )
        )
        for c in pool:
            if len(chosen) >= target_n:
                break
            if used_credits + c.credits > student.max_credits:
                continue
            cap = low_demand_caps.get(c.code)
            if cap is not None and demand_count[c.code] >= cap:
                continue
            chosen.append(c)
            used_credits += c.credits

        for c in chosen:
            if (student.email, c.code) not in planned_pairs:
                planned_pairs.add((student.email, c.code))
                ds.study_plans.append(StudyPlanRow(student.email, c.code, term))
                demand_count[c.code] += 1

    # Chốt trạng thái mở lớp theo ngưỡng min_required
    decided_at = datetime(2026, 11, 20, 9, 0, tzinfo=UTC)
    opened_codes: set[str] = set()
    for c in ds.courses:
        cnt = demand_count[c.code]
        if c.code in low_demand_caps:
            status = "NOT_OPENED"
        elif cnt >= min_required or c.code in protected_codes:
            status = "OPENED"
            opened_codes.add(c.code)
        else:
            status = "NOT_OPENED"
        ds.course_openings.append(
            TermCourseOpeningRow(
                term=term,
                course_code=c.code,
                planned_count=cnt,
                min_required=min_required,
                status=status,
                decided_at=decided_at,
            )
        )

    def _snap_to_tdtu_shift(schedule: list[dict]) -> list[dict]:
        """Chuẩn hóa lịch 1 môn = 1 ca theo khung giờ chuẩn TDTU (Ca 1–Ca 5)."""
        first = schedule[0]
        day = first["day"]
        start_min = _to_min(first["start"])
        if start_min < 9 * 60 + 25:
            slot = MAIN_SHIFTS[0]  # Ca 1: 06:50–09:20
        elif start_min < 12 * 60 + 15:
            slot = MAIN_SHIFTS[1]  # Ca 2: 09:30–12:00
        elif start_min < 15 * 60 + 20:
            slot = MAIN_SHIFTS[2]  # Ca 3: 12:45–15:15
        elif start_min < 18 * 60:
            slot = MAIN_SHIFTS[3]  # Ca 4: 15:25–17:55
        else:
            slot = SHIFT_5  # Ca 5: 18:05–20:35
        return [{"day": day, "start": slot[0], "end": slot[1]}]

    filtered_offerings = [
        OfferingRow(
            course_code=o.course_code,
            section=o.section,
            instructor=o.instructor,
            capacity=o.capacity,
            schedule=_snap_to_tdtu_shift(o.schedule),
            room=o.room,
            enrolled_count=o.enrolled_count,
            term=term,
        )
        for o in ds.offerings
        if o.course_code in opened_codes
    ]

    # Tự động mở bổ sung nhiều lớp (02, 03, ...) căn cứ vào số SV ĐKKHHT của từng môn (40 SV/lớp)
    default_cap = 40
    existing_sections: dict[str, set[str]] = {}
    for o in filtered_offerings:
        existing_sections.setdefault(o.course_code, set()).add(o.section)

    extra_offerings: list[OfferingRow] = []
    for c in ds.courses:
        if c.code not in opened_codes:
            continue
        planned = demand_count[c.code]
        needed = max(1, math.ceil(planned / default_cap))
        used_secs = existing_sections.setdefault(c.code, set())
        sec_num = 1
        while len(used_secs) < needed:
            sec_label = f"{sec_num:02d}"
            sec_num += 1
            if sec_label in used_secs:
                continue
            used_secs.add(sec_label)
            extra_offerings.append(
                OfferingRow(
                    course_code=c.code,
                    section=sec_label,
                    instructor=rng.choice(_INSTRUCTORS),
                    capacity=default_cap,
                    schedule=_random_schedule(
                        rng, allow_shift5=_is_special_shift5_course(c.code)
                    ),
                    room=f"B{rng.randint(1, 3)}-{rng.randint(101, 512)}",
                    enrolled_count=0,
                    term=term,
                )
            )

    ds.offerings = filtered_offerings + extra_offerings


LOADTEST_STUDENT_COUNT = 2000


def build_dataset(
    profile: str = "default", *, default_max_credits: int = 25
) -> Dataset:
    """profile: 'minimal' (chỉ kit, dùng cho test), 'default' (200 học phần, 1000 sinh viên), hoặc 'loadtest' (2000 sinh viên cho spike test)."""
    if profile not in ("minimal", "default", "loadtest"):
        raise ValueError(f"profile không hợp lệ: {profile}")
    rng = random.Random(f"{SEED}-{profile}")
    ds = Dataset(profile=profile)

    _add_kit_courses(ds)
    _add_bas_courses(ds)
    if profile != "minimal":
        _add_generated_courses(ds, rng)
    _add_offerings(
        ds,
        rng,
        include_generated=profile != "minimal",
        loadtest=profile == "loadtest",
    )
    _kit_students(ds, default_max_credits)
    if profile != "minimal":
        student_count = (
            LOADTEST_STUDENT_COUNT if profile == "loadtest" else DEFAULT_STUDENT_COUNT
        )
        _generated_students(ds, rng, default_max_credits, student_count)

    # Admin đặt CUỐI để sv000N có id = N khi nạp theo thứ tự
    ds.students.append(
        StudentRow(
            ADMIN_EMAIL, None, "Quản trị hệ thống", "admin", None, default_max_credits
        )
    )

    # Đồng bộ accumulated_credits cho mọi sinh viên bằng đúng tổng tín chỉ các môn đã đạt
    credits_by_code = {c.code: c.credits for c in ds.courses}
    acc_by_email: dict[str, int] = {}
    for comp in ds.completed:
        acc_by_email[comp.student_email] = acc_by_email.get(
            comp.student_email, 0
        ) + credits_by_code.get(comp.course_code, 0)
    for s in ds.students:
        s.accumulated_credits = acc_by_email.get(s.email, 0)

    # Sinh kế hoạch học tập kỳ 2026-2 & quyết định mở lớp cho profile 'default'
    if profile == "default":
        _add_study_plans_and_openings(ds, rng)

    # enrolled_count luôn đúng bằng số đăng ký ACTIVE
    counts: dict[tuple[str, str], int] = {}
    for e in ds.enrollments:
        if e.status == "ACTIVE":
            counts[e.offering_key] = counts.get(e.offering_key, 0) + 1
    for o in ds.offerings:
        o.enrolled_count = counts.get(o.key, 0)
    return ds


# --------------------------------------------------------------------------- kiểm tra nhất quán


def find_cycle(edges: list[tuple[str, str]]) -> list[str] | None:
    """Tìm một chu trình trong đồ thị 'course -> prereq' (DFS lặp, không đệ quy sâu). None nếu là DAG."""
    graph: dict[str, list[str]] = {}
    for a, b in edges:
        graph.setdefault(a, []).append(b)
        graph.setdefault(b, [])
    color = {n: 0 for n in graph}  # 0 chưa thăm, 1 đang thăm, 2 xong
    for start in graph:
        if color[start]:
            continue
        stack = [(start, iter(graph[start]))]
        path = [start]
        color[start] = 1
        while stack:
            node, it = stack[-1]
            nxt = next(it, None)
            if nxt is None:
                color[node] = 2
                stack.pop()
                path.pop()
            elif color[nxt] == 1:
                return path[path.index(nxt) :] + [nxt]
            elif color[nxt] == 0:
                color[nxt] = 1
                stack.append((nxt, iter(graph[nxt])))
                path.append(nxt)
    return None


def _check_prereqs(ds: Dataset, code_set: set[str]) -> list[str]:
    errs: list[str] = []
    seen = set()
    for p in ds.prereqs:
        if p.course_code not in code_set or p.prereq_code not in code_set:
            errs.append(f"Tiên quyết tham chiếu môn không tồn tại: {p}")
        if p.course_code == p.prereq_code:
            errs.append(f"Tự trỏ vào chính nó: {p}")
        if (
            (p.type == "AND") != (p.group_no == 0)
            or p.type not in ("AND", "OR")
            or p.group_no < 0
        ):
            errs.append(f"type/group_no sai: {p}")
        if (p.course_code, p.prereq_code) in seen:
            errs.append(f"Trùng cạnh: {p}")
        seen.add((p.course_code, p.prereq_code))
    cyc = find_cycle([(p.course_code, p.prereq_code) for p in ds.prereqs])
    if cyc:
        errs.append(f"Có vòng lặp tiên quyết: {' -> '.join(cyc)}")
    return errs


def _check_offering_schedule(o: OfferingRow) -> list[str]:
    errs: list[str] = []
    if not o.schedule:
        errs.append(f"Lớp không có lịch: {o.key}")
    spans: list[tuple[int, int, int]] = []
    for s in o.schedule:
        a, b = _to_min(s["start"]), _to_min(s["end"])
        if not (1 <= s["day"] <= 7 and (6 * 60 + 50) <= a < b <= 21 * 60):
            errs.append(f"Lịch ngoài khung 06:50-21:00 hoặc sai ngày: {o.key} {s}")
        if any(d2 == s["day"] and a < b2 and a2 < b for d2, a2, b2 in spans):
            errs.append(f"Các buổi của một lớp chồng nhau: {o.key}")
        spans.append((s["day"], a, b))
    return errs


def _check_offerings(ds: Dataset, code_set: set[str]) -> list[str]:
    errs: list[str] = []
    keys = [o.key for o in ds.offerings]
    if len(keys) != len(set(keys)):
        errs.append("Lớp (mã môn, section) bị trùng")
    for o in ds.offerings:
        if o.course_code not in code_set:
            errs.append(f"Lớp của môn không tồn tại: {o.key}")
        if o.capacity <= 0 or not (0 <= o.enrolled_count <= o.capacity):
            errs.append(f"Sĩ số sai (I1): {o.key} {o.enrolled_count}/{o.capacity}")
        errs += _check_offering_schedule(o)
    return errs


def _check_students(ds: Dataset) -> list[str]:
    errs: list[str] = []
    emails = [s.email for s in ds.students]
    if len(emails) != len(set(emails)):
        errs.append("Email bị trùng")
    mssvs = [s.mssv for s in ds.students if s.mssv]
    if len(mssvs) != len(set(mssvs)):
        errs.append("MSSV bị trùng")
    for s in ds.students:
        if s.role not in ("student", "admin") or (s.role == "student" and not s.mssv):
            errs.append(f"Vai trò/MSSV sai: {s.email}")
        if not 1 <= s.max_credits <= 40:
            errs.append(f"max_credits sai: {s.email}")
    return errs


def _check_completed(
    ds: Dataset, code_set: set[str], and_map: dict, or_map: dict
) -> tuple[dict[str, set[str]], list[str]]:
    """Trả (tập môn đã học của từng sinh viên, lỗi). Tập đã học phải 'đóng' theo tiên quyết."""
    errs: list[str] = []
    emails = {s.email for s in ds.students}
    done: dict[str, set[str]] = {}
    pairs = set()
    for r in ds.completed:
        if r.student_email not in emails or r.course_code not in code_set:
            errs.append(f"completed tham chiếu không tồn tại: {r}")
            continue
        if (r.student_email, r.course_code) in pairs:
            errs.append(f"completed bị trùng: {r}")
        pairs.add((r.student_email, r.course_code))
        if not 0 <= r.grade <= 10:
            errs.append(f"Điểm ngoài 0-10: {r}")
        done.setdefault(r.student_email, set()).add(r.course_code)
    for email, got in done.items():
        for code in got:
            if not satisfies(code, got, and_map, or_map):
                errs.append(
                    f"{email} đã học {code} nhưng thiếu tiên quyết của nó (không đóng theo DAG)"
                )
    return done, errs


def _schedules_overlap(a: OfferingRow, b: OfferingRow) -> bool:
    return any(
        s1["day"] == s2["day"]
        and _to_min(s1["start"]) < _to_min(s2["end"])
        and _to_min(s2["start"]) < _to_min(s1["end"])
        for s1 in a.schedule
        for s2 in b.schedule
    )


def _check_student_load(
    ds: Dataset, email: str, offs: list[OfferingRow], credits: dict[str, int]
) -> list[str]:
    errs: list[str] = []
    max_credits = next(s.max_credits for s in ds.students if s.email == email)
    if sum(credits[o.course_code] for o in offs) > max_credits:
        errs.append(f"{email} vượt tín chỉ (I4)")
    if len({o.course_code for o in offs}) != len(offs):
        errs.append(f"{email} có hai lớp cùng một môn (I10)")
    for i, a in enumerate(offs):
        errs += [
            f"{email} trùng lịch {a.key} và {b.key} (I5)"
            for b in offs[i + 1 :]
            if _schedules_overlap(a, b)
        ]
    return errs


def _check_enrollments(
    ds: Dataset, done: dict[str, set[str]], and_map: dict, or_map: dict
) -> tuple[set, list[str]]:
    """Trả (tập (email, lớp) đang ACTIVE, lỗi): I2, I3, I4, I5, I9, I10."""
    errs: list[str] = []
    omap = {o.key: o for o in ds.offerings}
    emails = {s.email for s in ds.students}
    credits = {c.code: c.credits for c in ds.courses}
    active: dict[str, list[OfferingRow]] = {}
    actual: dict[tuple[str, str], int] = {}
    seen: set = set()
    for e in ds.enrollments:
        if e.student_email not in emails or e.offering_key not in omap:
            errs.append(f"enrollment tham chiếu không tồn tại: {e}")
            continue
        if (e.student_email, e.offering_key) in seen:
            errs.append(f"Trùng đăng ký ACTIVE (I3): {e}")
        seen.add((e.student_email, e.offering_key))
        off = omap[e.offering_key]
        active.setdefault(e.student_email, []).append(off)
        actual[e.offering_key] = actual.get(e.offering_key, 0) + 1
        if not satisfies(
            off.course_code, done.get(e.student_email, set()), and_map, or_map
        ):
            errs.append(
                f"{e.student_email} đăng ký {off.key} nhưng chưa đủ tiên quyết (I9)"
            )
    for email, offs in active.items():
        errs += _check_student_load(ds, email, offs, credits)
    for o in ds.offerings:  # I2: enrolled_count phải đúng bằng số đăng ký ACTIVE
        if o.enrolled_count != actual.get(o.key, 0):
            errs.append(
                f"enrolled_count lệch số đăng ký ACTIVE (I2): {o.key} {o.enrolled_count} != {actual.get(o.key, 0)}"
            )
    return seen, errs


def _check_waitlist(ds: Dataset, active_pairs: set, waitlist_ratio: float) -> list[str]:
    errs: list[str] = []
    omap = {o.key: o for o in ds.offerings}
    emails = {s.email for s in ds.students}
    per: dict[tuple[str, str], list[WaitlistRow]] = {}
    for w in ds.waitlist:
        if w.student_email not in emails or w.offering_key not in omap:
            errs.append(f"waitlist tham chiếu không tồn tại: {w}")
            continue
        per.setdefault(w.offering_key, []).append(w)
        if (w.student_email, w.offering_key) in active_pairs:
            errs.append(f"Vừa ACTIVE vừa chờ cùng một lớp (I7): {w}")
    for key, rows in per.items():
        rows.sort(key=lambda r: r.enqueued_at)
        if [r.position for r in rows] != list(range(1, len(rows) + 1)):
            errs.append(f"position hàng chờ không liên tục (I6): {key}")
        if len(rows) > math.ceil(omap[key].capacity * waitlist_ratio):
            errs.append(f"Hàng chờ vượt giới hạn (I8): {key}")
        if omap[key].enrolled_count < omap[key].capacity:
            errs.append(f"Lớp còn chỗ mà vẫn có hàng chờ: {key}")
    return errs


def validate_dataset(ds: Dataset, waitlist_ratio: float = 0.2) -> list[str]:
    """Trả danh sách lỗi (rỗng = hợp lệ). Kiểm các bất biến: không vượt sĩ số, enrolled_count đúng, không trùng đăng ký/lịch, không vượt tín chỉ, hàng chờ FIFO..."""
    codes = [c.code for c in ds.courses]
    errs: list[str] = ["Mã học phần bị trùng"] if len(codes) != len(set(codes)) else []
    code_set = set(codes)
    errs += _check_prereqs(ds, code_set)
    and_map, or_map = _requirements(ds.prereqs)
    errs += _check_offerings(ds, code_set)
    errs += _check_students(ds)
    done, e_completed = _check_completed(ds, code_set, and_map, or_map)
    active_pairs, e_enroll = _check_enrollments(ds, done, and_map, or_map)
    return (
        errs
        + e_completed
        + e_enroll
        + _check_waitlist(ds, active_pairs, waitlist_ratio)
    )
