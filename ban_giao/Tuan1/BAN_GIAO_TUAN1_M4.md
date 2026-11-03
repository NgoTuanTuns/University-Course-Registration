# Bàn giao Tuần 1 — M4 (CSDL & quản lý phiên)

**Dự án:** Hệ thống Đăng ký Học phần & Kiểm tra Điều kiện Tiên quyết
**Người bàn giao:** M4  |  **Ngày:** 21/10/2026  |  **Căn cứ:** *Quy ước chung của nhóm* (Mục 3, 4, 6, 7) và kế hoạch Tuần 1 của M4
**Nhận bàn giao:** M2, M3, M5 (dùng ngay), M1 (dùng làm mock)

---

## 1. Tóm tắt

Tuần 1 của M4 giao **nền tảng dữ liệu** để cả nhóm dùng chung một database:

1. **Models** đủ 7 bảng, đúng nguyên văn DDL ở Mục 6 quy ước.
2. **Migration Alembic** `0001_initial` tạo 7 bảng.
3. **Dữ liệu mẫu** chạy bằng `python -m app.seed`: 200 học phần, 1.000 sinh viên, đủ các ca đặc biệt theo quy ước.
4. **Khung xác thực** để M2/M3 viết code trước khi JWT thật xong (Tuần 2).
5. **Schema + router `/auth`** trả dữ liệu mẫu để M1 làm mock.

> **Chưa có:** đăng nhập thật bằng JWT, refresh token, rate-limit, API quản trị. Đó là việc Tuần 2–4.

---

## 2. Danh sách bàn giao

| File (trong `backend/`) | Nội dung | Ai dùng |
|---|---|---|
| `app/models/*.py` (9 file) | 7 model SQLAlchemy, mỗi bảng một file, `naming_convention` cố định | M2, M3, M5 |
| `alembic.ini`, `alembic/env.py`, `alembic/script.py.mako` | Cấu hình Alembic bất đồng bộ, đọc `DATABASE_URL` | M5 (CI) |
| `alembic/versions/0001_initial.py` | Migration đầu tiên (viết tay, xem Mục 6) | cả nhóm |
| `app/seed_data.py` | Sinh dữ liệu mẫu thuần Python, kèm hàm kiểm tra nhất quán | M2, M3, M5 (làm dữ liệu test) |
| `app/seed.py` | Nạp dữ liệu vào PostgreSQL | cả nhóm |
| `app/core/security.py` | `CurrentUser`, `get_current_user`, `require_role`, `hash_password`, `verify_password` | M2, M3 |
| `app/schemas/auth.py`, `app/api/v1/auth.py` | `POST /auth/login`, `POST /auth/refresh` trả JSON mẫu | M1 |
| `tests/test_seed_data.py` | 20 test cho dữ liệu mẫu (không cần DB) | M5 |
| `tests/test_models_metadata.py` | 7 test kiểm tra models khớp DDL (không cần DB) | M5 |
| `tests/sql/verify_constraints.sql` | 11 khối SQL kiểm tra DB tự chặn dữ liệu sai | M4, M5 |

---

## 3. Cách dùng cho từng người

### Tất cả: dựng database có dữ liệu
```bash
docker compose up --build
docker compose exec api alembic upgrade head
docker compose exec api python -m app.seed            # thêm --reset để làm lại từ đầu
```
- `--profile minimal`: chỉ bộ ca đặc biệt (55 tài khoản, 20 học phần), dùng cho test.
- Seed lần 2 khi DB đã có dữ liệu sẽ báo lỗi và thoát; dùng `--reset` để nạp lại.
- Seed xóa các khóa Redis `prereq:*` sau khi nạp (đúng Mục 7 quy ước); Redis chưa chạy thì chỉ cảnh báo.

### M2 (tiên quyết)
- Dùng models `Course`, `Prerequisite`, `CompletedCourse` (`from app.models import ...`).
- Dữ liệu mẫu đã có sẵn chuỗi bắc cầu, nhóm "hoặc", hình thoi (xem Mục 4) để thử engine ngay.
- `completed_courses` của mọi sinh viên **đóng theo tiên quyết** (ai đã học Y thì đã học các môn Y cần), nên kết quả không phụ thuộc cách hiểu "bắc cầu" khi dùng dữ liệu này.
- Cache `prereq:*` do M2 quản lý; seed chỉ xóa khóa này sau khi nạp.

### M3 (đăng ký, waitlist)
- Models `Enrollment`, `Waitlist`, `CourseOffering` đã có. **M4 viết `enrollment.py` và `waitlist.py` từ DDL; M3 vui lòng xem lại và sửa trực tiếp nếu cần (đừng tạo bản trùng).**
- Dữ liệu mẫu đã có lớp **sắp đầy**, lớp **đầy + hàng chờ**, lớp **chỉ 1 chỗ**, hai lớp **trùng lịch**, hai lớp **liền kề** để viết test tranh suất và trùng lịch.
- Ngày học: `day` 1 = Thứ Hai … 7 = Chủ nhật; giờ nằm trong 07:00–21:00.

