"""Thuật toán Gợi ý xếp lịch tự động không trùng ca (Smart Auto-Scheduler).

Sử dụng Backtracking theo heuristic MRV (Minimum Remaining Values — ưu tiên xếp
các học phần ít lớp lựa chọn trước) kết hợp chấm điểm đa tiêu chí theo 5 ca chuẩn TDTU.
"""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import api_error
from app.core.faculty import course_allowed_for_faculty
from app.models import (
    CompletedCourse,
    Course,
    CourseOffering,
    Student,
    StudyPlan,
    TermCourseOpening,
)
from app.schemas.scheduler import SchedulerPreferences, SchedulerSuggestRequest
from app.services.enrollment_queries import active_items, offering_dict
from app.services.prerequisite_engine import check_eligibility
from app.services.schedule_conflict import find_schedule_conflicts

MAX_SEARCH_NODES = 5000


def _parse_minutes(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def classify_tdtu_shift(start_hhmm: str) -> int:
    """Phân loại giờ bắt đầu về 1 trong 5 ca chuẩn TDTU."""
    mins = _parse_minutes(start_hhmm)
    if mins < 9 * 60 + 25:
        return 1
    if mins < 12 * 60 + 15:
        return 2
    if mins < 15 * 60 + 20:
        return 3
    if mins < 18 * 60:
        return 4
    return 5


def score_plan(
    chosen_offerings: list[dict],
    existing_items: list[dict],
    prefs: SchedulerPreferences,
) -> tuple[int, int, list[str]]:
    """Chấm điểm một phương án TKB hợp lệ và sinh nhãn tóm tắt tiếng Việt."""
    score = 100
    all_slots: list[dict] = []
    for item in existing_items:
        all_slots.extend(item.get("schedule", []))
    new_slots: list[dict] = []
    for off in chosen_offerings:
        new_slots.extend(off.get("schedule", []))
    all_slots.extend(new_slots)

    distinct_days = {int(s["day"]) for s in all_slots}
    study_days_count = len(distinct_days)

    has_shift_1 = False
    has_shift_5 = False
    has_sat = False
    morning_count = 0
    afternoon_count = 0

    for s in new_slots:
        shift = classify_tdtu_shift(str(s["start"]))
        day = int(s["day"])
        if shift == 1:
            has_shift_1 = True
            if prefs.avoid_first_shift:
                score -= 40
        if shift == 5:
            has_shift_5 = True
            if prefs.avoid_night_shift:
                score -= 45
        if day == 6:
            has_sat = True
            if prefs.avoid_saturday:
                score -= 40
        if shift in (1, 2):
            morning_count += 1
            if prefs.time_of_day == "MORNING":
                score += 8
            elif prefs.time_of_day == "AFTERNOON":
                score -= 5
        elif shift in (3, 4):
            afternoon_count += 1
            if prefs.time_of_day == "AFTERNOON":
                score += 8
            elif prefs.time_of_day == "MORNING":
                score -= 5

    if prefs.minimize_days:
        score -= study_days_count * 6

    # Ưu tiên nhẹ các lớp còn nhiều chỗ trống để giảm rủi ro đầy chỗ khi bấm đăng ký
    for off in chosen_offerings:
        remaining = max(0, int(off["capacity"]) - int(off["enrolled_count"]))
        score += min(4, remaining // 10)

    tags: list[str] = [f"Đi học {study_days_count} ngày/tuần"]
    if not has_shift_1:
        tags.append("Không có Ca 1")
    if not has_sat:
        tags.append("Nghỉ Thứ 7")
    if not has_shift_5:
        tags.append("Không học tối (Ca 5)")
    if morning_count > afternoon_count:
        tags.append("Thiên về buổi sáng")
    elif afternoon_count > morning_count:
        tags.append("Thiên về buổi chiều")

    return score, study_days_count, tags


def solve_schedules(
    existing_items: list[dict],
    candidates_by_course: dict[int, list[dict]],
    prefs: SchedulerPreferences,
    *,
    min_break_minutes: int = 0,
    max_results: int = 3,
    max_nodes: int = MAX_SEARCH_NODES,
) -> list[dict]:
    """Tìm tối đa `max_results` phương án TKB không trùng lịch, sắp xếp theo điểm giảm dần."""
    if not candidates_by_course:
        return []

    # Cắt tỉa sớm các lớp trùng với lịch đã đăng ký hiện tại
    pruned: dict[int, list[dict]] = {}
    for cid, offs in candidates_by_course.items():
        valid = [
            o
            for o in offs
            if not find_schedule_conflicts(
                o["schedule"], existing_items, min_break_minutes
            )
        ]
        if not valid:
            return []
        pruned[cid] = valid

    # MRV: xếp học phần có ít lớp hợp lệ nhất trước để cắt nhánh sớm
    ordered_cids = sorted(pruned.keys(), key=lambda c: (len(pruned[c]), c))

    # Sắp xếp trước các lớp của từng môn theo điểm cá nhân giảm dần
    for cid in ordered_cids:
        pruned[cid].sort(
            key=lambda o: (
                -score_plan([o], existing_items, prefs)[0],
                int(o["id"]),
            )
        )

    solutions: list[tuple[int, int, tuple[int, ...], list[dict], list[str]]] = []
    seen_keys: set[tuple[int, ...]] = set()
    chosen: list[dict] = []
    nodes = 0

    def backtrack(idx: int) -> None:
        nonlocal nodes
        if nodes >= max_nodes:
            return
        if idx == len(ordered_cids):
            key = tuple(sorted(int(o["id"]) for o in chosen))
            if key in seen_keys:
                return
            seen_keys.add(key)
            sc, days, tags = score_plan(chosen, existing_items, prefs)
            solutions.append((sc, -days, key, list(chosen), tags))
            return

        cid = ordered_cids[idx]
        for off in pruned[cid]:
            nodes += 1
            if nodes > max_nodes:
                return
            if find_schedule_conflicts(off["schedule"], chosen, min_break_minutes):
                continue
            chosen.append(off)
            backtrack(idx + 1)
            chosen.pop()

    backtrack(0)

    solutions.sort(key=lambda item: (-item[0], -item[1], item[2]))
    top = solutions[:max_results]
    results = []
    for rank, (sc, neg_days, _key, offs, tags) in enumerate(top, 1):
        added_credits = sum(int(o["credits"]) for o in offs)
        results.append(
            {
                "rank": rank,
                "score": sc,
                "added_credits": added_credits,
                "study_days_count": -neg_days,
                "tags": tags,
                "offerings": sorted(offs, key=lambda o: (o["code"], o["section"])),
            }
        )
    return results


async def suggest_schedules(
    session: AsyncSession,
    student_id: int,
    req: SchedulerSuggestRequest,
) -> dict:
    settings = get_settings()
    target_term = req.term or settings.study_plan_term

    student = await session.get(Student, student_id)
    if student is None:
        raise api_error(404, "NOT_FOUND", "Không tìm thấy sinh viên")

    existing = await active_items(session, student_id, target_term)
    current_credits = sum(int(i["credits"]) for i in existing)
    enrolled_cids = {int(i["course_id"]) for i in existing}

    completed_cids = set(
        (
            await session.scalars(
                select(CompletedCourse.course_id).where(
                    CompletedCourse.student_id == student_id
                )
            )
        ).all()
    )

    # Tải các học phần trong KHHT kỳ hiện tại (chỉ lấy các môn chưa đăng ký & chưa hoàn thành)
    plan_rows = (
        await session.execute(
            select(Course, TermCourseOpening)
            .join(StudyPlan, StudyPlan.course_id == Course.id)
            .outerjoin(
                TermCourseOpening,
                (TermCourseOpening.course_id == Course.id)
                & (TermCourseOpening.term == target_term),
            )
            .where(
                StudyPlan.student_id == student_id,
                StudyPlan.term == target_term,
            )
            .order_by(Course.code)
        )
    ).all()

    planned_cids: set[int] = set()
    default_target_cids: list[int] = []
    target_courses_ui: list[dict] = []

    for course, opening in plan_rows:
        planned_cids.add(course.id)
        if course.id in enrolled_cids or course.id in completed_cids:
            continue
        if opening is not None and opening.status == "NOT_OPENED":
            continue
        default_target_cids.append(course.id)

    selected_cids: list[int]
    if req.course_ids is not None:
        # Giữ đúng thứ tự và loại trùng
        selected_cids = list(dict.fromkeys(req.course_ids))
    else:
        # Mặc định chọn tối đa các môn KHHT vừa hạn mức tín chỉ
        selected_cids = []
        running = current_credits
        for cid in default_target_cids:
            c_obj = next(c for c, _ in plan_rows if c.id == cid)
            if running + c_obj.credits <= student.max_credits:
                selected_cids.append(cid)
                running += c_obj.credits

    # Dựng danh sách target_courses cho UI (toàn bộ môn KHHT mở lớp chưa ĐK + môn user gửi thêm)
    ui_cids = list(dict.fromkeys([*default_target_cids, *selected_cids]))
    courses_by_id: dict[int, Course] = {}
    if ui_cids:
        course_objs = (
            await session.scalars(
                select(Course).where(Course.id.in_(ui_cids)).order_by(Course.code)
            )
        ).all()
        courses_by_id = {c.id: c for c in course_objs}
        for c in course_objs:
            if c.id in enrolled_cids or c.id in completed_cids:
                continue
            target_courses_ui.append(
                {
                    "course_id": c.id,
                    "code": c.code,
                    "name": c.name,
                    "credits": c.credits,
                    "in_study_plan": c.id in planned_cids,
                    "selected": c.id in selected_cids,
                }
            )

    if not selected_cids:
        return {
            "term": target_term,
            "current_credits": current_credits,
            "max_credits": student.max_credits,
            "credit_limit_warning": None,
            "target_courses": target_courses_ui,
            "plans": [],
            "unschedulable": [],
        }

    # Lấy trạng thái mở lớp và các lớp học phần của nhóm môn được chọn
    opening_rows = (
        await session.scalars(
            select(TermCourseOpening).where(
                TermCourseOpening.term == target_term,
                TermCourseOpening.course_id.in_(selected_cids),
            )
        )
    ).all()
    openings_by_cid = {op.course_id: op for op in opening_rows}

    offering_rows = (
        await session.scalars(
            select(CourseOffering)
            .where(
                CourseOffering.term == target_term,
                CourseOffering.course_id.in_(selected_cids),
            )
            .order_by(CourseOffering.course_id, CourseOffering.section)
        )
    ).all()
    offerings_by_cid: dict[int, list[CourseOffering]] = defaultdict(list)
    for off in offering_rows:
        offerings_by_cid[off.course_id].append(off)

    unschedulable: list[dict] = []
    candidates_by_course: dict[int, list[dict]] = {}
    schedulable_credits = 0

    for cid in selected_cids:
        c = courses_by_id.get(cid)
        if c is None:
            continue
        if cid in enrolled_cids:
            unschedulable.append(
                {
                    "course_id": cid,
                    "code": c.code,
                    "name": c.name,
                    "credits": c.credits,
                    "reason": "ALREADY_ENROLLED",
                    "detail": "Bạn đã đăng ký học phần này trong kỳ.",
                }
            )
            continue
        if cid in completed_cids:
            unschedulable.append(
                {
                    "course_id": cid,
                    "code": c.code,
                    "name": c.name,
                    "credits": c.credits,
                    "reason": "ALREADY_COMPLETED",
                    "detail": "Học phần này đã hoàn thành.",
                }
            )
            continue
        if student.role == "student" and not course_allowed_for_faculty(
            c.code, student.faculty
        ):
            unschedulable.append(
                {
                    "course_id": cid,
                    "code": c.code,
                    "name": c.name,
                    "credits": c.credits,
                    "reason": "FACULTY_MISMATCH",
                    "detail": f"Không thuộc chương trình đào tạo của {student.faculty}.",
                }
            )
            continue
        op = openings_by_cid.get(cid)
        if op is not None and op.status == "NOT_OPENED":
            unschedulable.append(
                {
                    "course_id": cid,
                    "code": c.code,
                    "name": c.name,
                    "credits": c.credits,
                    "reason": "NOT_OPENED",
                    "detail": "Học phần không mở lớp do chưa đủ SV ĐKKHHT.",
                }
            )
            continue
        if student.accumulated_credits < c.min_accumulated_credits:
            unschedulable.append(
                {
                    "course_id": cid,
                    "code": c.code,
                    "name": c.name,
                    "credits": c.credits,
                    "reason": "MIN_CREDITS_NOT_MET",
                    "detail": f"Yêu cầu tối thiểu {c.min_accumulated_credits} TC tích lũy.",
                }
            )
            continue
        elig = await check_eligibility(session, student_id, cid)
        if not elig.eligible:
            unschedulable.append(
                {
                    "course_id": cid,
                    "code": c.code,
                    "name": c.name,
                    "credits": c.credits,
                    "reason": "PREREQ_UNMET",
                    "detail": "Chưa đạt điều kiện tiên quyết.",
                }
            )
            continue

        all_offs = offerings_by_cid.get(cid, [])
        open_offs = [o for o in all_offs if o.enrolled_count < o.capacity]
        if not open_offs:
            unschedulable.append(
                {
                    "course_id": cid,
                    "code": c.code,
                    "name": c.name,
                    "credits": c.credits,
                    "reason": "ALL_SECTIONS_FULL",
                    "detail": "Tất cả các lớp mở của môn này hiện đã đầy sĩ số.",
                }
            )
            continue

        off_dicts = [
            offering_dict(o, c) | {"in_study_plan": cid in planned_cids}
            for o in open_offs
        ]
        non_conflicting = [
            o
            for o in off_dicts
            if not find_schedule_conflicts(
                o["schedule"], existing, settings.min_break_minutes
            )
        ]
        if not non_conflicting:
            unschedulable.append(
                {
                    "course_id": cid,
                    "code": c.code,
                    "name": c.name,
                    "credits": c.credits,
                    "reason": "CONFLICT_WITH_ENROLLED",
                    "detail": "Mọi lớp còn chỗ đều trùng lịch với môn bạn đã đăng ký.",
                }
            )
            continue

        candidates_by_course[cid] = non_conflicting
        schedulable_credits += c.credits

    credit_warning = None
    if current_credits + schedulable_credits > student.max_credits:
        credit_warning = (
            f"Tổng tín chỉ dự kiến ({current_credits + schedulable_credits} TC) "
            f"vượt hạn mức {student.max_credits} TC/học kỳ. Hãy bỏ bớt môn nếu cần."
        )

    raw_plans = solve_schedules(
        existing,
        candidates_by_course,
        req.preferences,
        min_break_minutes=settings.min_break_minutes,
        max_results=req.max_results,
    )

    plans = [
        {
            "rank": p["rank"],
            "score": p["score"],
            "total_credits": current_credits + p["added_credits"],
            "added_credits": p["added_credits"],
            "study_days_count": p["study_days_count"],
            "tags": p["tags"],
            "offerings": p["offerings"],
        }
        for p in raw_plans
    ]

    return {
        "term": target_term,
        "current_credits": current_credits,
        "max_credits": student.max_credits,
        "credit_limit_warning": credit_warning,
        "target_courses": target_courses_ui,
        "plans": plans,
        "unschedulable": unschedulable,
    }
