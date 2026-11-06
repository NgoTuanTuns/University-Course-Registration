"""Router quản trị học phần (M4, Tuần 3).

Quy ước chung của nhóm:
- Toàn bộ router này yêu cầu quyền quản trị viên: require_role("admin").
  Sinh viên gọi tới sẽ nhận 403 FORBIDDEN.
- Tiền tố: /admin/courses
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import require_role
from app.schemas.auth import MessageResponse
from app.schemas.course import CourseCreate, CourseListResponse, CourseOut, CourseUpdate
from app.services import course_service

router = APIRouter(
    prefix="/admin/courses",
    tags=["admin-courses"],
    dependencies=[Depends(require_role("admin"))],
)


@router.get("", response_model=CourseListResponse)
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


@router.get("/{course_id}", response_model=CourseOut)
async def get_course(
    course_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CourseOut:
    """Lấy thông tin chi tiết một học phần."""
    course = await course_service.get_course_by_id(session, course_id)
    return CourseOut.model_validate(course)


@router.post("", response_model=CourseOut, status_code=status.HTTP_201_CREATED)
async def create_course(
    body: CourseCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CourseOut:
    """Tạo mới một học phần. Báo 409 ALREADY_EXISTS nếu trùng mã."""
    course = await course_service.create_course(session, body)
    return CourseOut.model_validate(course)


@router.put("/{course_id}", response_model=CourseOut)
async def update_course(
    course_id: int,
    body: CourseUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CourseOut:
    """Cập nhật thông tin học phần."""
    course = await course_service.update_course(session, course_id, body)
    return CourseOut.model_validate(course)


@router.delete("/{course_id}", response_model=MessageResponse)
async def delete_course(
    course_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> MessageResponse:
    """Xóa học phần. Nếu đang có tham chiếu (lớp học, tiên quyết, điểm), trả 409 IN_USE."""
    await course_service.delete_course(session, course_id)
    return MessageResponse(message=f"Đã xóa thành công học phần có ID={course_id}")
