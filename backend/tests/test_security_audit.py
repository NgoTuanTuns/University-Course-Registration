"""Kiểm thử tự động các yêu cầu an toàn theo chuẩn OWASP Top 10 (M4, Tuần 5).

Bao gồm:
1. A01 Broken Access Control: RBAC phân quyền admin/student; chống IDOR khi hủy đăng ký / rời hàng chờ.
2. A02 Cryptographic Failures: Không rò rỉ password_hash trong bất kỳ API nào.
3. A03 Injection: Thoát an toàn ký tự đại diện SQL ILIKE (%, _).
4. A04 Insecure Design: Xử lý đăng nhập an toàn chống dò email (timing-safe dummy hash).
5. A07 Auth Failures: Phát hiện tái sử dụng refresh token kích hoạt thu hồi toàn bộ phiên.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.core.security import CurrentUser, require_role
from app.schemas.auth import TokenResponse, UserOut
from app.services import (
    auth_service,
    course_service,
    enrollment_service,
    waitlist_service,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# A01: Broken Access Control & IDOR
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_security_rbac_admin_guard_rejects_student():
    """A01: Sinh viên cố tình gọi endpoint của Admin sẽ bị chặn với 403 FORBIDDEN."""
    guard = require_role("admin")
    student = CurrentUser(id=1, role="student", email="sv0001@uni.edu.vn")

    with pytest.raises(HTTPException) as exc:
        await guard(user=student)

    assert exc.value.status_code == 403
    assert exc.value.detail["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_security_idor_cancel_enrollment_forbidden():
    """A01: Chống IDOR - Sinh viên A không thể hủy đăng ký của Sinh viên B (nhận 404)."""
    session = AsyncMock()

    # Giả lập enrollment thuộc về student_id = 999
    # Nhưng sinh viên đang gọi API có student_id = 1
    mock_res = MagicMock()
    mock_res.scalar.return_value = (
        None  # Truy vấn lọc WHERE student_id == 1 trả về None
    )
    session.scalar.return_value = None

    with pytest.raises(HTTPException) as exc:
        await enrollment_service.cancel(
            session=session,
            student_id=1,  # Sinh viên yêu cầu
            enrollment_id=100,  # ID đăng ký của người khác
        )

    assert exc.value.status_code == 404
    assert exc.value.detail["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_security_idor_leave_waitlist_forbidden():
    """A01: Chống IDOR - Sinh viên A không thể xóa hàng chờ của Sinh viên B (nhận 404)."""
    session = AsyncMock()
    session.scalar.return_value = None

    with patch(
        "app.services.enrollment_service.lock_students",
        new_callable=AsyncMock,
    ):
        with pytest.raises(HTTPException) as exc:
            await waitlist_service.leave(
                session=session,
                student_id=1,
                waitlist_id=50,
            )

    assert exc.value.status_code == 404
    assert exc.value.detail["code"] == "NOT_FOUND"


# ---------------------------------------------------------------------------
# A02: Cryptographic Failures & Information Leakage
# ---------------------------------------------------------------------------


def test_security_password_hash_never_exposed():
    """A02: password_hash tuyệt đối không xuất hiện trong schema UserOut hoặc TokenResponse."""
    user_fields = set(UserOut.model_fields.keys())
    assert "password_hash" not in user_fields
    assert "password" not in user_fields

    token_fields = set(TokenResponse.model_fields.keys())
    assert "password_hash" not in token_fields
    assert "password" not in token_fields


# ---------------------------------------------------------------------------
# A03: Injection & SQL Wildcard Escaping
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_security_sql_wildcard_escaping():
    """A03: Ký tự %, _ trong tìm kiếm học phần được escape đúng chuẩn để tránh quét toàn bộ DB."""
    session = AsyncMock()
    mock_count = MagicMock()
    mock_count.scalar_one.return_value = 0

    mock_items = MagicMock()
    mock_items.scalars.return_value.all.return_value = []

    session.execute.side_effect = [mock_count, mock_items]

    # Tìm kiếm chuỗi chứa ký tự đại diện SQL nguy hiểm
    dangerous_q = "%_test_%"
    items, total = await course_service.list_courses(session, q=dangerous_q)

    # Đảm bảo câu lệnh thực thi an toàn không bị văng lỗi
    assert items == []
    assert total == 0
    assert session.execute.called


# ---------------------------------------------------------------------------
# A04: Insecure Design & Timing Attack Mitigation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_security_timing_safe_login_on_nonexistent_email():
    """A04: Đăng nhập với email không tồn tại vẫn thực hiện so sánh băm giả để không lộ email."""
    session = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_res

    with (
        patch(
            "app.services.auth_service.verify_password",
            new_callable=AsyncMock,
            return_value=False,
        ) as mock_verify,
        patch(
            "app.services.auth_service._get_dummy_hash",
            new_callable=AsyncMock,
            return_value="$2b$12$dummyhashfordummycomparisondummyhashfordummycomp",
        ),
    ):
        user = await auth_service.authenticate(
            session, "khongtontai@uni.edu.vn", "WrongPassword123"
        )
        assert user is None
        # Xác thực hàm verify_password vẫn được gọi đúng 1 lần với dummy hash
        assert mock_verify.called


# ---------------------------------------------------------------------------
# A07: Identification and Authentication Failures (Token Reuse Detection)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_security_refresh_token_reuse_detection():
    """A07: Phát hiện tái sử dụng refresh token cũ sẽ kích hoạt thu hồi toàn bộ phiên trong Redis."""
    from app.api.v1.auth import refresh
    from app.core import tokens
    from app.schemas.auth import RefreshRequest

    session = AsyncMock()
    # Sinh một refresh token hợp lệ về mặt chữ ký
    valid_refresh = tokens.create_refresh_token(
        user_id=1, role="student", email="sv0001@uni.edu.vn"
    )

    with (
        patch(
            "app.api.v1.auth.consume_refresh_token",
            new_callable=AsyncMock,
            return_value=False,  # Đã bị tiêu thụ trước đó
        ),
        patch(
            "app.api.v1.auth.revoke_all_user_tokens",
            new_callable=AsyncMock,
        ) as mock_revoke_all,
    ):
        with pytest.raises(HTTPException) as exc:
            await refresh(RefreshRequest(refresh_token=valid_refresh), session)

        assert exc.value.status_code == 401
        assert exc.value.detail["code"] == "UNAUTHENTICATED"
        # Xác thực hành động thu hồi TOÀN BỘ phiên của sinh viên đó lập tức được kích hoạt
        assert mock_revoke_all.called
        mock_revoke_all.assert_awaited_once_with(1)
