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
from datetime import datetime, timedelta, timezone

TERM = "2026-1"
SEED = 20261
ADMIN_EMAIL = "admin@uni.edu.vn"
ADMIN_PASSWORD = "Admin@123"
STUDENT_PASSWORD = "Student@123"
EMAIL_DOMAIN = "uni.edu.vn"

DEFAULT_STUDENT_COUNT = 1000  # sv0001 ... sv1000
GENERATED_COURSE_COUNT = 180  # + 12 kit + 8 BAS = 200 học phần ở profile default

# Khung giờ chuẩn (đều nằm trong 07:00-21:00)
SLOTS = [("07:00", "09:30"), ("09:30", "12:00"), ("13:00", "15:30"), ("15:30", "18:00"), ("18:00", "20:30")]
_BASE_ENROLL = datetime(2026, 8, 1, tzinfo=timezone.utc)
_BASE_WAIT = datetime(2026, 8, 2, tzinfo=timezone.utc)

# --------------------------------------------------------------------------- kiểu dữ liệu


@dataclass
class CourseRow:
    code: str
    name: str
    credits: int
    level: int  # tầng trong DAG (chỉ để sinh dữ liệu; không lưu DB)
    description: str | None = None


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
class Dataset:
    profile: str
    courses: list[CourseRow] = field(default_factory=list)
    prereqs: list[PrereqRow] = field(default_factory=list)
    offerings: list[OfferingRow] = field(default_factory=list)
    students: list[StudentRow] = field(default_factory=list)
    completed: list[CompletedRow] = field(default_factory=list)
    enrollments: list[EnrollmentRow] = field(default_factory=list)
    waitlist: list[WaitlistRow] = field(default_factory=list)

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
    ("INT451", "Chuyên đề", 4, [], [["MAT201", "MAT202"], ["INT221", "INT222"]]),  # hai nhóm OR
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
    (1, "09:30", "12:00"), (1, "15:30", "18:00"), (2, "09:30", "12:00"), (2, "13:00", "15:30"),
    (4, "09:30", "12:00"), (5, "13:00", "15:30"), (6, "07:00", "09:30"), (6, "13:00", "15:30"),
]

_HO = ["Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Huỳnh", "Phan", "Vũ", "Võ", "Đặng", "Bùi", "Đỗ", "Hồ", "Ngô", "Dương", "Lý"]
_DEM = ["Văn", "Thị", "Minh", "Quốc", "Hữu", "Ngọc", "Anh", "Thanh", "Đức", "Hoài", "Gia", "Khánh"]
_TEN = ["An", "Bình", "Châu", "Dũng", "Giang", "Hà", "Hải", "Hiếu", "Hoa", "Hùng", "Khoa", "Lan", "Linh", "Long",
        "Mai", "Nam", "Phúc", "Quân", "Sơn", "Thảo", "Trang", "Tuấn", "Vy", "Yến"]
