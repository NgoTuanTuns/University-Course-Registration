# UniFlow — Hệ thống Đăng ký Học phần & Điều hành Đào tạo

Dự án bài tập lớn môn **Công nghệ Phần mềm**. **UniFlow** là hệ thống đăng ký học phần trực tuyến mô phỏng quy trình đào tạo tín chỉ theo mô hình Đại học Tôn Đức Thắng (TDTU) cho **Học kỳ 2026-2** (cuối 12/2026 – cuối 05/2027), tập trung vào tính toàn vẹn dữ liệu dưới tải đồng thời cao, kiểm tra điều kiện tiên quyết theo đồ thị DAG và trải nghiệm sắp xếp thời khóa biểu chuẩn 5 ca học.

---

## 1. Kiến trúc & Công nghệ sử dụng

- **Frontend:** React 18, TypeScript, Vite 6, React Router, Lucide Icons, Vitest, ESLint, Prettier.
- **Backend:** Python 3.11, FastAPI (async/await), Pydantic v2, Uvicorn.
- **Cơ sở dữ liệu:** PostgreSQL 15, SQLAlchemy 2.0 (AsyncPG), Alembic Migrations (10 bảng dữ liệu, head `0005_add_registration_phases`).
- **Bộ đệm & Điều phối khóa:** Redis 7 (cache đồ thị DAG tiên quyết, idempotency key, rate limiting, lock gate).
- **Hạ tầng & Kiểm thử:** Docker Compose, Nginx Reverse Proxy, Pytest (unit, integration, concurrency), Locust Loadtest, OpenAPI Contract Snapshot, GitHub Actions CI.

---

## 2. Phân công nhóm (M1 – M5)

| Vai trò | Phụ trách chính | Phạm vi công việc |
| :--- | :--- | :--- |
| **M1** | Frontend Web | Giao diện người dùng, xác thực JWT, tra cứu & bộ lọc nhanh, xem trước TKB, sơ đồ DAG, trung tâm thông báo, xuất `.ics`, không gian Admin. |
| **M2** | Prerequisites Engine | Đồ thị có hướng phi chu trình (DAG), kiểm tra điều kiện AND/OR, phát hiện chu trình, giải trình điều kiện thiếu, Redis cache. |
| **M3** | Enrollment & Scheduler | Đăng ký/hủy học phần, đổi lớp nguyên tử chống deadlock, hàng chờ FIFO tự đôn chỗ, gợi ý xếp lịch tự động (MRV Backtracking). |
| **M4** | Database & Security | Mô hình 10 bảng SQLAlchemy, Alembic migrations, sinh dữ liệu mẫu 1.001 tài khoản, JWT Token Rotation, RBAC, phân quyền theo khoa. |
| **M5** | DevOps & QA | Docker Compose, Nginx, GitHub Actions CI, bộ kiểm định bất biến dữ liệu (Invariants), OpenAPI Snapshot, kịch bản kiểm tải Locust. |

---

## 3. Tính năng chính

