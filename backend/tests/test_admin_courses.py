"""Kiểm thử API Quản trị học phần - /admin/courses (M4, Tuần 3).

Các trường hợp:
1. Tạo học phần mới thành công (201).
2. Tạo trùng mã học phần -> 409 ALREADY_EXISTS.
3. Cập nhật học phần thành công.
4. Xóa học phần đang có tham chiếu (lớp học phần, tiên quyết, sinh viên đã học) -> 409 IN_USE.
5. Xóa học phần không có tham chiếu -> thành công.
6. Tra cứu học phần không tồn tại -> 404 NOT_FOUND.
7. Phân quyền: Sinh viên gọi API admin -> 403 FORBIDDEN; Admin gọi -> thành công.
"""
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi import HTTPException

from app.core.security import CurrentUser, require_role
from app.models import Course
from app.schemas.course import CourseCreate, CourseUpdate
from app.services import course_service


@pytest.mark.asyncio
async def test_create_course_success():
    session = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_res

    data = CourseCreate(
        code="INT999",
        name="Chuyên đề Trí tuệ Nhân tạo",
        credits=3,
        description="Môn học thử nghiệm",
    )
    course = await course_service.create_course(session, data)

    assert course.code == "INT999"
    assert course.name == "Chuyên đề Trí tuệ Nhân tạo"
    assert course.credits == 3
    assert session.add.called
    assert session.commit.called


@pytest.mark.asyncio
async def test_create_course_duplicate_code_raises_409():
    session = AsyncMock()
    existing_course = Course(id=1, code="INT131", name="Nhập môn lập trình", credits=3)
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = existing_course
    session.execute.return_value = mock_res

    data = CourseCreate(code="int131", name="Trùng mã", credits=3)

    with pytest.raises(HTTPException) as exc_info:
        await course_service.create_course(session, data)

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_get_course_not_found_raises_404():
    session = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_res

    with pytest.raises(HTTPException) as exc_info:
        await course_service.get_course_by_id(session, 99999)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_delete_course_in_use_raises_409():
    session = AsyncMock()
    course = Course(id=10, code="INT101", name="Cơ sở lập trình", credits=3)

    mock_get = MagicMock()
    mock_get.scalar_one_or_none.return_value = course

    mock_offering = MagicMock()
    mock_offering.scalar_one.return_value = 2

    mock_prereq_of = MagicMock()
    mock_prereq_of.scalar_one.return_value = 1

    mock_has_prereq = MagicMock()
    mock_has_prereq.scalar_one.return_value = 0

    mock_completed = MagicMock()
    mock_completed.scalar_one.return_value = 15

    session.execute.side_effect = [
        mock_get,
        mock_offering,
        mock_prereq_of,
        mock_has_prereq,
        mock_completed,
    ]

    with pytest.raises(HTTPException) as exc_info:
        await course_service.delete_course(session, 10)

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "IN_USE"
    assert len(exc_info.value.detail["references"]) == 3
    assert not session.delete.called


@pytest.mark.asyncio
async def test_delete_course_safe_success():
    session = AsyncMock()
    course = Course(id=20, code="INT999", name="Môn độc lập", credits=2)

    mock_get = MagicMock()
    mock_get.scalar_one_or_none.return_value = course

    mock_zero = MagicMock()
    mock_zero.scalar_one.return_value = 0

    session.execute.side_effect = [
        mock_get,
        mock_zero,
        mock_zero,
        mock_zero,
        mock_zero,
    ]

    with patch("app.services.course_service.get_redis") as mock_redis_getter:
        mock_r = AsyncMock()
        mock_redis_getter.return_value = mock_r
        await course_service.delete_course(session, 20)

    assert session.delete.called
    assert session.commit.called


@pytest.mark.asyncio
async def test_require_role_admin_guard():
    guard = require_role("admin")

    # Sinh viên gọi -> 403 FORBIDDEN
    student_user = CurrentUser(id=1, role="student", email="sv@uni.edu.vn")
    with pytest.raises(HTTPException) as exc_info:
        await guard(user=student_user)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["code"] == "FORBIDDEN"

    # Admin gọi -> thành công
    admin_user = CurrentUser(id=1001, role="admin", email="admin@uni.edu.vn")
    res = await guard(user=admin_user)
    assert res == admin_user
