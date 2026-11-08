# UniFlow — Hệ thống Đăng ký Học phần & Kiểm tra Điều kiện Tiên quyết

Dự án bài tập lớn môn **Công nghệ Phần mềm**. Hệ thống quản lý đăng ký môn học và giải trình điều kiện tiên quyết cho sinh viên đại học, hỗ trợ giải quyết tranh chấp đồng thời khi số lượng đăng ký lớn.

---

## 👥 Thành viên nhóm & Phân công vai trò (M1 – M5)

| Vai trò | Phụ trách chính | Nhiệm vụ trọng tâm |
| :--- | :--- | :--- |
| **M1** | Frontend Web Developer | Giao diện React 18 + TS + TailwindCSS, quản lý phiên đăng nhập JWT, tra cứu môn học, biểu đồ giải trình tiên quyết, quản trị viên Admin. |
| **M2** | Prerequisites Engine | Thuật toán đồ thị có hướng phi chu trình (DAG), phát hiện chu trình, giải trình điều kiện tiên quyết, bộ đệm Redis cache, benchmark. |
| **M3** | Enrollment & Registration | Nghiệp vụ đăng ký học phần, hủy môn, kiểm tra trùng lịch học, danh sách chờ (Waitlist FIFO), xử lý tranh chấp concurrency. |
| **M4** | Database & Security | Thiết kế 7 bảng dữ liệu SQLAlchemy, Alembic migrations, nạp 1.000+ sinh viên mẫu, xác thực JWT (Token Rotation), RBAC, API Admin. |
| **M5** | DevOps & QA Lead | Docker Compose, Nginx Reverse Proxy, CI GitHub Actions, bộ kiểm định toàn vẹn (Invariants I1–I10), OpenAPI Snapshot, Locust loadtest. |

---

## 🛠️ Công nghệ sử dụng

- **Frontend:** React 18, TypeScript, Tailwind CSS, Lucide Icons, Vite 6, Vitest.
- **Backend:** Python 3.11, FastAPI (async/await), Pydantic v2, Uvicorn.
- **Cơ sở dữ liệu:** PostgreSQL 15, SQLAlchemy 2.0 (AsyncPG), Alembic migrations.
- **Bộ đệm & Khóa:** Redis 7 (Alpine).
- **Kiểm thử & Đảm bảo chất lượng:** Pytest, Vitest, Ruff, ESLint, Prettier, OpenAPI Contract Snapshot.
- **Triển khai & Vận hành:** Docker Compose, Docker Multi-stage Builds, Nginx.

---

## 🚀 Hướng dẫn cài đặt và Khởi chạy

### Yêu cầu tiên quyết
- **Docker Desktop** (khuyến nghị cho mọi thành viên).
- **Git** và **VS Code**.
- *(Tùy chọn khi phát triển local)*: Python 3.11+ và Node.js 20+.

---

### Cách 1: Khởi chạy toàn bộ bằng Docker Compose (Khuyên dùng khi chấm bài / Demo)

1. **Chuẩn bị file cấu hình:**
   ```powershell
   # Tạo file .env từ mẫu (nếu chưa có)
   copy .env.example .env
   ```

2. **Dựng và khởi chạy các container:**
   ```powershell
   docker compose up --build
   ```

3. **Mở một terminal mới để áp dụng migration và nạp dữ liệu mẫu:**
   ```powershell
   # Chạy migration tạo 7 bảng
   docker compose exec api alembic upgrade head

   # Nạp dữ liệu mẫu (1.001 sinh viên, 200 môn học, 357 lớp mở)
   docker compose exec api python -m app.seed --reset
   ```

4. **Truy cập ứng dụng:**
   - **Cổng Nginx (truy cập chính):** <http://localhost:8080>
   - **Giao diện Web trực tiếp (Vite):** <http://localhost:5173>
   - **Tài liệu API Swagger UI:** <http://localhost:8000/docs>

---

### Cách 2: Chế độ phát triển cục bộ Hybrid (Khuyên dùng khi lập trình trên Windows)

Chế độ này tận dụng PostgreSQL & Redis trong Docker, đồng thời chạy Backend & Frontend trực tiếp trên máy để hỗ trợ Hot Reload mượt mà nhất.

1. **Bật hạ tầng cơ sở dữ liệu & Cache:**
   ```powershell
   docker compose up -d db redis
   ```
   *(PostgreSQL lắng nghe tại host cổng `5433`, Redis tại cổng `6380` nhằm tránh đụng độ cổng dịch vụ hệ thống).*

2. **Khởi chạy Backend:**
   ```powershell
   cd backend
   $env:PYTHONPATH="."
   # Áp dụng migration và seed nếu lần đầu chạy
   ..\.venv\Scripts\alembic upgrade head
   ..\.venv\Scripts\python -m app.seed --reset

   # Chạy Uvicorn dev server
   ..\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
   ```

3. **Khởi chạy Frontend (ở một terminal khác tại thư mục gốc):**
   ```powershell
   npm install
   npm run dev
   ```
   *Truy cập:* <http://localhost:5173>

---

## 🔑 Tài khoản thử nghiệm (Seed Data)

Hệ thống đã nạp sẵn dữ liệu chuẩn để kiểm thử các luồng phân quyền (RBAC):

| Vai trò | Email đăng nhập | Mật khẩu | Quyền hạn |
| :--- | :--- | :--- | :--- |
| **Sinh viên** | `sv0001@uni.edu.vn` | `Student@123` | Tra cứu môn học, xem cây điều kiện tiên quyết, đăng ký môn |
| **Quản trị viên** | `admin@uni.edu.vn` | `Admin@123` | Toàn quyền Quản lý Học phần (CRUD Courses), xem trạng thái sinh viên |

