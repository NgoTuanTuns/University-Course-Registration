"""Router quản trị hệ thống (M4, Tuần 3 và Tuần 4).

Bao gồm:
- /admin/courses: CRUD học phần (M4 Tuần 3)
- /admin/prereqs: Quản lý điều kiện tiên quyết và đồ thị DAG (M4 Tuần 4)

Toàn bộ router này yêu cầu quyền quản trị viên: require_role("admin").
Sinh viên gọi tới sẽ nhận 403 FORBIDDEN.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import require_role
from app.schemas.auth import MessageResponse
from app.schemas.course import CourseCreate, CourseListResponse, CourseOut, CourseUpdate
from app.schemas.prerequisite import (
    CoursePrereqsResponse,
    PrereqCreate,
    PrereqEdgeOut,
    PrereqListResponse,
    PrereqUpdate,
)
from app.services import (
    course_service,
    offering_admin_service,
    prerequisite_admin_service,
)

router = APIRouter(
    prefix="/admin",
    dependencies=[Depends(require_role("admin"))],
)

courses_router = APIRouter(prefix="/courses", tags=["admin-courses"])
prereqs_router = APIRouter(prefix="/prereqs", tags=["admin-prereqs"])
offerings_router = APIRouter(prefix="/offerings", tags=["admin-offerings"])


# ===========================================================================
# 1. Quản trị học phần (/admin/courses)
# ===========================================================================


@courses_router.get("", response_model=CourseListResponse)
async def list_courses(
    session: Annotated[AsyncSession, Depends(get_session)],
    q: str | None = Query(
        default=None, description="Tìm kiếm theo mã hoặc tên môn học"
    ),
    page: int = Query(default=1, ge=1, description="Trang hiện tại (bắt đầu từ 1)"),
    page_size: int = Query(
        default=20, ge=1, le=100, description="Số lượng mỗi trang (tối đa 100)"
    ),
) -> CourseListResponse:
    """Lấy danh sách học phần (phân trang, tìm kiếm)."""
    items, total = await course_service.list_courses(
        session, q=q, page=page, page_size=page_size
    )
    return CourseListResponse(
        items=[CourseOut.model_validate(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@courses_router.get("/{course_id}", response_model=CourseOut)
async def get_course(
    course_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CourseOut:
    """Lấy thông tin chi tiết một học phần."""
    course = await course_service.get_course_by_id(session, course_id)
    return CourseOut.model_validate(course)


@courses_router.post("", response_model=CourseOut, status_code=status.HTTP_201_CREATED)
async def create_course(
    body: CourseCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CourseOut:
    """Tạo mới một học phần. Báo 409 ALREADY_EXISTS nếu trùng mã."""
    course = await course_service.create_course(session, body)
    return CourseOut.model_validate(course)


@courses_router.put("/{course_id}", response_model=CourseOut)
async def update_course(
    course_id: int,
    body: CourseUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CourseOut:
    """Cập nhật thông tin học phần."""
    course = await course_service.update_course(session, course_id, body)
    return CourseOut.model_validate(course)


@courses_router.delete("/{course_id}", response_model=MessageResponse)
async def delete_course(
    course_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> MessageResponse:
    """Xóa học phần. Nếu đang có tham chiếu (lớp học, tiên quyết, điểm), trả 409 IN_USE."""
    await course_service.delete_course(session, course_id)
    return MessageResponse(message=f"Đã xóa thành công học phần có ID={course_id}")


# ===========================================================================
# 2. Quản trị điều kiện tiên quyết (/admin/prereqs)
# ===========================================================================


@prereqs_router.get("", response_model=PrereqListResponse)
async def list_prerequisites(
    session: Annotated[AsyncSession, Depends(get_session)],
    course_id: int | None = Query(
        default=None, description="Lọc theo ID học phần (tùy chọn)"
    ),
) -> PrereqListResponse:
    """Lấy danh sách các cạnh tiên quyết trong hệ thống (có thể lọc theo môn học)."""
    items = await prerequisite_admin_service.list_prerequisites(
        session, course_id=course_id
    )
    return PrereqListResponse(items=items, total=len(items))


@prereqs_router.get("/{course_id}", response_model=CoursePrereqsResponse)
async def get_course_prerequisites(
    course_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CoursePrereqsResponse:
    """Lấy danh sách điều kiện tiên quyết của môn học, phân tách rõ nhóm AND và nhóm OR."""
    return await prerequisite_admin_service.get_course_prerequisites(
        session, course_id=course_id
    )


@prereqs_router.post(
    "", response_model=PrereqEdgeOut, status_code=status.HTTP_201_CREATED
)
async def create_prerequisite(
    body: PrereqCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PrereqEdgeOut:
    """Thêm một điều kiện tiên quyết mới.

    - Tự động kiểm tra chu trình (DFS): nếu tạo vòng trả 422 PREREQ_CYCLE kèm cycle_path.
    - Dùng PostgreSQL advisory lock để tuần tự hóa hai admin ghi đồng thời.
    - Tự động xóa cache Redis sau khi commit thành công.
    """
    return await prerequisite_admin_service.create_prerequisite(session, body)


@prereqs_router.put("/{course_id}/{prereq_course_id}", response_model=PrereqEdgeOut)
async def update_prerequisite(
    course_id: int,
    prereq_course_id: int,
    body: PrereqUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PrereqEdgeOut:
    """Cập nhật loại ràng buộc (AND/OR) hoặc group_no của điều kiện tiên quyết."""
    return await prerequisite_admin_service.update_prerequisite(
        session, course_id, prereq_course_id, body
    )


@prereqs_router.delete(
    "/{course_id}/{prereq_course_id}", response_model=MessageResponse
)
async def delete_prerequisite(
    course_id: int,
    prereq_course_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> MessageResponse:
    """Xóa một điều kiện tiên quyết khỏi hệ thống và dọn dẹp cache."""
    await prerequisite_admin_service.delete_prerequisite(
        session, course_id, prereq_course_id
    )
    return MessageResponse(
        message=f"Đã xóa thành công điều kiện tiên quyết ({course_id} -> {prereq_course_id})"
    )


# ===========================================================================
# 3. Quản trị sĩ số lớp học phần phục vụ test đầy lớp / Waitlist (/admin/offerings)
# ===========================================================================


@offerings_router.post("/{offering_id}/fill")
async def fill_offering(
    offering_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    """Làm đầy sĩ số một lớp học phần để kiểm thử kịch bản đầy chỗ và danh sách chờ."""
    return await offering_admin_service.fill_offering_to_capacity(session, offering_id)


@offerings_router.post("/{offering_id}/release-seat")
async def release_offering_seat(
    offering_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    """Giải phóng 1 chỗ trống (hủy 1 sinh viên nền) để kích hoạt đôn Waitlist tự động."""
    return await offering_admin_service.release_one_seat(session, offering_id)


# Kết nối subrouters vào router chính của admin
router.include_router(courses_router)
router.include_router(prereqs_router)
router.include_router(offerings_router)
