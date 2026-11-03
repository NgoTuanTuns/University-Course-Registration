# Bàn giao Tuần 2 — M4 (JWT & phân quyền)

**Dự án:** Hệ thống Đăng ký Học phần & Kiểm tra Điều kiện Tiên quyết
**Người bàn giao:** M4  |  **Căn cứ:** *Quy ước chung của nhóm* (Mục 5: `Authorization: Bearer`, mã lỗi `UNAUTHENTICATED`/`TOKEN_EXPIRED`/`FORBIDDEN`; Mục 2: `JWT_SECRET`, `ACCESS_TOKEN_TTL_MIN`, `REFRESH_TOKEN_TTL_DAYS`) và kế hoạch Tuần 2 của M4
**Nhận bàn giao:** M1 (đăng nhập), M2, M3 (bắt buộc đăng nhập cho router), M5 (CI, khởi động)

> **Không thêm biến môi trường nào** (dùng đúng 3 biến JWT đã có trong `.env.example`).

---

## 1. Tóm tắt

| Việc theo kế hoạch Tuần 2 | Trạng thái |
|---|---|
| `POST /auth/login` thật (bcrypt trong thread pool, lỗi chung chung, không lộ email tồn tại) | ✔ xong |
| JWT HS256: `sub, role, email, type, jti, iat, exp`; access 30 phút, refresh 7 ngày, không dùng thay nhau | ✔ xong |
| `get_current_user`: phân biệt `TOKEN_EXPIRED` và `UNAUTHENTICATED` | ✔ xong |
| `require_role("admin")`: sinh viên gọi chức năng admin → `403 FORBIDDEN` | ✔ xong |
| Xóa bản tạm `X-Debug-User` | ✔ đã xóa (không còn trong code) |
| Từ chối `JWT_SECRET` yếu ở `APP_ENV=prod` | ✔ có hàm; **M5 cần gọi lúc khởi động** (Mục 3) |
| Bắt buộc đăng nhập cho mọi router (trừ `/auth/*`, `/health`) | ◐ M4 cung cấp công cụ + test phát hiện; **chủ từng router tự thêm** (Mục 3) |
| `POST /auth/refresh` | ◐ làm bản cơ bản sớm cho M1 (chưa xoay vòng, xem Mục 5) |
| Chốt nơi lưu token ở frontend | Quy ước không quy định; tokens trả trong JSON, M1/nhóm chọn cách lưu |

---

## 2. Danh sách file (trong `backend/`)

**Mới:**

| File | Nội dung |
|---|---|
| `app/core/tokens.py` | Tạo/giải mã JWT (thuần PyJWT, không cần FastAPI/DB): `create_access_token`, `create_refresh_token`, `decode_token`, `get_secret`, `access_ttl_seconds` |
| `app/services/auth_service.py` | `authenticate`, `get_user` |
| `app/core/db.py` | **Bản tạm** `get_session` (xem Mục 3, M5) |
| `tests/test_tokens.py` | 17 test token (chạy không cần DB/FastAPI) |
| `tests/test_auth_api.py` | 17 test API: đăng nhập, refresh, 401/403, token hết hạn/sai chữ ký (cần fastapi + httpx) |
| `tests/test_auth_service.py` | 4 test đăng nhập với session giả |
| `tests/test_routes_require_login.py` | Duyệt **mọi route** của `app.main`, gọi không token, phải ra 401; liệt kê route quên bắt đăng nhập |
| `tests/auth_helpers.py` | `auth_headers(user_id, role)` để M2/M3/M5 test endpoint cần đăng nhập |

**Đã sửa:** `app/core/security.py` (bản thật thay bản tạm), `app/api/v1/auth.py` (login/refresh thật), `app/schemas/auth.py` (chỉ sửa chú thích).

---

## 3. Việc của từng người

### M1 — đăng nhập
- `POST /api/v1/auth/login`, body `{"email","password"}` → `200`:
  `{"access_token","refresh_token","token_type":"bearer","expires_in":1800,"user":{"id","email","full_name","role","mssv","max_credits"}}`
- Mọi request sau gửi `Authorization: Bearer <access_token>`.
- Lỗi: `401 UNAUTHENTICATED` (sai email *hoặc* mật khẩu, cùng một thông báo "Sai email hoặc mật khẩu"); `401 TOKEN_EXPIRED` (access token hết hạn → gọi `/auth/refresh`); `403 FORBIDDEN` (sai vai trò).
- `POST /auth/refresh`, body `{"refresh_token"}` → cùng dạng phản hồi như login (cặp token mới). Refresh token hết hạn/sai → `401 UNAUTHENTICATED` (đưa người dùng về trang đăng nhập).
- `max_credits` có sẵn trong `user` của phản hồi đăng nhập.

