# Bàn giao Tuần 3 — M4 (Xoay vòng Refresh Token, Rate-limit & API Quản trị Học phần)

**Dự án:** Hệ thống Đăng ký Học phần & Kiểm tra Điều kiện Tiên quyết  
**Người bàn giao:** M4  |  **Ngày bàn giao:** 03/11/2026  
**Căn cứ:** *Quy ước chung của nhóm* (Mục 3, Mục 5, Mục 7) và kế hoạch Tuần 3 của M4 (*M4_cong_viec_7_tuan.md*)  
**Nhận bàn giao:** M1 (làm trang quản trị học phần ở Tuần 4 & tích hợp refresh token), M2, M3 (tầng service/router), M5 (Redis & CI)

---

## 1. Tóm tắt công việc hoàn thành

Tuần 3 của M4 tập trung vào 3 trọng tâm chính theo đúng kế hoạch:

1. **Xoay vòng Refresh Token (Token Rotation) & Phát hiện dùng lại (Reuse Detection):**
   - Refresh token được cấp kèm `jti` duy nhất và lưu trạng thái trong Redis (`refresh:{student_id}:{jti}`, TTL = 7 ngày).
   - Mỗi refresh token chỉ được dùng **1 lần duy nhất**: khi gọi `POST /api/v1/auth/refresh`, token cũ lập tức bị thu hồi và một cặp access/refresh token mới được cấp.
   - **Phát hiện tái sử dụng (Reuse Detection):** Nếu một refresh token đã bị tiêu thụ hoặc đã bị thu hồi mà lại được gửi lại, hệ thống nhận diện đây là hành vi đánh cắp token và **lập tức thu hồi TOÀN BỘ phiên đăng nhập** của sinh viên đó trong Redis, trả về `401 UNAUTHENTICATED`.
   - **Đăng xuất (`POST /api/v1/auth/logout`):** Hỗ trợ thu hồi refresh token khỏi Redis để kết thúc phiên an toàn.
   - Khi Redis gặp sự cố: Từ chối refresh an toàn (fail-safe) nhưng không làm sập các API khác dùng access token còn hạn.

2. **Giới hạn tần suất (Rate Limiting) bằng Redis:**
   - Cơ chế bộ đếm nguyên tử qua script Lua (`INCR` + `EXPIRE`).
   - Khóa Redis theo đúng quy ước: `ratelimit:{phạm vi}:{định danh}`.
   - Chặn dò mật khẩu nghiêm ngặt tại `POST /api/v1/auth/login` theo `(IP, email)` (ngưỡng 5 lần/phút).
   - Khi vượt ngưỡng: Trả về HTTP `429` với mã lỗi chuẩn `RATE_LIMITED` và tiêu đề HTTP `Retry-After: <số giây>`.
   - Tự động bỏ qua rate-limit khi chạy tải với `APP_ENV=loadtest` hoặc cấu hình `RATE_LIMIT_ENABLED=false` để không ảnh hưởng spike test 2.000 sinh viên của M5.
   - Phân giải IP chính xác ưu tiên tiêu đề Nginx (`X-Forwarded-For`, `X-Real-IP`).
   - Khi Redis gặp sự cố: Tự động cho qua và ghi log cảnh báo (ưu tiên tính khả dụng hệ thống).

3. **Bộ API Quản trị Học phần (`/api/v1/admin/courses`):**
   - Phân quyền nghiêm ngặt: Toàn bộ router được bảo vệ bằng `require_role("admin")`. Sinh viên gọi đến nhận `403 FORBIDDEN`.
   - `GET /api/v1/admin/courses`: Phân trang (`page`, `page_size`), tìm kiếm từ khóa theo mã hoặc tên học phần.
   - `GET /api/v1/admin/courses/{id}`: Chi tiết học phần (404 `NOT_FOUND` nếu không tồn tại).
   - `POST /api/v1/admin/courses`: Tạo học phần mới, kiểm tra trùng mã học phần (409 `ALREADY_EXISTS`), kiểm tra số tín chỉ 1–10.
   - `PUT /api/v1/admin/courses/{id}`: Cập nhật thông tin học phần.
   - `DELETE /api/v1/admin/courses/{id}`: Xóa học phần an toàn. **Kiểm tra ràng buộc tham chiếu toàn vẹn**: Nếu học phần đang có lớp học phần mở, có trong bảng điểm sinh viên hoặc là điều kiện tiên quyết của môn khác thì từ chối xóa và trả `409 IN_USE` kèm danh sách chi tiết lý do (tránh lỗi 500 khóa ngoại DB). Xóa thành công sẽ tự động dọn cache `prereq:*` trong Redis.

