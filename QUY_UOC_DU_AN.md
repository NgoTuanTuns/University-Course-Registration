# Quy ước chung của nhóm — Hệ thống Đăng ký Học phần & Kiểm tra Điều kiện Tiên quyết

Bài tập cuối kỳ, nhóm 5 người. Tài liệu này để cả nhóm viết code cùng một kiểu, dùng chung một cơ sở dữ liệu và chạy được trên máy của bất kỳ ai. Chỗ nào chưa hợp lý hoặc khó làm theo thì nói trong nhóm rồi sửa lại tài liệu.

Công nghệ giữ đúng như kế hoạch. Để người chưa quen phần mềm vẫn làm được, **mọi thứ chạy bằng Docker Compose**: mỗi người chỉ cần cài Docker, không phải cài riêng Python, PostgreSQL hay Redis.

---

## 1. Công nghệ sử dụng

| Phần | Công nghệ |
|---|---|
| Frontend | React 18 + TypeScript + TailwindCSS (build bằng Vite) |
| Backend | FastAPI (Python 3.11, async) + Pydantic |
| Cơ sở dữ liệu | PostgreSQL 15, truy cập bằng SQLAlchemy, quản lý bảng bằng Alembic |
| Cache & khóa | Redis 7 |
| Kiểm thử | pytest (logic), Locust (tải) |
| Triển khai | Docker Compose + Nginx |

## 2. Cài đặt và chạy

Chỉ cần cài sẵn: **Docker Desktop**, **Git**, **VS Code**.

```bash
git clone <địa-chỉ-repo>
cd <thư-mục-repo>
cp .env.example .env                      # Windows: copy .env.example .env
docker compose up --build                 # chạy toàn bộ hệ thống
```

Mở thêm một terminal, chạy lần đầu để tạo bảng và nạp dữ liệu mẫu:
```bash
docker compose exec api alembic upgrade head
docker compose exec api python -m app.seed
```

Sau đó mở trình duyệt:
- Ứng dụng: http://localhost:8080
- Trang thử API (Swagger): http://localhost:8000/docs

Một số lệnh hay dùng:
```bash
docker compose down                       # tắt hệ thống
docker compose logs -f api                # xem log backend
docker compose exec api pytest            # chạy test backend
docker compose down -v                    # xóa luôn dữ liệu DB (làm lại từ đầu)
```

### Cổng
| Dịch vụ | Cổng trong container | Cổng trên máy |
|---|---|---|
| `nginx` (cổng truy cập chính) | 80 | 8080 |
| `web` (Vite dev server) | 5173 | 5173 |
| `api` (FastAPI) | 8000 | 8000 |
| `db` (PostgreSQL) | 5432 | 5433 |
| `redis` | 6379 | 6380 |

Cổng 5433 và 6380 được chọn khác mặc định để không đụng PostgreSQL/Redis có thể đã cài sẵn trên máy bạn. Các container gọi nhau bằng tên dịch vụ (`db`, `redis`, `api`), không dùng `localhost`.

### Biến môi trường (`.env.example`)
```dotenv
APP_ENV=dev
CORS_ORIGINS=http://localhost:5173,http://localhost:8080

POSTGRES_USER=course_user
POSTGRES_PASSWORD=doi_mat_khau_nay
POSTGRES_DB=course_reg
DATABASE_URL=postgresql+asyncpg://course_user:doi_mat_khau_nay@db:5432/course_reg
TEST_DATABASE_URL=postgresql+asyncpg://course_user:doi_mat_khau_nay@db:5432/course_reg_test

REDIS_URL=redis://redis:6379/0

JWT_SECRET=doi_thanh_chuoi_bat_ky_dai_mot_chut
ACCESS_TOKEN_TTL_MIN=30
REFRESH_TOKEN_TTL_DAYS=7

DEFAULT_MAX_CREDITS=25
WAITLIST_MAX_RATIO=0.2
PREREQ_CACHE_TTL_SEC=600

VITE_API_BASE_URL=/api/v1
```
- File `.env` **không đưa lên Git**; ai thêm biến mới thì thêm vào `.env.example` trong cùng lần commit.
- Test chạy trên database riêng `course_reg_test`, không đụng dữ liệu đang dùng để demo.