_PROGRAMS = ["Công nghệ thông tin", "Khoa học máy tính", "Kỹ thuật phần mềm", "An toàn thông tin", "Hệ thống thông tin"]
_INSTRUCTORS = [f"{h} {d} {t}" for h, d, t in zip(_HO * 2, (_DEM * 3)[:32], (_TEN * 2)[:32])]
_TOPICS = {
    "ELE": ["Mạch điện", "Điện tử số", "Vi xử lý", "Xử lý tín hiệu", "Hệ thống nhúng", "Đo lường"],
    "PHY": ["Vật lý đại cương", "Quang học", "Cơ học", "Nhiệt học", "Điện từ học"],
    "ENG": ["Tiếng Anh chuyên ngành", "Kỹ năng nghe nói", "Viết học thuật", "Giao tiếp quốc tế"],
    "MAN": ["Quản lý dự án", "Khởi nghiệp", "Kinh tế học", "Marketing số", "Quản trị chất lượng"],
    "MAT": ["Xác suất", "Thống kê", "Toán rời rạc", "Giải tích số", "Tối ưu hóa"],
    "INT": ["Mạng máy tính", "Hệ điều hành", "Lập trình web", "Trí tuệ nhân tạo", "An toàn thông tin",
            "Kỹ thuật phần mềm", "Điện toán đám mây", "Xử lý ảnh", "Dữ liệu lớn", "Lập trình di động"],
}
_LEVEL_LABEL = {1: "cơ bản", 2: "căn bản", 3: "nâng cao", 4: "ứng dụng", 5: "chuyên sâu", 6: "chuyên đề", 7: "tổng hợp"}
_LEVEL_COUNTS = {1: 30, 2: 35, 3: 35, 4: 30, 5: 25, 6: 15, 7: 10}  # tổng 180
_TERMS = ["2022-1", "2022-2", "2023-1", "2023-2", "2024-1", "2024-2", "2025-1", "2025-2"]


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
            or_map.setdefault(p.course_code, {}).setdefault(p.group_no, []).append(p.prereq_code)
    return and_map, or_map


def satisfies(code: str, completed: set[str], and_map: dict, or_map: dict) -> bool:
    """Đạt tiên quyết trực tiếp của `code`: mọi môn AND đã học, mỗi nhóm OR có ít nhất một môn đã học."""
    if any(p not in completed for p in and_map.get(code, [])):
        return False
    return all(any(o in completed for o in opts) for opts in or_map.get(code, {}).values())


# --------------------------------------------------------------------------- dựng dữ liệu


def _add_kit_courses(ds: Dataset) -> None:
    for code, name, level, and_list, or_groups in KIT_COURSES:
        ds.courses.append(CourseRow(code, name, 3, level))
        for p in and_list:
            ds.prereqs.append(PrereqRow(code, p, "AND", 0))
        for g, opts in enumerate(or_groups, start=1):
            for o in opts:
                ds.prereqs.append(PrereqRow(code, o, "OR", g))


def _add_bas_courses(ds: Dataset) -> None:
    for i in range(1, 9):
        ds.courses.append(CourseRow(f"BAS{100 + i}", f"Kỹ năng bổ trợ {i}", 3, 1))


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
            ds.courses.append(CourseRow(code, name, rng.choice([2, 3, 3, 3, 4]), level))

            if level >= 2:
                chosen: set[str] = {rng.choice(by_level[level - 1])}  # đảm bảo có chuỗi sâu đủ 7 tầng
                lower = [c for lv in range(1, level) for c in by_level.get(lv, [])]
                if level >= 3 and rng.random() < 0.45:
                    chosen.add(rng.choice(lower))
                for p in sorted(chosen):
                    ds.prereqs.append(PrereqRow(code, p, "AND", 0))
                groups = 0
                for prob in (0.35, 0.10):
                    if rng.random() < prob:
                        opts = rng.sample([c for c in lower if c not in chosen], 2)
                        groups += 1
                        chosen.update(opts)
                        for o in sorted(opts):
                            ds.prereqs.append(PrereqRow(code, o, "OR", groups))
            by_level.setdefault(level, []).append(code)


def _random_schedule(rng: random.Random) -> list[dict]:
    n = rng.choice([1, 1, 2])
    days = rng.sample(range(1, 7), n)  # Thứ Hai - Thứ Bảy
    slot = rng.choice(SLOTS)
    return _sched([(d, slot[0], slot[1]) for d in sorted(days)])