---

## 2. Danh sách file bàn giao (trong `backend/`)

### File mới:
| File | Nội dung | Ai dùng |
|---|---|---|
| `app/core/errors.py` | Hàm tạo `api_error` chuẩn hóa cấu trúc `{ detail: { code, message, ... } }` | Toàn bộ backend |
| `app/core/redis.py` | Kết nối Redis async, lưu/thu hồi refresh token, phát hiện tái sử dụng | M4, M5, M2, M3 |
| `app/core/rate_limit.py` | Middleware & hàm kiểm tra rate limit bằng Lua script Redis, xử lý IP và header `Retry-After` | M4, các router |
| `app/schemas/course.py` | Schema dữ liệu vào/ra cho học phần và phân trang admin | M1 (làm UI), M4 |
| `app/services/course_service.py` | Nghiệp vụ quản trị học phần: tìm kiếm, tạo mới, kiểm tra trùng mã, kiểm tra tham chiếu `IN_USE` | Router admin |
| `app/api/v1/admin.py` | Router `/admin/courses` đầy đủ CRUD bảo vệ bằng quyền admin | M1 (kết nối UI) |
| `tests/auth_helpers.py` | Tiện ích `auth_headers(user_id, role)` sinh token test cho cả nhóm | M1, M2, M3, M5 |
| `tests/test_refresh_rotation.py` | 5 bài test xoay vòng refresh token, thu hồi khi logout, phát hiện dùng lại | M4, M5 (CI) |
| `tests/test_rate_limit.py` | 6 bài test kiểm tra rate-limit, 429 Retry-After, bypass loadtest, phân giải IP | M4, M5 (CI) |
| `tests/test_admin_courses.py` | 6 bài test CRUD học phần, 409 ALREADY_EXISTS, 409 IN_USE, phân quyền 403 | M4, M5 (CI) |

### File đã cập nhật:
| File | Nội dung cập nhật |
|---|---|
| `app/core/db.py` | Đã hợp nhất tinh hoa của `database.py` và `db.py`, chuẩn hóa lazy session, xóa bỏ file thừa `database.py` |
| `app/core/security.py` | Chuẩn hóa import `api_error` từ `app.core.errors` |
| `app/schemas/auth.py` | Bổ sung `MessageResponse` phục vụ API đăng xuất |
| `app/api/v1/auth.py` | Tích hợp rate-limit ở `/login`, tích hợp xoay vòng + phát hiện dùng lại ở `/refresh`, thêm endpoint `/logout` |
| `app/api/v1/prerequisites.py` | Chuẩn hóa import session từ `app.core.db` |

---

## 3. Hướng dẫn sử dụng cho từng thành viên

### 3.1 Dành cho M1 (Frontend Engineer)
1. **Trang Quản trị Học phần (bắt đầu ở Tuần 4):**
   - Đã sẵn sàng các endpoint tại `/api/v1/admin/courses`. Nhớ gửi kèm header `Authorization: Bearer <access_token>` của tài khoản admin.
   - Danh sách: `GET /api/v1/admin/courses?q=...&page=1&page_size=20` → trả về `{ items: [...], total, page, page_size }`.
   - Tạo học phần: `POST /api/v1/admin/courses` body `{"code": "INT131", "name": "...", "credits": 3, "description": "..."}`. Trùng mã trả `409` code `ALREADY_EXISTS`.
   - Xóa học phần: `DELETE /api/v1/admin/courses/{id}`. Nếu môn đang có lớp hoặc là tiên quyết của môn khác, API trả `409` code `IN_USE` kèm mảng `references: [...]` — frontend có thể hiển thị cảnh báo chi tiết lý do không thể xóa cho admin.
2. **Cơ chế Refresh Token tự động:**
   - Khi API bất kỳ trả về `401 TOKEN_EXPIRED`, frontend gọi `POST /api/v1/auth/refresh` với body `{"refresh_token": "..."}`.
   - Nhận về cặp token mới (cả access token và refresh token mới). **Cập nhật lại cả 2 token** vì refresh token cũ đã bị hủy.
   - Nếu nhận `401 UNAUTHENTICATED`, nghĩa là refresh token đã hết hạn hoặc bị nghi ngờ dùng lại -> chuyển người dùng về trang đăng nhập.
3. **Đăng xuất:**
   - Gọi `POST /api/v1/auth/logout` với body `{"refresh_token": "..."}` để server hủy phiên trong Redis, sau đó xóa token ở client.