## 3. Cấu trúc thư mục

```
project/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/            # config.py, db.py, redis.py, security.py, errors.py
│   │   ├── models/          # các bảng (SQLAlchemy), mỗi bảng một file
│   │   ├── schemas/         # dữ liệu vào/ra của API (Pydantic)
│   │   ├── services/        # nghiệp vụ: prerequisite_engine.py, enrollment_service.py, waitlist_service.py
│   │   ├── api/v1/          # các router: auth, courses, prerequisites, enroll, waitlist, admin
│   │   └── seed.py          # dữ liệu mẫu
│   ├── alembic/             # lịch sử thay đổi bảng
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── api/             # mọi lời gọi tới backend nằm ở đây
│       ├── features/        # courses, timetable, enroll, waitlist, admin
│       ├── components/      # thành phần giao diện dùng chung
│       ├── pages/ hooks/ types/ mocks/
├── loadtest/                # kịch bản Locust
├── nginx/
├── docs/                    # sơ đồ PlantUML, báo cáo
├── docker-compose.yml
├── .env.example
└── README.md
```

## 4. Quy tắc viết code

### Chung
- Tên biến, hàm, file đặt bằng **tiếng Anh**; comment viết tiếng Việt cho dễ hiểu cũng được.
- Mỗi hàm làm một việc. Hàm quá dài (khoảng trên 40 dòng) thì tách ra.
- Giá trị cố định (số tín chỉ tối đa, thời hạn token, TTL cache…) lấy từ `.env`, không viết thẳng trong code.
- Không đưa mật khẩu, `JWT_SECRET`, file `.env` lên Git (đã có trong `.gitignore`).
- Thời gian lưu và truyền theo UTC, định dạng ISO 8601.
- Chỗ khó (thuật toán kiểm tra tiên quyết, xử lý tranh suất) có comment giải thích để bạn khác đọc hiểu.
- Không để lại `print`/`console.log` thử nghiệm khi nộp.

### Backend (Python)
- Đặt tên: biến/hàm/file `snake_case`, class `PascalCase`, hằng số `UPPER_CASE`.
- Dùng **ruff** để kiểm tra và format (cài extension Ruff trong VS Code, bật "format on save"), khỏi tranh cãi kiểu trình bày.
- Hàm công khai có type hint (`def get_course(course_id: int) -> Course:`).
- Chia code thành 3 lớp, mỗi lớp một nhiệm vụ:
  - `api/` (router): nhận request, kiểm tra dữ liệu, gọi service, trả kết quả. **Không viết logic nghiệp vụ ở đây.**
  - `services/`: chứa logic (kiểm tra tiên quyết, đăng ký, waitlist) và quyết định khi nào commit/rollback transaction.
  - `models/`: định nghĩa bảng.
- Dùng `async`/`await` cho thao tác DB và Redis; cứ làm theo các file mẫu có sẵn trong repo.
- Không tự ghép chuỗi SQL; dùng SQLAlchemy.
- Không bao giờ trả `password_hash` ra API.
- Thay đổi cấu trúc bảng **luôn đi qua Alembic** (`alembic revision --autogenerate -m "mô tả"`), không sửa tay trong database.

### Frontend (React + TypeScript)
- File component và component: `PascalCase` (`CourseList.tsx`); biến và hàm: `camelCase`; hook bắt đầu bằng `use`.
- Bật `strict` trong TypeScript và **hạn chế dùng `any`**; kiểu dữ liệu của API đặt trong `src/types/`.
- Dùng **ESLint + Prettier** (bật "format on save").
- Chỉ gọi backend qua các hàm trong `src/api/`, không viết `fetch` rải rác trong từng component.
- Tên trường JSON từ backend là `snake_case`; chuyển sang `camelCase` ở một chỗ duy nhất trong `src/api/`.
- Khi API trả lỗi, hiển thị thông báo thân thiện dựa trên `code` (Mục 5), không hiện lỗi kỹ thuật thô.
- Trong lúc backend chưa xong, dùng MSW (thư mục `mocks/`) để giả lập API theo đúng định dạng ở Mục 5.