### Cổng Sinh viên
- **Kế hoạch học tập (ĐKKHHT):** Xem danh sách môn dự kiến kỳ `2026-2`, theo dõi sĩ số nhu cầu mở lớp (`>= 15 SV` mới mở lớp) và tự động khóa ở chế độ chỉ xem sau khi kết thúc đợt ĐKKHHT.
- **Tra cứu & Đăng ký học phần:** Tự động lọc theo khoa, ưu tiên môn trong KHHT và đúng tiến độ năm học; hỗ trợ **Bộ lọc nhanh** (`Chỉ môn trong KHHT`, `Ẩn lớp trùng lịch hiện tại`, `Chỉ lớp còn chỗ`, `Đủ điều kiện`), tô xám lớp đã đăng ký và mở pop-up **Xem trước thời khóa biểu** độ tương phản cao (Đã đăng ký / Xem trước / Trùng lịch).
- **Thời khóa biểu chuẩn 5 ca TDTU & Xuất lịch `.ics`:** Hỗ trợ môn 1 ca/tuần và môn thực hành/cốt lõi 2 ca/tuần (Ca 1–Ca 4 chính, Ca 5 buổi tối cho môn đặc biệt); xuất file `.ics` (RFC 5545, múi giờ `Asia/Ho_Chi_Minh`) để nhập trực tiếp vào Google Calendar / Apple Calendar.
- **Đổi lớp học phần an toàn (Atomic Section Swap):** Chuyển giữa các lớp cùng học phần trong 1 transaction PostgreSQL khóa theo thứ tự ID tăng dần (chống deadlock, giữ nguyên lớp cũ nếu lớp đích đầy hoặc trùng lịch, tự động đôn hàng chờ lớp cũ).
- **Gợi ý xếp lịch tự động (Smart Auto-Scheduler):** Dùng thuật toán MRV Backtracking kết hợp chấm điểm đa tiêu chí (tránh Ca 1, tránh Ca 5, nghỉ Thứ 7, dồn ít ngày đi học nhất, ưu tiên buổi sáng/chiều) trả về Top 3 phương án không trùng ca và cho phép đăng ký hàng loạt.
- **Danh sách chờ (Waitlist FIFO) & Trung tâm thông báo:** Tự động ghi danh hàng chờ khi lớp đầy, hỗ trợ hủy chờ ở mọi màn hình, tự đôn chỗ theo thứ tự thời gian và phát thông báo tại biểu tượng chuông trên thanh tiêu đề (đôn lớp, hủy mở lớp, mở thêm lớp, trạng thái đợt ĐK).
- **Học phí tạm tính theo tín chỉ:** Tính tự động học phí kỳ `2026-2` theo nhóm học phần và phụ phí phòng máy, đồng bộ tức thì theo thao tác đăng ký/đổi/hủy lớp và hỗ trợ in phiếu tạm tính.
- **Sơ đồ điều kiện tiên quyết (DAG) & Hồ sơ học tập:** Biểu đồ tương tác hiển thị điều kiện AND/OR, tiến độ tích lũy và bảng điểm GPA.

### Cổng Quản trị (Phòng Đào tạo)
- **Điều hành giai đoạn đợt đăng ký (`/admin/phases`):** Chuyển đổi trực tiếp 4 giai đoạn (`Đợt ĐKKHHT` → `Chốt mở lớp` → `Đợt ĐKMH chính thức` → `Đã khóa sổ học kỳ`), cấu hình thời hạn đếm ngược và tự động khóa thao tác khi quá hạn.
- **Tổng hợp nhu cầu & Chốt mở nhiều lớp (`/admin/study-plans`):** Theo dõi số SV ĐKKHHT từng môn và tự động mở nhiều lớp (`ceil(nhu_cầu / 40)`) cho các môn đạt ngưỡng.
- **Quản trị học phần, Tiên quyết & Sĩ số lớp mở:** CRUD học phần, cập nhật cạnh tiên quyết kèm chặn chu trình DAG, và công cụ **Làm đầy sĩ số / Giải phóng 1 chỗ** trên `/courses` (bảo toàn bất biến dữ liệu `I1–I9`) để kiểm thử đầy lớp và tự đôn Waitlist.

---

## 4. Hướng dẫn cài đặt và Khởi chạy

### Yêu cầu hệ thống
- Docker Desktop (khuyến nghị khi demo và chấm bài).
- *(Tùy chọn cho phát triển cục bộ)*: Python 3.11+ và Node.js 20+.

### Cách 1: Khởi chạy trọn bộ bằng Docker Compose (Khuyên dùng)

1. Tạo file biến môi trường từ mẫu (nếu chưa có):
   ```powershell
   copy .env.example .env
   ```

2. Khởi chạy toàn bộ dịch vụ (`nginx`, `web`, `api`, `db`, `redis`):
   ```powershell
   docker compose up --build -d
   ```

3. Chạy migration và nạp dữ liệu mẫu kỳ `2026-2`:
   ```powershell
   docker compose exec api alembic upgrade head
   docker compose exec api python -m app.seed --reset
   ```

4. Truy cập hệ thống:
   - **Ứng dụng Web (qua Nginx):** <http://localhost:8080>
   - **Frontend Vite trực tiếp:** <http://localhost:5173>
   - **Swagger API Docs:** <http://localhost:8000/docs>