4. **Xử lý mã lỗi `429 RATE_LIMITED`:**
   - Khi thử đăng nhập sai quá 5 lần/phút, server trả HTTP 429 kèm header `Retry-After: <giây>`. Frontend đọc header này và hiển thị đếm ngược thời gian chờ.

### 3.2 Dành cho M2 & M3 (Backend Services & Routers)
- **Kiểm tra quyền / Dependency:** Dùng `from app.core.security import get_current_user, require_role, CurrentUser`.
- **Database session:** Dùng `from app.core.db import get_session`. Không tự ý commit trong `get_session`, tầng service quyết định commit.
- **Tiện ích test:** Dùng `from tests.auth_helpers import auth_headers` để sinh header xác thực cho sinh viên (`role="student"`) hoặc admin (`role="admin"`).

### 3.3 Dành cho M5 (DevOps, CI & Infra)
1. **Khóa Redis bổ sung (cập nhật Mục 7 quy ước):**
   - `refresh:{student_id}:{jti}`: TTL 7 ngày (604.800 giây).
   - `ratelimit:{phạm vi}:{định danh}`: TTL theo cửa sổ cấu hình (mặc định 60 giây).
2. **Biến môi trường hỗ trợ test tải:**
   - Thêm vào môi trường chạy Locust: `APP_ENV=loadtest` hoặc `RATE_LIMIT_ENABLED=false` để rate-limit không chặn nhầm 2.000 virtual users.

---

## 4. Trạng thái kiểm chứng & Test Suite

- **Bộ test cơ sở (Models metadata, Prerequisite Engine, Seed Data):**
  - Đã chạy: `python -m pytest backend/tests/test_models_metadata.py backend/tests/test_prerequisite_engine.py backend/tests/test_seed_data.py`
  - Kết quả: **58/58 passed (100%)**.
- **Bộ test mới của Tuần 3:**
  - `backend/tests/test_rate_limit.py`: Kiểm tra rate-limit, 429 Retry-After, nhận diện IP, bypass loadtest.
  - `backend/tests/test_refresh_rotation.py`: Kiểm tra xoay vòng single-use, phát hiện dùng lại (thu hồi toàn bộ phiên), logout, fail-safe khi Redis sự cố.
  - `backend/tests/test_admin_courses.py`: Kiểm tra CRUD học phần, chặn trùng mã 409 `ALREADY_EXISTS`, chặn xóa môn đang dùng 409 `IN_USE`, chặn sinh viên gọi 403 `FORBIDDEN`.

---

## 5. Kịch bản thử nghiệm trực tiếp (Manual Verification)

### Bước 1: Khởi động hệ thống
```bash
docker compose up --build -d
docker compose exec api alembic upgrade head
docker compose exec api python -m app.seed
```

### Bước 2: Thử nghiệm Rate-limit Đăng nhập
- Dùng Postman hoặc curl gửi 6 request liên tiếp sai mật khẩu tới `POST /api/v1/auth/login`:
  - 5 request đầu: trả về `401 UNAUTHENTICATED` ("Sai email hoặc mật khẩu").
  - Request thứ 6: trả về `429` với body `{"detail": {"code": "RATE_LIMITED", "message": "Quá nhiều yêu cầu, vui lòng thử lại sau"}}` và header `Retry-After`.

### Bước 3: Thử nghiệm Xoay vòng & Phát hiện Tái sử dụng Refresh Token
1. Đăng nhập thành công tài khoản sinh viên `sv0001@uni.edu.vn` → nhận `access_token` và `refresh_token_1`.
2. Gọi `POST /api/v1/auth/refresh` với `refresh_token_1` → nhận cặp token mới (`access_token_2`, `refresh_token_2`).
3. Gửi lại `refresh_token_1` lần nữa → nhận `401 UNAUTHENTICATED` và kiểm tra Redis thấy mọi key `refresh:1:*` của sinh viên đó đều đã bị xóa sạch (toàn bộ phiên bị thu hồi).

### Bước 4: Thử nghiệm API Quản trị Học phần (`/api/v1/admin/courses`)
1. Dùng token của sinh viên gọi `GET /api/v1/admin/courses` → nhận ngay `403 FORBIDDEN`.
2. Dùng token của admin (`admin@uni.edu.vn`) gọi `POST /api/v1/admin/courses` tạo môn `INT999` → thành công `201`.
3. Thử `DELETE /api/v1/admin/courses/1` (môn INT131 đã có lớp và sinh viên học) → nhận `409` code `IN_USE` kèm danh sách tham chiếu.
4. Thử `DELETE` môn `INT999` vừa tạo → thành công `200`.