### Git
- Nhánh `main` luôn chạy được. Mỗi người làm trên nhánh riêng, đặt tên `ten-tinhnang` (ví dụ `an-timetable`).
- Commit nhỏ, mô tả rõ làm gì: `Thêm API kiểm tra tiên quyết`, `Sửa lỗi trùng lịch`.
- Trước khi làm: `git pull` để lấy code mới nhất.
- Muốn đưa code vào `main`: tạo Pull Request, **một bạn khác đọc qua và chạy thử** rồi mới merge. Gợi ý review theo vòng: M1 xem M2, M2 xem M3, M3 xem M4, M4 xem M5, M5 xem M1.

### Kiểm thử
- Backend dùng `pytest` + `pytest-asyncio`; file đặt tên `test_*.py` trong `backend/tests/`.
- Phần có logic quan trọng thì có test: **kiểm tra tiên quyết** (cả bắc cầu và nhóm "hoặc"), **đăng ký** (không vượt sĩ số, không đăng ký trùng, không vượt tín chỉ, không trùng lịch), **waitlist** (đôn đúng thứ tự).
- Test tranh suất: cho nhiều yêu cầu cùng đăng ký vào lớp chỉ còn 1 chỗ, kết quả phải đúng 1 người vào.
- Kiểm thử tải bằng Locust trong `loadtest/`: kịch bản mở đăng ký với khoảng 2.000 sinh viên trong 30 giây (xem yêu cầu SR-NF-05).

## 5. Quy ước API

- Địa chỉ gốc: `/api/v1`. Có thể thử API trực tiếp tại `/docs`.
- Đường dẫn dùng danh từ số nhiều: `/courses`, `/enrollments`, `/waitlist`. Các endpoint chính theo Mục 5 của kế hoạch: `GET /prerequisites/check`, `POST /prerequisites/explain`, `POST /enroll`.
- Tên trường JSON: `snake_case` (ví dụ `student_id`, `offering_id`).
- Sau khi đăng nhập, frontend gửi kèm header `Authorization: Bearer <access_token>`.
- Danh sách có phân trang: `?page=1&page_size=20` (tối đa 100), trả về `{ "items": [], "total": 0, "page": 1, "page_size": 20 }`.
- Mã trạng thái thường dùng: `200` thành công, `201` tạo mới, `401` chưa đăng nhập, `403` không đủ quyền, `404` không tìm thấy, `409` xung đột, `422` dữ liệu không hợp lệ hoặc vi phạm quy tắc.
- Khi lỗi, backend trả về cùng một dạng (dùng `HTTPException` của FastAPI) để frontend dễ xử lý:
  ```json
  { "detail": { "code": "PREREQ_NOT_MET", "message": "Thiếu môn tiên quyết", "missing_courses": ["INT131"] } }
  ```

| code | HTTP | Ý nghĩa |
|---|---|---|
| `UNAUTHENTICATED` | 401 | Chưa đăng nhập |
| `TOKEN_EXPIRED` | 401 | Token hết hạn (frontend dùng refresh token để lấy token mới) |
| `FORBIDDEN` | 403 | Không đủ quyền (sinh viên gọi chức năng admin) |
| `NOT_FOUND` | 404 | Không tìm thấy dữ liệu |
| `PREREQ_NOT_MET` | 422 | Thiếu điều kiện tiên quyết |
| `CREDIT_LIMIT_EXCEEDED` | 422 | Vượt số tín chỉ tối đa của kỳ |
| `SCHEDULE_CONFLICT` | 409 | Trùng lịch học |
| `ALREADY_ENROLLED` | 409 | Đã đăng ký lớp này rồi |
| `CONCURRENT_UPDATE` | 409 | Có người vừa sửa cùng dữ liệu, thử lại được |

- Đăng ký thành công: `201`. Lớp đã đầy và được đưa vào danh sách chờ: `200` với `"status": "WAITLISTED"`.

## 6. Cơ sở dữ liệu (chốt cho cả nhóm)