### M2, M3 — bắt buộc đăng nhập cho router của mình
```python
from fastapi import APIRouter, Depends
from app.core.security import CurrentUser, get_current_user

router = APIRouter(prefix="/enroll", dependencies=[Depends(get_current_user)])   # cả router phải đăng nhập

@router.post("")
async def enroll(body: EnrollRequest, user: CurrentUser = Depends(get_current_user)):   # cần biết là ai
    student_id = user.id
```
- **Bản tạm `X-Debug-User` đã bị xóa.** Test dùng token thật:
  ```python
  from tests.auth_helpers import auth_headers
  resp = await client.post("/api/v1/enroll", json={...}, headers=auth_headers(user_id=1))   # sv0001
  ```
  `user_id` phải khớp id trong DB (`sv000N` có `id = N`). Quản trị: `auth_headers(1001, "admin")` (admin có id lớn nhất sau seed).
- `tests/test_routes_require_login.py` sẽ **liệt kê route nào chưa bắt đăng nhập**. Route đó được tính là lỗi của chủ route.

### M5
1. **Gọi kiểm tra `JWT_SECRET` lúc khởi động** (để `APP_ENV=prod` mà dùng khóa mẫu/yếu thì app không chạy):
   ```python
   from app.core import tokens
   # trong lifespan/startup của main.py
   tokens.get_secret()      # ném RuntimeError nếu thiếu hoặc quá yếu ở prod
   ```
2. **`core/db.py`**: tôi đưa kèm **bản tạm** có `get_session`. Nếu repo đã có `core/db.py` của M5 thì **giữ bản của M5** (đừng ghi đè). Chỉ cần có hàm `get_session` trả `AsyncSession`; nếu M5 đặt tên khác, sửa một dòng import ở `api/v1/auth.py` và `tests/test_auth_api.py`.
3. **CI**: đặt `JWT_SECRET` (giá trị bất kỳ) trong môi trường test; `tests/auth_helpers.py` tự đặt giá trị mặc định nếu thiếu.
4. **pytest**: cần `pythonpath = .` (để `from app...` và `from tests.auth_helpers import ...` chạy được).
5. Gắn `auth.router` dưới `/api/v1` (nếu chưa).

---

## 4. Trạng thái kiểm chứng

### Đã chạy và đạt (trong sandbox)
- [x] 17 test token đạt: roundtrip, claim bắt buộc, TTL từ `.env`, `jti` duy nhất, hết hạn → `TokenExpiredError`, token ký bằng khóa khác → `InvalidTokenError`, rác, refresh dùng như access (và ngược lại), `alg=none`, thiếu claim, vai trò lạ, `sub` không phải số, thiếu `JWT_SECRET`, prod từ chối khóa mẫu/ngắn.
- [x] Chạy thật `get_current_user` và `require_role` với token thật (dùng bản giả của `fastapi`/`bcrypt`): **11/11 ca đúng**, gồm không header, `Basic`, `Bearer` rỗng, token rác, khóa khác, hết hạn → `TOKEN_EXPIRED`, refresh-như-access, hợp lệ (cả `bearer` chữ thường), student → 403, admin → được.
- [x] **Làm hỏng code cố ý, test có bắt không:** bỏ kiểm tra loại token ✔ bắt; bỏ kiểm tra vai trò ✔; hết hạn bị coi là sai ✔; TTL nhân nhầm ✔; prod cho phép khóa mẫu ✔. (Ca "nhận `alg=none`" không bị bắt vì chính PyJWT đã từ chối `none` khi có khóa; đây là lớp bảo vệ thứ hai, không phải lỗ hổng.)
- [x] 20 test dữ liệu mẫu của Tuần 1 vẫn đạt; mọi hàm ≤ 40 dòng; không `print`, không import thừa; cú pháp mọi file đúng.

### Cần xác nhận trên máy *(điền cột cuối)*

| # | Việc | Kết quả đúng | Đạt? |
|---|---|---|---|
| 1 | `pytest tests/test_tokens.py` | 17 passed | ☐ |
| 2 | `pytest tests/test_auth_api.py tests/test_auth_service.py` | 21 passed (cần `fastapi`, `httpx`, `bcrypt`, `pytest-asyncio`) | ☐ |
| 3 | Đăng nhập thật bằng tài khoản seed (Mục 6, kịch bản thử tay) | đúng bảng ở Mục 6 | ☐ |
| 4 | `pytest tests/test_routes_require_login.py` | skip nếu chưa có `app.main`; có thì liệt kê route chưa bắt đăng nhập | ☐ |
| 5 | `ruff format backend && ruff check backend` | sạch | ☐ |

> Mục 2–4 chưa chạy được trong sandbox (không có FastAPI, httpx, bcrypt, PostgreSQL). **Đừng đánh dấu bàn giao xong khi cột "Đạt?" chưa đủ.** Nếu test báo `ModuleNotFoundError: tests` thì thiếu `pythonpath = .`.

---

## 5. Giới hạn đã biết (nói trước)