> Môi trường loadtest dùng database/Redis tách biệt; xem chi tiết tại [`loadtest/README.md`](loadtest/README.md).

### Cách 2: Chạy phát triển cục bộ (Hybrid)

1. Khởi động PostgreSQL (`5433`) và Redis (`6380`):
   ```powershell
   docker compose up -d db redis
   ```

2. Chạy Backend:
   ```powershell
   cd backend
   $env:PYTHONPATH="."
   ..\.venv\Scripts\alembic upgrade head
   ..\.venv\Scripts\python -m app.seed --reset
   ..\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
   ```

3. Chạy Frontend (terminal khác tại thư mục gốc):
   ```powershell
   npm install
   npm run dev
   ```

---

## 5. Tài khoản thử nghiệm (Seed Data)

| Vai trò | Email đăng nhập | Mật khẩu | Hồ sơ mẫu |
| :--- | :--- | :--- | :--- |
| **Sinh viên Năm 3 (CNTT)** | `sv0587@uni.edu.vn` | `Student@123` | Khoa Công nghệ thông tin, 57 TC tích lũy, có sẵn KHHT gồm cả môn mở lớp và môn không mở lớp |
| **Tân sinh viên Năm 1 (CNTT)** | `sv0055@uni.edu.vn` | `Student@123` | Khoa Công nghệ thông tin, 0 TC tích lũy |
| **Quản trị viên (Admin)** | `admin@uni.edu.vn` | `Admin@123` | Toàn quyền điều hành đợt ĐK, chốt mở lớp, quản trị học phần, tiên quyết và sĩ số lớp |

*(Các tài khoản từ `sv0001@uni.edu.vn` đến `sv1000@uni.edu.vn` đều dùng chung mật khẩu `Student@123`).*

---

## 6. Kiểm thử & Cổng đảm bảo chất lượng (Quality Gates)

### Backend (371 tests: 250 unit + 121 integration & concurrency)
```powershell
# Lint & Format
cd backend
..\.venv\Scripts\ruff check --config pyproject.toml app tests ../loadtest/locustfile.py
..\.venv\Scripts\ruff format --check --config pyproject.toml app tests alembic ../loadtest/locustfile.py

# Kiểm tra OpenAPI Contract Snapshot
docker compose exec -T api python -m app.tools.openapi_snapshot --check

# Chạy toàn bộ test tích hợp & đồng thời trên PostgreSQL + Redis
docker compose exec -T api pytest -q

# Kiểm định bất biến dữ liệu (0 vi phạm)
docker compose exec -T api python -m app.tools.invariants
```

### Frontend (22 Vitest tests + TypeScript + ESLint + Prettier + Build)
```powershell
npx prettier --check "src/**/*.{ts,tsx,css}" index.html
npx tsc --noEmit
npm run lint
npm test -- --run
npm run build
```

---

## 7. Cấu trúc thư mục chính

```text
.
├── backend/
│   ├── alembic/versions/    # Migration 0001 -> 0005 (10 bảng)
│   ├── app/
│   │   ├── api/v1/          # Routers: auth, courses, enroll, waitlist, timetable, study_plans, registration_phases, scheduler, students, admin
│   │   ├── core/            # config, db, redis, security, tokens, faculty, tuition, rate_limit
│   │   ├── models/          # SQLAlchemy 2.0 ORM models
│   │   ├── schemas/         # Pydantic v2 schemas
│   │   ├── services/        # Business logic: enrollment, swap, waitlist, prerequisite DAG, scheduler, study_plan, phase
│   │   └── tools/           # invariants, openapi_snapshot, benchmark
│   └── tests/               # Unit, integration & concurrency test suite
├── docs/                    # OpenAPI snapshot, thiết kế DB/bảo mật/kiểm thử, test vectors
├── loadtest/                # Kịch bản Locust & công cụ đo tải
├── nginx/                   # Cấu hình Reverse Proxy
├── public/                  # Favicon UniFlow & logo TDTU
└── src/                     # Ứng dụng React + TypeScript
```