def _add_offerings(ds: Dataset, rng: random.Random, include_generated: bool) -> None:
    for code, sessions, cap in KIT_OFFERINGS:
        ds.offerings.append(
            OfferingRow(code, "01", rng.choice(_INSTRUCTORS), cap, _sched(sessions), f"A{rng.randint(1, 5)}-{rng.randint(101, 512)}")
        )
    for i, slot in enumerate(BAS_SLOTS, start=1):
        ds.offerings.append(OfferingRow(f"BAS{100 + i}", "01", rng.choice(_INSTRUCTORS), 60, _sched([slot]), f"B{rng.randint(1, 3)}-{rng.randint(101, 512)}"))
    if include_generated:
        special = {c for c, _, _ in KIT_OFFERINGS} | {f"BAS{100 + i}" for i in range(1, 9)}
        for c in ds.courses:
            if c.code in special:
                continue
            for s in range(1, rng.choice([1, 2, 3]) + 1):
                ds.offerings.append(
                    OfferingRow(c.code, f"{s:02d}", rng.choice(_INSTRUCTORS), rng.choice([30, 40, 50, 60]),
                                _random_schedule(rng), f"{rng.choice(['A1', 'A2', 'B1', 'B2', 'C1'])}-{rng.randint(101, 512)}")
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
        ds.enrollments.append(EnrollmentRow(email, key, _BASE_ENROLL + timedelta(seconds=t)))
    for pos, n in enumerate((6, 7, 8), start=1):  # hàng chờ INT331-01
        ds.waitlist.append(WaitlistRow(e(n), ("INT331", "01"), pos, _BASE_WAIT + timedelta(seconds=pos)))


def _kit_students(ds: Dataset, default_max: int) -> None:
    """sv0001 ... sv0054: mỗi tài khoản phục vụ một tình huống (README mục 'Kit')."""
    rng = random.Random(f"{SEED}-kit")
    c12 = ["INT101", "INT131"]
    c123 = ["INT101", "INT131", "INT231"]
    c1234 = ["INT101", "INT131", "INT231", "MAT201"]
    completed = {1: c1234, 2: ["INT101"], 3: c123, 4: c12, 5: c12, **{n: c123 for n in (6, 7, 8)},
                 9: c1234, 10: c1234, **{n: c123 for n in range(11, 26)}, **{n: c12 for n in range(26, 55)}}
    # 1 đủ điều kiện INT341 | 2 thiếu bắc cầu INT431 | 3 thiếu nhóm OR | 4 đủ 24 tín chỉ | 5 trùng lịch
    # 6-8 hàng chờ INT331-01 | 9-10 tranh suất INT341-01 | 11-25 lấp đầy INT331-01 | 26-54 trong INT231-01
    for n, courses in completed.items():
        email = f"sv{n:04d}@{EMAIL_DOMAIN}"
        ds.students.append(StudentRow(email, f"SV{n:04d}", _full_name(rng), "student", "Công nghệ thông tin", default_max))
        for code in courses:
            ds.completed.append(CompletedRow(email, code, 8.0, _TERMS[min(ds.course(code).level - 1, 7)]))
    _kit_enrollments(ds)


def _generated_students(ds: Dataset, rng: random.Random, default_max: int, total: int) -> None:
    """sv0055 ... sv{total}: sinh viên năm 1-4 với tập môn đã học 'đóng' theo tiên quyết."""
    and_map, or_map = _requirements(ds.prereqs)
    ordered = sorted(ds.courses, key=lambda c: (c.level, c.code))
    for n in range(55, total + 1):
        email = f"sv{n:04d}@{EMAIL_DOMAIN}"
        ds.students.append(StudentRow(email, f"SV{n:04d}", _full_name(rng), "student", rng.choice(_PROGRAMS), default_max))
        year = rng.choice([1, 1, 2, 2, 3, 3, 4])
        reach = 1.5 * year
        done: set[str] = set()
        for c in ordered:  # theo tầng tăng dần => tiên quyết luôn được xét trước
            if c.level <= reach - 1:
                p = 0.30
            elif c.level <= reach:
                p = 0.18
            elif c.level <= reach + 1:
                p = 0.06
            else:
                continue
            if satisfies(c.code, done, and_map, or_map) and rng.random() < p:
                done.add(c.code)
                grade = round(rng.uniform(5.0, 10.0), 1)
                ds.completed.append(CompletedRow(email, c.code, grade, _TERMS[min(c.level - 1 + rng.randint(0, 1), 7)]))


def build_dataset(profile: str = "default", *, default_max_credits: int = 25) -> Dataset:
    """profile: 'minimal' (chỉ kit, dùng cho test) hoặc 'default' (200 học phần, 1000 sinh viên)."""
    if profile not in ("minimal", "default"):
        raise ValueError(f"profile không hợp lệ: {profile}")
    rng = random.Random(f"{SEED}-{profile}")
    ds = Dataset(profile=profile)

    _add_kit_courses(ds)
    _add_bas_courses(ds)
    if profile != "minimal":
        _add_generated_courses(ds, rng)
    _add_offerings(ds, rng, include_generated=profile != "minimal")
    _kit_students(ds, default_max_credits)
    if profile != "minimal":
        _generated_students(ds, rng, default_max_credits, DEFAULT_STUDENT_COUNT)

    # Admin đặt CUỐI để sv000N có id = N khi nạp theo thứ tự
    ds.students.append(StudentRow(ADMIN_EMAIL, None, "Quản trị hệ thống", "admin", None, default_max_credits))

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
                return path[path.index(nxt):] + [nxt]
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
        if (p.type == "AND") != (p.group_no == 0) or p.type not in ("AND", "OR") or p.group_no < 0:
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
        if not (1 <= s["day"] <= 7 and 7 * 60 <= a < b <= 21 * 60):
            errs.append(f"Lịch ngoài khung 07:00-21:00 hoặc sai ngày: {o.key} {s}")
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


def _check_completed(ds: Dataset, code_set: set[str], and_map: dict, or_map: dict) -> tuple[dict[str, set[str]], list[str]]:
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
                errs.append(f"{email} đã học {code} nhưng thiếu tiên quyết của nó (không đóng theo DAG)")
    return done, errs


def _schedules_overlap(a: OfferingRow, b: OfferingRow) -> bool:
    return any(
        s1["day"] == s2["day"] and _to_min(s1["start"]) < _to_min(s2["end"]) and _to_min(s2["start"]) < _to_min(s1["end"])
        for s1 in a.schedule
        for s2 in b.schedule
    )


def _check_student_load(ds: Dataset, email: str, offs: list[OfferingRow], credits: dict[str, int]) -> list[str]:
    errs: list[str] = []
    max_credits = next(s.max_credits for s in ds.students if s.email == email)
    if sum(credits[o.course_code] for o in offs) > max_credits:
        errs.append(f"{email} vượt tín chỉ (I4)")
    if len({o.course_code for o in offs}) != len(offs):
        errs.append(f"{email} có hai lớp cùng một môn (I10)")
    for i, a in enumerate(offs):
        errs += [f"{email} trùng lịch {a.key} và {b.key} (I5)" for b in offs[i + 1:] if _schedules_overlap(a, b)]
    return errs


def _check_enrollments(ds: Dataset, done: dict[str, set[str]], and_map: dict, or_map: dict) -> tuple[set, list[str]]:
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
        if not satisfies(off.course_code, done.get(e.student_email, set()), and_map, or_map):
            errs.append(f"{e.student_email} đăng ký {off.key} nhưng chưa đủ tiên quyết (I9)")
    for email, offs in active.items():
        errs += _check_student_load(ds, email, offs, credits)
    for o in ds.offerings:  # I2: enrolled_count phải đúng bằng số đăng ký ACTIVE
        if o.enrolled_count != actual.get(o.key, 0):
            errs.append(f"enrolled_count lệch số đăng ký ACTIVE (I2): {o.key} {o.enrolled_count} != {actual.get(o.key, 0)}")
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
    return errs + e_completed + e_enroll + _check_waitlist(ds, active_pairs, waitlist_ratio)