1. **`/auth/refresh` chưa xoay vòng, chưa thu hồi:** refresh token đã cấp còn dùng được đến khi hết hạn (7 ngày). Xoay vòng + phát hiện dùng lại bằng Redis là **Tuần 3**; dạng phản hồi giữ nguyên nên M1 không phải sửa.
2. **Chưa có rate-limit đăng nhập** (Tuần 3): hiện chưa chặn được dò mật khẩu hàng loạt.
3. **Vai trò và email lấy từ token**, không tra DB mỗi request: đổi vai trò một người có hiệu lực sau tối đa 30 phút (khi access token hết hạn). Riêng `/auth/refresh` có tra lại DB.
4. **Email so khớp theo chữ thường** (seed lưu chữ thường). Tài khoản mới sau này cũng phải lưu chữ thường.
5. **`core/db.py` là bản tạm** (không phải việc của M4); M5 thay bằng bản chính thức.
6. **Frontend lưu token ở đâu** quy ước chưa nêu; token đang trả trong JSON body nên chọn cách nào cũng được. Nếu M1 lưu trong `localStorage` thì chịu rủi ro XSS: nên ghi vào báo cáo bảo mật ở Tuần 5.
7. Chưa chạy `ruff` (không có trong sandbox).

---

## 6. Thử tay trên máy bạn (sau khi đã `alembic upgrade head` và `python -m app.seed`)

Tạo `backend/dev_main.py` (chỉ để thử, **không commit**):
```python
from fastapi import Depends, FastAPI
from app.api.v1 import auth
from app.core.security import CurrentUser, get_current_user, require_role

app = FastAPI()
app.include_router(auth.router, prefix="/api/v1")

@app.get("/whoami")
async def whoami(user: CurrentUser = Depends(get_current_user)): return user

@app.get("/admin-only")
async def admin_only(user: CurrentUser = Depends(require_role("admin"))): return user
```
```powershell
$env:DATABASE_URL = "postgresql+asyncpg://course_user:doi_mat_khau_nay@localhost:5433/course_reg"
$env:JWT_SECRET   = "doi_thanh_chuoi_bat_ky_dai_mot_chut"
uvicorn dev_main:app --port 8000
```
Mở http://localhost:8000/docs và thử theo bảng:

| Thao tác | Kết quả đúng |
|---|---|
| `POST /api/v1/auth/login` với `sv0001@uni.edu.vn` / `Student@123` | 200, có `access_token`, `user.role = student`, **không có** `password_hash` |
| Login sai mật khẩu; login email không tồn tại | cả hai `401` với **cùng** thông báo "Sai email hoặc mật khẩu" |
| `GET /whoami` không có header | `401 UNAUTHENTICATED` |
| `GET /whoami` với `Authorization: Bearer <access_token>` | 200, `id = 1`, `role = student` |
| `GET /admin-only` với token của sinh viên | `403 FORBIDDEN` |
| Login `admin@uni.edu.vn` / `Admin@123` rồi `GET /admin-only` | 200 |
| `GET /whoami` với **refresh_token** thay access_token | `401 UNAUTHENTICATED` |
| `POST /auth/refresh` với refresh_token | 200, cặp token mới |
| Đặt `ACCESS_TOKEN_TTL_MIN=1`, đợi 61 giây, gọi `/whoami` | `401 TOKEN_EXPIRED` |

---

## 7. Gợi ý commit (một việc một commit)

```text
Thêm module tokens tạo và kiểm tra JWT access/refresh
Thêm service đăng nhập authenticate và get_user
Thay get_current_user tạm bằng bản đọc JWT, xóa X-Debug-User
Thêm /auth/login và /auth/refresh thật
Thêm core/db.py tạm cung cấp get_session
Thêm test token, API xác thực và tiện ích auth_headers
Thêm test kiểm tra mọi route phải đăng nhập
```

---

## 8. Việc tiếp theo của M4 (Tuần 3)

- [ ] **Refresh token xoay vòng** lưu Redis `refresh:{student_id}:{jti}`; phát hiện dùng lại refresh token → thu hồi phiên (**làm trước**: M1 cần cho luồng hết phiên)
- [ ] `/admin/courses` (CRUD; trùng mã, xóa học phần đang được tham chiếu trả lỗi rõ) — M1 làm trang admin ở Tuần 4
- [ ] **Rate-limit** bằng Redis: đăng nhập chặt theo (IP, email), API theo người dùng; có chế độ nới cho môi trường tải
- [ ] Khóa Redis mới (`refresh:*`, `ratelimit:*`) cần được **thêm vào Mục 7 quy ước** khi làm
- [ ] Hồ sơ seed cho kiểm thử tải (nếu nhóm đồng ý làm ở Tuần 3)

---

## 9. Điều kiện coi là "bàn giao xong Tuần 2"

- [ ] Cột "Đạt?" ở Mục 4 đã đủ ✔
- [ ] PR đã được M3 đọc qua (vòng review M3 → M4) và merge vào `main`
- [ ] M2 và M3 đã thay mọi chỗ dùng `X-Debug-User` bằng `auth_headers`
- [ ] M5 đã gọi `tokens.get_secret()` lúc khởi động và cấu hình `pythonpath = .`
- [ ] Router của M2, M3 đã có `Depends(get_current_user)` (test ở Mục 4 #4 không còn liệt kê route nào)