Gồm **7 bảng** như thiết kế trong kế hoạch. Quy ước chung:
- Tên bảng và cột `snake_case`; tên bảng ở số nhiều.
- Khóa chính là số nguyên tự tăng `id` (dễ đọc, dễ gõ khi thử API).
- Thời gian dùng `TIMESTAMPTZ`, mặc định `now()`.
- Trạng thái dùng `VARCHAR` + `CHECK` (không dùng kiểu ENUM của PostgreSQL cho đỡ rắc rối khi sửa).
- Học kỳ (`term`) viết dạng `2026-1` (năm-kỳ).
- Lịch học (`schedule`, kiểu JSONB) là danh sách buổi học, `day` từ 1 (Thứ Hai) đến 7 (Chủ nhật), giờ dạng `HH:MM`:
  ```json
  [ { "day": 2, "start": "07:00", "end": "09:30" } ]
  ```
- Cả nhóm viết bảng bằng SQLAlchemy trong `models/` theo đúng các cột dưới đây. Muốn đổi bảng thì báo cả nhóm trước để mọi người cập nhật theo.

```sql
CREATE TABLE students (
  id            INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  mssv          VARCHAR(20)  UNIQUE,                  -- admin có thể để trống
  email         VARCHAR(255) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  full_name     VARCHAR(150) NOT NULL,
  role          VARCHAR(10)  NOT NULL DEFAULT 'student' CHECK (role IN ('student','admin')),
  program       VARCHAR(100),
  max_credits   SMALLINT     NOT NULL DEFAULT 25 CHECK (max_credits BETWEEN 1 AND 40),
  created_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
  CHECK (role <> 'student' OR mssv IS NOT NULL)
);

CREATE TABLE courses (
  id          INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  code        VARCHAR(20)  NOT NULL UNIQUE,           -- ví dụ INT131
  name        VARCHAR(200) NOT NULL,
  credits     SMALLINT     NOT NULL CHECK (credits BETWEEN 1 AND 10),
  description TEXT,
  created_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE course_offerings (                       -- lớp học phần mở trong một kỳ
  id             INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  course_id      INTEGER     NOT NULL REFERENCES courses(id),
  term           VARCHAR(10) NOT NULL,                -- 2026-1
  section        VARCHAR(10) NOT NULL,                -- mã lớp, ví dụ 01
  instructor     VARCHAR(150),                        -- giảng viên
  capacity       SMALLINT    NOT NULL CHECK (capacity > 0),
  enrolled_count SMALLINT    NOT NULL DEFAULT 0,      -- số người đã đăng ký
  schedule       JSONB       NOT NULL,                -- như ví dụ ở trên
  room           VARCHAR(50),
  UNIQUE (course_id, term, section),
  CHECK (enrolled_count BETWEEN 0 AND capacity)
);
CREATE INDEX ix_offerings_term ON course_offerings (term);
CREATE INDEX ix_offerings_course ON course_offerings (course_id);

-- Điều kiện tiên quyết (danh sách kề của đồ thị DAG).
-- type = 'AND': bắt buộc phải học xong môn này.
-- type = 'OR' : các dòng có cùng (course_id, group_no) là một nhóm, chỉ cần học xong 1 môn trong nhóm.
CREATE TABLE prerequisites (
  course_id        INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
  prereq_course_id INTEGER NOT NULL REFERENCES courses(id),
  type             VARCHAR(3) NOT NULL DEFAULT 'AND' CHECK (type IN ('AND','OR')),
  group_no         SMALLINT   NOT NULL DEFAULT 0,     -- 0 nếu AND, từ 1 trở lên nếu OR
  PRIMARY KEY (course_id, prereq_course_id),
  CHECK (course_id <> prereq_course_id),
  CHECK ((type = 'AND' AND group_no = 0) OR (type = 'OR' AND group_no > 0))
);
CREATE INDEX ix_prereq_prereq ON prerequisites (prereq_course_id);

-- Chỉ lưu các môn sinh viên đã học xong và đạt (thang điểm 10).
CREATE TABLE completed_courses (
  student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
  course_id  INTEGER NOT NULL REFERENCES courses(id),
  grade      NUMERIC(3,1) CHECK (grade BETWEEN 0 AND 10),
  term       VARCHAR(10),
  PRIMARY KEY (student_id, course_id)
);

CREATE TABLE enrollments (
  id           INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  student_id   INTEGER     NOT NULL REFERENCES students(id) ON DELETE CASCADE,
  offering_id  INTEGER     NOT NULL REFERENCES course_offerings(id),
  status       VARCHAR(10) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','CANCELLED')),
  version      INTEGER     NOT NULL DEFAULT 0,        -- tăng 1 mỗi lần sửa (chống ghi đè đồng thời)
  enrolled_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  cancelled_at TIMESTAMPTZ
);
-- Mỗi sinh viên chỉ có một đăng ký ACTIVE cho mỗi lớp (hủy rồi vẫn đăng ký lại được)
CREATE UNIQUE INDEX uq_enrollments_active ON enrollments (student_id, offering_id) WHERE status = 'ACTIVE';
CREATE INDEX ix_enrollments_student  ON enrollments (student_id, status);
CREATE INDEX ix_enrollments_offering ON enrollments (offering_id) WHERE status = 'ACTIVE';

CREATE TABLE waitlist (
  id          INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  student_id  INTEGER     NOT NULL REFERENCES students(id) ON DELETE CASCADE,
  offering_id INTEGER     NOT NULL REFERENCES course_offerings(id) ON DELETE CASCADE,
  position    INTEGER     NOT NULL CHECK (position > 0),   -- thứ tự hiển thị trong hàng chờ
  enqueued_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (student_id, offering_id)
);
CREATE INDEX ix_waitlist_queue ON waitlist (offering_id, enqueued_at, id);
```