### M5 (hạ tầng, test)
- Cần gắn router: `app.include_router(auth.router, prefix="/api/v1")`.
- Cần tạo database `course_reg_test` (Quy ước Mục 2) và thêm `alembic upgrade head` vào CI.
- Thêm `pythonpath = .` vào cấu hình pytest nếu test báo không import được `app`.
- Thư viện cần có trong `requirements.txt`: `sqlalchemy[asyncio]>=2.0`, `asyncpg`, `alembic`, `bcrypt`, `fastapi`, `pydantic>=2`, `redis`.
- Có thể dùng `build_dataset("minimal")` trong `app/seed_data.py` làm dữ liệu test mà không cần DB.

### M1 (frontend)
- `POST /auth/login` và `POST /auth/refresh` đang trả **JSON mẫu** (chưa thật). Định dạng khi làm thật sẽ giữ nguyên; xem `app/schemas/auth.py`.
- Dùng được các tài khoản mẫu ở Mục 4 để dựng giao diện.

### M2/M3 khi chưa có JWT
Với `APP_ENV=dev`, gửi header `X-Debug-User: <id>:<student|admin>` (ví dụ `1:student`, `1001:admin`) để dùng `get_current_user`/`require_role`. **Đây là bản tạm và sẽ bị xóa cuối Tuần 2** khi JWT thật xong.

---

## 4. Dữ liệu mẫu

**Số dòng sau khi seed:**

| profile | sinh viên (+admin) | học phần | tiên quyết | lớp | đã học | đăng ký | hàng chờ |
|---|---|---|---|---|---|---|---|
| `default` | 1.001 | 200 | 338 | 357 | 12.668 | 53 | 3 |
| `minimal` | 55 | 20 | 15 | 20 | 132 | 53 | 3 |

**Tài khoản:** admin `admin@uni.edu.vn` / `Admin@123`; sinh viên `svNNNN@uni.edu.vn` / `Student@123` (mssv `SVNNNN`; `sv000N` có `id = N`). Chỉ dùng cho dữ liệu mẫu.

| Tài khoản | Tình huống |
|---|---|
| `sv0001` | Đủ điều kiện học `INT341` |
| `sv0002` | Chỉ học `INT101`: muốn `INT431` thì thiếu `INT331, INT231, INT131` (**bắc cầu**) |
| `sv0003` | Đủ `INT231`, thiếu **nhóm "hoặc"** `MAT201`/`MAT202` của `INT341` |
| `sv0004` | Đang đăng ký 8 lớp = 24 tín chỉ → thêm `INT221-01` sẽ **vượt 25 tín chỉ** |
| `sv0005` | Đang học `INT221-01` → `INT222-01` bị **trùng lịch**; `MAT201-01` **liền kề** nên hợp lệ |
| `sv0006`–`sv0008` | Trong **hàng chờ** `INT331-01` (vị trí 1, 2, 3) |
| `sv0009`, `sv0010` | Cùng đủ điều kiện `INT341-01` (lớp **chỉ 1 chỗ**): thử tranh suất |
| `sv0011`–`sv0025` | Đang học `INT331-01` (lớp **đầy** 15/15); `sv0011` hủy thì `sv0006` được đôn |
| `sv0026`–`sv0054` | Đang học `INT231-01` (lớp **sắp đầy** 29/30) |

**Học phần đặc biệt:** `INT101→INT131→INT231→INT331→INT431` (chuỗi 5 tầng); `INT321` cần `INT221` và `INT222` (hình thoi); `INT341` cần `INT231` + một trong {`MAT201`, `MAT202`}; `INT451` có hai nhóm "hoặc". Các lớp đặc biệt đều có mã `-01`.

**Dữ liệu luôn nhất quán** (có test): `enrolled_count` = số đăng ký `ACTIVE`; `position` hàng chờ liên tục từ 1; không có vòng lặp tiên quyết; không ai vượt tín chỉ hay trùng lịch.

---

## 5. Trạng thái kiểm chứng

### Đã kiểm chứng tự động (không cần database)
- [x] 20 test dữ liệu mẫu đạt: nhất quán 2 profile; 200 học phần / 1.000 sinh viên; DAG sâu ≥ 7 tầng; không vòng lặp; từng tình huống ở Mục 4; tính tái lập.
- [x] Làm hỏng dữ liệu cố ý (vòng lặp, `enrolled_count` lệch, thiếu tiên quyết, lịch ngoài khung giờ, `position` nhảy cóc, trùng email, vượt tín chỉ, vừa đăng ký vừa chờ…) thì hàm kiểm tra đều báo lỗi.
- [x] DDL khớp quy ước: đúng 12 `CHECK`, 7 index, 5 `ON DELETE CASCADE`; tên cột, `CHECK`, `UNIQUE`, index giữa models và migration giống nhau.
- [x] Mọi hàm ≤ 40 dòng; không còn `print`; không import thừa; cú pháp mọi file đúng.

