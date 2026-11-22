"""Nghiệp vụ quản trị sĩ số lớp học phần phục vụ kiểm thử đầy lớp & hàng chờ (Waitlist)."""

from __future__ import annotations

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import api_error
from app.models import (
    CompletedCourse,
    CourseOffering,
    Enrollment,
    Student,
    Waitlist,
)
from app.services import enrollment_service

# Bảo vệ các tài khoản sinh viên dùng cho kịch bản demo để admin không lỡ điền/hủy nhầm
PROTECTED_DEMO_EMAILS = frozenset(
    {
        "sv0001@uni.edu.vn",
        "sv0055@uni.edu.vn",
        "sv0587@uni.edu.vn",
    }
)


async def fill_offering_to_capacity(session: AsyncSession, offering_id: int) -> dict:
    """Điền đầy sĩ số lớp học phần bằng các sinh viên chưa đăng ký môn để test Waitlist."""
    offering = await session.scalar(
        select(CourseOffering).where(CourseOffering.id == offering_id).with_for_update()
    )
    if offering is None:
        raise api_error(404, "NOT_FOUND", "Không tìm thấy lớp học phần")

    needed = offering.capacity - offering.enrolled_count
    if needed <= 0:
        return {
            "offering_id": offering.id,
            "enrolled_count": offering.enrolled_count,
            "capacity": offering.capacity,
            "added_count": 0,
            "message": f"Lớp đã đầy sĩ số ({offering.enrolled_count}/{offering.capacity}).",
        }

    # Chọn sinh viên chưa có đăng ký ACTIVE nào trong kỳ (tránh trùng lịch / vượt tín chỉ)
    # và chưa hoàn thành môn học này, không chạm vào tài khoản demo.
    has_active_enr = exists(
        select(Enrollment.id)
        .join(CourseOffering, CourseOffering.id == Enrollment.offering_id)
        .where(
            Enrollment.student_id == Student.id,
            Enrollment.status == "ACTIVE",
            CourseOffering.term == offering.term,
        )
    )
    has_completed = exists(
        select(CompletedCourse.course_id).where(
            CompletedCourse.student_id == Student.id,
            CompletedCourse.course_id == offering.course_id,
        )
    )
    has_waitlist = exists(
        select(Waitlist.id).where(
            Waitlist.student_id == Student.id,
            Waitlist.offering_id == offering.id,
        )
    )

    candidate_ids = list(
        (
            await session.scalars(
                select(Student.id)
                .where(
                    Student.role == "student",
                    Student.email.notin_(PROTECTED_DEMO_EMAILS),
                    ~has_active_enr,
                    ~has_completed,
                    ~has_waitlist,
                )
                .order_by(Student.id.desc())
                .limit(needed)
            )
        ).all()
    )

    for sid in candidate_ids:
        session.add(
            Enrollment(
                student_id=sid,
                offering_id=offering.id,
                status="ACTIVE",
                version=0,
            )
        )

    added = len(candidate_ids)
    offering.enrolled_count += added
    # Fallback nếu DB test quá nhỏ không đủ sinh viên rảnh: co capacity khớp sĩ số hiện tại
    if offering.enrolled_count < offering.capacity:
        offering.capacity = max(offering.enrolled_count, 1)

    await session.commit()
    return {
        "offering_id": offering.id,
        "enrolled_count": offering.enrolled_count,
        "capacity": offering.capacity,
        "added_count": added,
        "message": (
            f"Đã làm đầy lớp học phần ({offering.enrolled_count}/{offering.capacity}, "
            f"bổ sung {added} sinh viên). Bạn có thể chuyển sang tài khoản sinh viên để test Waitlist."
        ),
    }


async def release_one_seat(session: AsyncSession, offering_id: int) -> dict:
    """Hủy 1 sinh viên nền khỏi lớp để giải phóng chỗ và kích hoạt đôn Waitlist tự động."""
    offering = await session.get(CourseOffering, offering_id)
    if offering is None:
        raise api_error(404, "NOT_FOUND", "Không tìm thấy lớp học phần")

    target = (
        await session.execute(
            select(Enrollment.id, Enrollment.student_id)
            .join(Student, Student.id == Enrollment.student_id)
            .where(
                Enrollment.offering_id == offering_id,
                Enrollment.status == "ACTIVE",
                Student.email.notin_(PROTECTED_DEMO_EMAILS),
            )
            .order_by(Enrollment.id.desc())
            .limit(1)
        )
    ).one_or_none()

    if target is None:
        raise api_error(
            409,
            "NO_RELEASABLE_SEAT",
            "Không còn sinh viên nền nào để giải phóng (chỉ còn tài khoản demo hoặc lớp đang trống).",
        )

    enr_id, student_id = int(target[0]), int(target[1])
    before_active_sids = set(
        (
            await session.scalars(
                select(Enrollment.student_id).where(
                    Enrollment.offering_id == offering_id,
                    Enrollment.status == "ACTIVE",
                )
            )
        ).all()
    )

    await enrollment_service.cancel(session, student_id, enr_id)
    await session.refresh(offering)

    after_active_sids = set(
        (
            await session.scalars(
                select(Enrollment.student_id).where(
                    Enrollment.offering_id == offering_id,
                    Enrollment.status == "ACTIVE",
                )
            )
        ).all()
    )
    newly_promoted = list(after_active_sids - before_active_sids)
    promoted_sid = int(newly_promoted[0]) if newly_promoted else None
    promoted_label = ""
    if promoted_sid is not None:
        p_student = await session.get(Student, promoted_sid)
        promoted_label = (
            p_student.mssv or p_student.email
            if p_student is not None
            else f"ID {promoted_sid}"
        )

    msg = (
        f"Đã giải phóng 1 chỗ và tự động đôn sinh viên {promoted_label} từ hàng chờ vào lớp! "
        f"Sĩ số hiện tại: {offering.enrolled_count}/{offering.capacity}."
        if promoted_sid
        else f"Đã giải phóng 1 chỗ trống. Sĩ số hiện tại: {offering.enrolled_count}/{offering.capacity}."
    )
    return {
        "offering_id": offering.id,
        "enrolled_count": offering.enrolled_count,
        "capacity": offering.capacity,
        "promoted_student_id": promoted_sid,
        "message": msg,
    }