### Cách dùng các bảng cho đúng
- **Giữ chỗ khi đăng ký:** dùng đúng một câu cập nhật có điều kiện, để không bao giờ vượt sĩ số:
  ```sql
  UPDATE course_offerings
     SET enrolled_count = enrolled_count + 1
   WHERE id = :offering_id AND enrolled_count < capacity
  RETURNING id;
  ```
  Không có dòng nào trả về nghĩa là lớp đã đầy → đưa vào waitlist. Khi hủy thì giảm `enrolled_count` 1 đơn vị và đôn người đầu hàng chờ, làm trong cùng một transaction. Redis lock chỉ là lớp bảo vệ thêm lúc cao điểm, không thay thế câu lệnh này.
- **Tính tín chỉ đang đăng ký:** cộng `credits` của các đăng ký `ACTIVE` trong cùng kỳ.
- **Kiểm tra tiên quyết:** đạt khi (1) mọi môn loại `AND` đã có trong `completed_courses` và (2) mỗi nhóm `OR` có ít nhất một môn đã có. Phải xét cả tiên quyết bắc cầu (A cần B, B cần C). Khi nhập hoặc sửa dữ liệu phải kiểm tra không tạo vòng lặp (A cần B, B lại cần A); dữ liệu có vòng lặp bị từ chối.
- **Waitlist:** vào trước ra trước (theo `enqueued_at`, `id`). `position` chỉ để hiển thị và được cập nhật lại mỗi khi hàng chờ thay đổi.
- **Dữ liệu mẫu (`seed.py`):** khoảng 50–200 học phần, nhớ có đủ các ca: tiên quyết bắc cầu, nhóm "hoặc", lớp sắp đầy, hai lớp trùng lịch, một tài khoản admin và vài tài khoản sinh viên.

## 7. Quy ước Redis

Dùng database 0 khi chạy bình thường, database 1 khi chạy test. Khóa đặt theo mẫu sau:

| Mục đích | Khóa | Thời gian sống |
|---|---|---|
| Cache kết quả kiểm tra tiên quyết | `prereq:{student_id}:{course_id}` | `PREREQ_CACHE_TTL_SEC` (10 phút) |
| Khóa khi đăng ký cùng một lớp | `lock:offering:{offering_id}` | 5 giây (tự hết hạn) |

Khi dữ liệu tiên quyết hoặc `completed_courses` của sinh viên thay đổi, phải xóa các khóa `prereq:*` tương ứng.

## 8. Trước khi gộp code (checklist ngắn)

- [ ] Chạy được bằng `docker compose up` trên máy mình, không báo lỗi.
- [ ] Đã format code (ruff / Prettier).
- [ ] Có test cho phần logic mới (nếu có).
- [ ] Không còn `print`/`console.log` thử nghiệm, không có mật khẩu hay file `.env` trong commit.
- [ ] Nếu đổi bảng: đã có Alembic migration và báo cả nhóm.
- [ ] Nếu thêm biến môi trường: đã cập nhật `.env.example`.
- [ ] Một bạn khác đã đọc qua và chạy thử.