### M4 cần xác nhận trên máy trước khi gửi PR *(điền kết quả vào cột cuối)*

| # | Việc | Kết quả đúng | Đạt? |
|---|---|---|---|
| 1 | `pytest tests/test_seed_data.py tests/test_models_metadata.py` | 27 passed | ☐ |
| 2 | `alembic upgrade head` | không lỗi, có 7 bảng + `alembic_version` | ☐ |
| 3 | `alembic downgrade base` rồi `upgrade head` | cả hai không lỗi | ☐ |
| 4 | `alembic check` | "No new upgrade operations detected" | ☐ |
| 5 | `python -m app.seed` | số dòng khớp bảng ở Mục 4 | ☐ |
| 6 | `verify_constraints.sql` | 11 dòng `OK` + "Tất cả ràng buộc hoạt động đúng" | ☐ |
| 7 | `alembic revision --autogenerate -m "so_sanh"` | `upgrade()` chỉ có `pass` (rồi xóa file đó) | ☐ |
| 8 | `ruff format backend` và `ruff check backend` | sạch | ☐ |

> Các mục 1–7 chưa được chạy trong môi trường có PostgreSQL khi viết bản giao này. **Đừng đánh dấu "bàn giao xong" cho nhóm trước khi cột "Đạt?" đủ.**

---

## 6. Điểm lưu ý

1. **Migration viết tay**, không dùng `--autogenerate` như quy ước vì lúc viết không có database. Kiểm lại bằng mục 7 ở bảng trên.
2. **Hai model do M4 viết thay M3:** `enrollment.py`, `waitlist.py` (M3 xem lại).
3. **Chưa chạy được ruff** khi viết; dòng dài nhất ~158 ký tự nên `ruff format` sẽ xuống dòng lại nhiều chỗ (chỉ đổi cách trình bày).
4. **`BCRYPT_ROUNDS = 12`** là hằng số trong `core/security.py`. Muốn lấy từ `.env` thì thêm biến vào `.env.example` cùng lúc.
5. **`core/security.py` có `try/except ImportError`** cho `app.core.errors` của M5; xóa khối này khi M5 đã đẩy `core/errors.py`.
6. **Windows:** `alembic.ini` và `verify_constraints.sql` chỉ được chứa ký tự ASCII (không dấu), nếu không sẽ lỗi `UnicodeDecodeError: 'charmap'`.
7. **`X-Debug-User`** chỉ hoạt động khi `APP_ENV=dev`; tuyệt đối không dùng ở môi trường khác. Xóa cuối Tuần 2.

---

## 7. Việc cần người khác làm để Tuần 1 khép lại

| Ai | Việc | Hạn đề xuất |
|---|---|---|
| **M3** | Xem lại `models/enrollment.py`, `models/waitlist.py`; review PR của M4 (vòng review M3 xem M4) | trước khi merge |
| **M5** | Gắn `auth.router`, tạo DB `course_reg_test`, thêm `alembic upgrade head` vào CI, cấu hình pytest | cuối Tuần 1 |
| **M2** | Thử engine trên dữ liệu mẫu; báo M4 nếu cần thêm ca đặc biệt | trong Tuần 1–2 |
| **M1** | Xem `schemas/auth.py` và báo nếu định dạng đăng nhập chưa đủ trường | trước Tuần 2 |

---

## 8. Việc tiếp theo của M4 (Tuần 2)

- [ ] `POST /auth/login` thật: tra DB, `verify_password` (đã chạy trong thread pool), cấp JWT access token (TTL từ `ACCESS_TOKEN_TTL_MIN`) và refresh token (TTL từ `REFRESH_TOKEN_TTL_DAYS`)
- [ ] `get_current_user` đọc JWT; phân biệt `TOKEN_EXPIRED` và `UNAUTHENTICATED`; **xóa nhánh `X-Debug-User`**
- [ ] Phân quyền 2 vai trò: sinh viên gọi chức năng admin → `403 FORBIDDEN`
- [ ] Gắn dependency xác thực vào mọi router hiện có (trừ `/auth/*`)
- [ ] Test: đăng nhập đúng/sai, token hết hạn, token sai chữ ký, bảng quyền theo endpoint

*(Tuần 3 trở đi: refresh token xoay vòng, rate-limit, API quản trị học phần và tiên quyết, seed các ca khó hơn.)*

---

## 9. Điều kiện coi là "bàn giao xong Tuần 1"

- [ ] Cột "Đạt?" ở Mục 5 đã đủ ✔
- [ ] PR đã được M3 đọc qua và chạy thử, đã merge vào `main`
- [ ] M2, M3, M5 xác nhận chạy được `alembic upgrade head` và `python -m app.seed` trên máy của họ
- [ ] M5 đã gắn router và thêm migration vào CI
