"""Kiểm thử API Quản trị Điều kiện Tiên quyết - /admin/prereqs (M4, Tuần 4).

Các kịch bản kiểm thử:
1. Thêm cạnh AND hợp lệ (group_no = 0) -> 201 Created.
2. Thêm cạnh OR hợp lệ (group_no >= 1) -> 201 Created.
3. Ràng buộc group_no: AND có group_no > 0 -> 422 VALIDATION_ERROR.
4. Ràng buộc group_no: OR có group_no = 0 -> 422 VALIDATION_ERROR.
5. Chặn tự trỏ: course_id == prereq_course_id -> 422 VALIDATION_ERROR.
6. Môn học không tồn tại -> 404 NOT_FOUND.
7. Trùng cạnh tiên quyết -> 409 ALREADY_EXISTS.
8. Chặn chu trình (Cycle Detection): tạo vòng -> 422 PREREQ_CYCLE kèm cycle_path.
9. Lấy danh sách tiên quyết của môn học: phân tách rõ nhóm AND và các nhóm OR.
10. Cập nhật nhóm/loại tiên quyết -> thành công.
11. Xóa cạnh tiên quyết -> thành công.
12. Phân quyền: sinh viên gọi -> 403 FORBIDDEN.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.core.security import CurrentUser, require_role
from app.models import Course, Prerequisite
from app.schemas.prerequisite import PrereqCreate, PrereqUpdate
from app.services import prerequisite_admin_service
from app.services.prerequisite_core import PrerequisiteCycleError

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_create_prereq_and_success():
    """Thêm cạnh AND hợp lệ."""
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()

    c1 = Course(id=1, code="INT131", name="Cấu trúc dữ liệu", credits=3)
    c2 = Course(id=2, code="INT101", name="Nhập môn lập trình", credits=3)

    async def mock_get(model, cid):
        return {1: c1, 2: c2}.get(cid)

    session.get = AsyncMock(side_effect=mock_get)

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_res

    with (
        patch(
            "app.services.prerequisite_engine.ensure_edge_allowed",
            new_callable=AsyncMock,
        ),
        patch(
            "app.services.prerequisite_engine.invalidate_graph",
            new_callable=AsyncMock,
        ) as mock_inv,
    ):
        body = PrereqCreate(course_id=1, prereq_course_id=2, type="AND", group_no=0)
        res = await prerequisite_admin_service.create_prerequisite(session, body)

        assert res.course_id == 1
        assert res.prereq_course_id == 2
        assert res.type == "AND"
        assert res.group_no == 0
        assert session.commit.called
        assert mock_inv.called


@pytest.mark.asyncio
async def test_create_prereq_or_success():
    """Thêm cạnh OR hợp lệ (group_no >= 1)."""
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()

    c1 = Course(id=3, code="INT221", name="Mạng máy tính", credits=3)
    c2 = Course(id=4, code="INT222", name="Hệ điều hành", credits=3)

    async def mock_get(model, cid):
        return {3: c1, 4: c2}.get(cid)

    session.get = AsyncMock(side_effect=mock_get)

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_res

    with (
        patch(
            "app.services.prerequisite_engine.ensure_edge_allowed",
            new_callable=AsyncMock,
        ),
        patch(
            "app.services.prerequisite_engine.invalidate_graph",
            new_callable=AsyncMock,
        ),
    ):
        body = PrereqCreate(course_id=3, prereq_course_id=4, type="OR", group_no=1)
        res = await prerequisite_admin_service.create_prerequisite(session, body)

        assert res.type == "OR"
        assert res.group_no == 1


@pytest.mark.asyncio
async def test_create_prereq_invalid_group_no():
    """Ràng buộc group_no không hợp lệ."""
    session = AsyncMock()

    # AND nhưng group_no > 0
    with pytest.raises(HTTPException) as exc1:
        await prerequisite_admin_service.create_prerequisite(
            session,
            PrereqCreate(course_id=1, prereq_course_id=2, type="AND", group_no=1),
        )
    assert exc1.value.status_code == 422
    assert exc1.value.detail["code"] == "VALIDATION_ERROR"

    # OR nhưng group_no == 0
    with pytest.raises(HTTPException) as exc2:
        await prerequisite_admin_service.create_prerequisite(
            session,
            PrereqCreate(course_id=1, prereq_course_id=2, type="OR", group_no=0),
        )
    assert exc2.value.status_code == 422
    assert exc2.value.detail["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_create_prereq_self_loop():
    """Chặn tự trỏ: course_id == prereq_course_id."""
    session = AsyncMock()
    with pytest.raises(HTTPException) as exc:
        await prerequisite_admin_service.create_prerequisite(
            session,
            PrereqCreate(course_id=1, prereq_course_id=1, type="AND", group_no=0),
        )
    assert exc.value.status_code == 422
    assert exc.value.detail["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_create_prereq_course_not_found():
    """Môn học không tồn tại."""
    session = AsyncMock()
    session.get.return_value = None

    with pytest.raises(HTTPException) as exc:
        await prerequisite_admin_service.create_prerequisite(
            session,
            PrereqCreate(course_id=999, prereq_course_id=2, type="AND", group_no=0),
        )
    assert exc.value.status_code == 404
    assert exc.value.detail["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_create_prereq_already_exists():
    """Cạnh tiên quyết đã tồn tại."""
    session = AsyncMock()
    c1 = Course(id=1, code="INT131", name="Môn 1", credits=3)
    c2 = Course(id=2, code="INT101", name="Môn 2", credits=3)

    async def mock_get(model, cid):
        return {1: c1, 2: c2}.get(cid)

    session.get = AsyncMock(side_effect=mock_get)

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = Prerequisite(
        course_id=1, prereq_course_id=2, type="AND", group_no=0
    )
    session.execute.return_value = mock_res

    with pytest.raises(HTTPException) as exc:
        await prerequisite_admin_service.create_prerequisite(
            session,
            PrereqCreate(course_id=1, prereq_course_id=2, type="AND", group_no=0),
        )
    assert exc.value.status_code == 409
    assert exc.value.detail["code"] == "ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_create_prereq_cycle_detection():
    """Chặn chu trình: 422 PREREQ_CYCLE kèm cycle_path."""
    session = AsyncMock()
    c1 = Course(id=1, code="INT131", name="Môn 1", credits=3)
    c2 = Course(id=2, code="INT101", name="Môn 2", credits=3)

    async def mock_get(model, cid):
        return {1: c1, 2: c2}.get(cid)

    session.get = AsyncMock(side_effect=mock_get)

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_res

    with patch(
        "app.services.prerequisite_engine.ensure_edge_allowed",
        side_effect=PrerequisiteCycleError(["INT131", "INT101", "INT131"]),
    ):
        with pytest.raises(HTTPException) as exc:
            await prerequisite_admin_service.create_prerequisite(
                session,
                PrereqCreate(course_id=1, prereq_course_id=2, type="AND", group_no=0),
            )
        assert exc.value.status_code == 422
        assert exc.value.detail["code"] == "PREREQ_CYCLE"
        assert exc.value.detail["cycle_path"] == ["INT131", "INT101", "INT131"]


@pytest.mark.asyncio
async def test_get_course_prerequisites_separated():
    """Lấy danh sách điều kiện tiên quyết của môn học phân tách rõ AND và OR groups."""
    session = AsyncMock()
    course = Course(id=10, code="INT451", name="Đồ án", credits=4)
    session.get = AsyncMock(return_value=course)

    p1 = Prerequisite(course_id=10, prereq_course_id=1, type="AND", group_no=0)
    c1 = Course(id=1, code="INT101", name="Nhập môn", credits=3)

    p2 = Prerequisite(course_id=10, prereq_course_id=2, type="OR", group_no=1)
    c2 = Course(id=2, code="INT221", name="Mạng", credits=3)

    p3 = Prerequisite(course_id=10, prereq_course_id=3, type="OR", group_no=1)
    c3 = Course(id=3, code="INT222", name="Hệ điều hành", credits=3)

    mock_res = MagicMock()
    mock_res.all.return_value = [(p1, c1), (p2, c2), (p3, c3)]
    session.execute.return_value = mock_res

    resp = await prerequisite_admin_service.get_course_prerequisites(session, 10)
    assert resp.course_code == "INT451"
    assert len(resp.and_prerequisites) == 1
    assert resp.and_prerequisites[0].prereq_code == "INT101"
    assert len(resp.or_groups) == 1
    assert resp.or_groups[0].group_no == 1
    assert len(resp.or_groups[0].options) == 2


@pytest.mark.asyncio
async def test_update_and_delete_prerequisite():
    """Cập nhật và xóa điều kiện tiên quyết."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.delete = AsyncMock()

    edge = Prerequisite(course_id=1, prereq_course_id=2, type="AND", group_no=0)
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = edge
    session.execute.return_value = mock_res

    c1 = Course(id=1, code="C1", name="Course 1", credits=3)
    c2 = Course(id=2, code="C2", name="Course 2", credits=3)

    async def mock_get(model, cid):
        return {1: c1, 2: c2}.get(cid)

    session.get = AsyncMock(side_effect=mock_get)

    with patch(
        "app.services.prerequisite_engine.invalidate_graph",
        new_callable=AsyncMock,
    ) as mock_inv:
        # Cập nhật
        updated = await prerequisite_admin_service.update_prerequisite(
            session, 1, 2, PrereqUpdate(type="OR", group_no=2)
        )
        assert updated.type == "OR"
        assert updated.group_no == 2
        assert mock_inv.called

        # Xóa
        mock_inv.reset_mock()
        await prerequisite_admin_service.delete_prerequisite(session, 1, 2)
        assert session.delete.called
        assert mock_inv.called


@pytest.mark.asyncio
async def test_require_role_admin_guard_on_prereqs():
    """Kiểm tra phân quyền: sinh viên gọi API admin bị 403 FORBIDDEN."""
    guard = require_role("admin")

    student_user = CurrentUser(id=1, role="student", email="sv0001@uni.edu.vn")
    with pytest.raises(HTTPException) as exc:
        await guard(user=student_user)
    assert exc.value.status_code == 403
    assert exc.value.detail["code"] == "FORBIDDEN"

    admin_user = CurrentUser(id=1001, role="admin", email="admin@uni.edu.vn")
    res = await guard(user=admin_user)
    assert res == admin_user