*(Bạn cũng có thể đăng nhập bằng các mã sinh viên từ `sv0002@uni.edu.vn` đến `sv1000@uni.edu.vn` với cùng mật khẩu `Student@123`).*

---

## 🧪 Kiểm định chất lượng & Bộ Test tự động (Quality Gates)

Dự án áp dụng tiêu chuẩn kiểm thử khắt khe được tự động hóa qua GitHub Actions CI.

### 1. Kiểm thử Frontend (M1)
Chạy tại thư mục gốc:
```powershell
npm run lint                  # Kiểm tra quy chuẩn mã nguồn với ESLint
npm exec prettier -- --check .# Kiểm tra định dạng code với Prettier
npm test                      # Chạy 11/11 bài kiểm thử xung đột lịch với Vitest
npm run build                 # Kiểm tra biên dịch TypeScript và đóng gói Vite
```

### 2. Kiểm thử Backend (M2, M4, M5)
Chạy tại thư mục `backend/` (hoặc qua `docker compose exec api ...`):
```powershell
# 1. Kiểm tra linter và định dạng mã nguồn Python
ruff check app tests
ruff format --check app tests

# 2. Kiểm tra tính khớp hợp đồng API với Frontend
python -m app.tools.openapi_snapshot --check

# 3. Kiểm tra tính toàn vẹn cơ sở dữ liệu (Invariants I1-I10)
python -m app.tools.invariants

# 4. Chạy Unit test độc lập (không cần DB, chạy cực nhanh)
$env:UNIT_TESTS_ONLY="1"; pytest -m unit

# 5. Chạy Integration & Concurrency test (yêu cầu PostgreSQL test)
pytest -m "integration or concurrency"
```

---

## 📂 Cấu trúc thư mục dự án

```text
cuoiki/
├── .github/workflows/       # Kịch bản CI/CD GitHub Actions
├── backend/                 # Mã nguồn Backend FastAPI
│   ├── alembic/             # Lịch sử và kịch bản nâng cấp DB migrations
│   ├── app/
│   │   ├── api/v1/          # Endpoints: auth, admin, prerequisites, enroll...
│   │   ├── core/            # Cấu hình config, DB session, Redis, JWT tokens, RBAC
│   │   ├── models/          # 7 bảng cơ sở dữ liệu SQLAlchemy (Course, Student,...)
│   │   ├── schemas/         # Mô hình dữ liệu Pydantic Request/Response
│   │   ├── services/        # Nghiệp vụ: prerequisite_engine, course_service,...
│   │   ├── tools/           # Công cụ: invariants.py, openapi_snapshot.py
│   │   ├── main.py          # FastAPI application entrypoint
│   │   ├── seed.py          # Script nạp dữ liệu mẫu CLI
│   │   └── seed_data.py     # Bộ sinh dữ liệu mẫu bảo đảm DAG không chu trình
│   ├── tests/               # 246+ bài kiểm thử tự động (Unit, Integration)
│   └── pyproject.toml       # Cấu hình Pytest, Coverage và Ruff
├── ban_giao/                # Biên bản bàn giao công việc hàng tuần của từng thành viên
│   ├── Tuan1/
│   ├── Tuan2/
│   └── Tuan3/
├── chitietcongviec/         # Kế hoạch chi tiết 7 tuần và Quy ước nhóm
├── docs/                    # Tài liệu đặc tả kỹ thuật, sơ đồ, OpenAPI contract
├── nginx/                   # Cấu hình Nginx Reverse Proxy
├── public/                  # Static assets & MSW mock service worker
├── src/                     # Mã nguồn Frontend React 18 + TypeScript
│   ├── api/                 # Axios HTTP client, token rotation, API modules
│   ├── components/          # UI Components dùng chung (Header, Sidebar, Modal,...)
│   ├── features/            # Tính năng: auth, courses, prerequisites, timetable
│   ├── types/               # TypeScript interfaces & types
│   ├── App.tsx              # Root component & Routing
│   └── main.tsx             # Frontend entrypoint
├── docker-compose.yml       # Điều phối container (Nginx, Web, API, DB, Redis)
├── Dockerfile               # Multi-stage Dockerfile cho Backend
├── Dockerfile.web           # Multi-stage Dockerfile cho Frontend
├── package.json             # Cấu hình phụ thuộc Frontend
├── vite.config.ts           # Cấu hình Vite dev server & API proxy
└── README.md                # Tài liệu hướng dẫn dự án
```

---

## 📌 Các lệnh quản trị thường dùng

```powershell
# Xem logs thời gian thực của backend
docker compose logs -f api

# Tắt toàn bộ hệ thống
docker compose down

# Xóa toàn bộ container và volume dữ liệu (reset database hoàn toàn)
docker compose down -v
```

---

## 📜 Quy ước dự án

1. **Bảo mật:** Không bao giờ commit file `.env` hoặc secret keys lên GitHub.
2. **Quy trình Git:** Không commit trực tiếp vào nhánh `main`. Mọi tính năng tạo nhánh riêng và mở Pull Request có sự thẩm định (review) chéo giữa các thành viên.
3. **Chi tiết quy ước:** Xem chi tiết tại [QUY_UOC_DU_AN.md](chitietcongviec/QUY_UOC_DU_AN.md).
