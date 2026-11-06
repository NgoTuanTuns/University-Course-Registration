"""Nghiệp vụ đăng nhập (M4): tra DB, kiểm tra mật khẩu. Không biết gì về HTTP."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core.security import hash_password, verify_password
from app.models import Student

_dummy_hash: str | None = None


async def _get_dummy_hash() -> str:
    """Hash giả, tính một lần, để email không tồn tại cũng tốn thời gian như email có thật."""
    global _dummy_hash
    if _dummy_hash is None:
        _dummy_hash = await run_in_threadpool(
            hash_password, "mat-khau-gia-de-do-thoi-gian"
        )
    return _dummy_hash


async def authenticate(
    session: AsyncSession, email: str, password: str
) -> Student | None:
    """Trả người dùng nếu email + mật khẩu đúng, ngược lại trả None.

    Sai email và sai mật khẩu cho CÙNG kết quả (None) và tốn thời gian xấp xỉ nhau, để không ai
    dò được email nào có tài khoản. Email được so sánh theo chữ thường (seed lưu chữ thường).
    """
    result = await session.execute(
        select(Student).where(Student.email == email.strip().lower())
    )
    user = result.scalar_one_or_none()
    if user is None:
        await verify_password(password, await _get_dummy_hash())
        return None
    return user if await verify_password(password, user.password_hash) else None


async def get_user(session: AsyncSession, user_id: int) -> Student | None:
    result = await session.execute(select(Student).where(Student.id == user_id))
    return result.scalar_one_or_none()
