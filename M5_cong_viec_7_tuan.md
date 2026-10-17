# M5 — QA Engineer & DevOps: Công việc chi tiết 7 tuần coding

**Đề tài:** Hệ thống Đăng ký Học phần & Kiểm tra Điều kiện Tiên quyết
**Vai trò:** M5 — Docker Compose + Nginx, CI, chiến lược kiểm thử, kiểm thử tải Locust, quản trị dự án, tài liệu tổng hợp
**Căn cứ:** *Báo cáo kế hoạch dự án* (Mục 4.5, 6, 7, 8) và *Quy ước chung của nhóm*.

> **Cách đánh số tuần.** Kế hoạch gốc có 9 tuần; Tuần 1–2 là thiết kế, nên **7 tuần coding còn lại tương ứng Tuần 3–9 của kế hoạch** (giống file của M1–M4).
>
> **Đường găng của M5:** cả nhóm dùng `docker compose up` ngay từ ngày đầu coding. Nếu môi trường chạy chưa tốt trong **2 ngày đầu** thì mọi người đều bị chặn. Vì vậy Ngày 1–2 của Tuần 1 ưu tiên tuyệt đối cho Docker Compose, khung `core/` và CI — chưa viết test chi tiết.
>
> **Phân chia việc kiểm thử:** mỗi thành viên **tự viết test cho logic của mình** (quy ước Mục 4 "Kiểm thử": tiên quyết, đăng ký, waitlist). M5 sở hữu **hạ tầng kiểm thử** (khung, fixture, CI), các **bộ test xuyên thành phần** (nghiệm thu, bất biến, tích hợp, hợp đồng, E2E, tải) và **chất lượng tổng thể** của dự án.

---

## 0. Tổng quan 7 tuần

| Tuần coding | Tuần kế hoạch | Trọng tâm | Sản phẩm chính |
|---|---|---|---|
| 1 | 3 | **Docker Compose chạy thật**, khung `core/`, **CI**, khung test + fixture | `docker compose up` dùng được cho cả nhóm; CI chạy lint/test |
| 2 | 4 | Kế hoạch test, **bộ bất biến**, bộ nghiệm thu tiên quyết, snapshot OpenAPI, **Locust bản nháp**; **review lần 1** | `find_invariant_violations`, Locust chạy thử được |
| 3 | 5 | **Pipeline kiểm thử tích hợp** trong CI, kiểm thử hợp đồng, test phân quyền, hạ tầng E2E | CI chạy tích hợp + hợp đồng |
| 4 | 6 | **Spike test 2.000 người dùng (baseline)**, **bug bash**; **review lần 2** | Báo cáo tải baseline, danh sách lỗi |
| 5 | 7 | **Chạy lại tải**, so sánh trước/sau, xử lý test không ổn định | Bảng trước/sau, bản nháp báo cáo tải |
| 6 | 8 | **Docker prod profile**, E2E smoke cùng M1, CI xanh, đóng băng; **review lần 3** | Build production chạy offline; E2E xanh |
| 7 | 9 | **Báo cáo tải cuối**, tài liệu tổng hợp, hậu cần buổi bảo vệ | Báo cáo cuối kỳ, kịch bản demo, bản dự phòng |

**Việc lặp lại mỗi tuần:**
- Đầu buổi làm: `git pull`; làm trên nhánh riêng dạng `ten-ci-compose` (`ten-tinhnang`); commit nhỏ, mô tả rõ.
- Mỗi PR: một bạn khác đọc và chạy thử rồi mới merge. **Vòng review: M4 xem PR của M5; M5 xem PR của M1.**
- Cập nhật **bảng tiến độ** (Mục 1.4) vào cuối mỗi tuần; nhắc các điểm đang chờ chốt (Mục 9).
- Theo dõi CI: nếu `main` đỏ thì xử lý ngay cùng người gây lỗi (`main` luôn phải chạy được).

---

## 1. Quy ước M5 phải bám theo (tóm tắt để tra nhanh)

**Cổng (quy ước):** `nginx` 80→**8080**; `web` (Vite) 5173; `api` (FastAPI) 8000; `db` (PostgreSQL) 5432→**5433**; `redis` 6379→**6380**. Container gọi nhau bằng **tên dịch vụ** (`db`, `redis`, `api`), không dùng `localhost`. Ứng dụng: `http://localhost:8080`; Swagger: `http://localhost:8000/docs`.

**Lệnh nhóm đang dùng (không đổi khi M5 cải tiến):**
```bash
cp .env.example .env                      # Windows: copy .env.example .env
docker compose up --build
docker compose exec api alembic upgrade head
docker compose exec api python -m app.seed
docker compose exec api pytest
docker compose down -v                    # xóa luôn dữ liệu DB
```

**Biến môi trường:** theo `.env.example` trong quy ước; `.env` **không đưa lên Git**; ai thêm biến thì thêm vào `.env.example` **trong cùng lần commit**.

**Redis:** database 0 khi chạy thường, **database 1 khi chạy test**. **Test chạy trên database riêng `course_reg_test`**, không đụng dữ liệu demo.

**Kiểm thử:** `pytest` + `pytest-asyncio` (file `test_*.py` trong `backend/tests/`); Locust trong `loadtest/`; logic quan trọng phải có test (tiên quyết gồm bắc cầu và nhóm "hoặc"; đăng ký không vượt sĩ số/trùng/vượt tín chỉ/trùng lịch; waitlist đôn đúng thứ tự); **test tranh chấp**: nhiều yêu cầu vào lớp còn 1 chỗ thì đúng 1 người vào; **tải**: 2.000 sinh viên trong 30 giây (SR-NF-05).

**Git (M5 giữ kỷ luật chung):** nhánh `main` luôn chạy được; nhánh riêng `ten-tinhnang`; PR có người khác đọc và chạy thử; commit nhỏ, mô tả rõ; **checklist trước khi gộp (Mục 8 quy ước):** chạy được bằng `docker compose up`, đã format (ruff/Prettier), có test cho logic mới, không còn `print`/`console.log`/mật khẩu/`.env`, có Alembic migration nếu đổi bảng, cập nhật `.env.example` nếu thêm biến, đã có người đọc qua.

**Yêu cầu liên quan:** SR-NF-03 (OpenAPI đóng băng), SR-NF-05 (tải), SR-NF-07 (`docker compose up`, không cần internet), SR-NF-02 (dễ kiểm thử độc lập); tiêu chí nghiệm thu Mục 8 kế hoạch.

---

## Tuần 1 (Tuần 3 kế hoạch) — Docker Compose, khung `core/`, CI, khung test

**Mục tiêu:** Mọi thành viên chạy được toàn bộ hệ thống và test trên máy mình; CI bắt lỗi từ push đầu tiên.

### 1.1 Docker Compose (Ngày 1–2 — đường găng)
- [ ] `docker-compose.yml` với 5 dịch vụ đúng quy ước cổng: `nginx`, `web`, `api`, `db` (PostgreSQL 15), `redis` (Redis 7); **ghim tag phiên bản cụ thể** cho ảnh nền.
- [ ] **Healthcheck:** `db` bằng `pg_isready`, `redis` bằng `redis-cli ping`, `api` bằng `GET /health` (Mục 1.2); `depends_on` với `condition: service_healthy` để `api` chỉ khởi động khi DB/Redis sẵn sàng.
- [ ] Mã nguồn gắn vào container (bind mount) để **tải lại nóng** khi sửa code: `api` chạy `uvicorn --reload`, `web` chạy Vite dev server.
- [ ] **Lưu ý Windows/Docker Desktop (nhóm đang dùng `copy .env.example .env`):**
  - bind mount thường không phát hiện thay đổi file → bật polling (`WATCHFILES_FORCE_POLLING=true` cho uvicorn, `server.watch.usePolling` cho Vite khi chạy trong container);
  - thêm `.gitattributes` với `* text=auto eol=lf` và ép LF cho `*.sh`; nếu không, script khởi động bị `\r` và container báo lỗi khó hiểu;
  - `node_modules` của `web` đặt trong volume riêng để không lẫn với thư mục Windows.
- [ ] `volume` đặt tên cho dữ liệu PostgreSQL; `docker compose down -v` mới xóa.
- [ ] **DB `course_reg_test`:** `POSTGRES_DB` chỉ tạo một database → thêm script khởi tạo trong `docker-entrypoint-initdb.d` tạo `course_reg_test`; script này chỉ chạy lần đầu khi volume trống, nên thêm hướng dẫn tạo thủ công cho người đã có volume cũ (Mục 9, D24).
- [ ] **Nginx:** cổng 8080; `/` chuyển tới Vite (có hỗ trợ WebSocket cho HMR); `/api/` chuyển tới `api:8000` giữ nguyên đường dẫn `/api/v1/...` (khớp `VITE_API_BASE_URL=/api/v1`); đặt `X-Forwarded-For`, `X-Real-IP`, `X-Forwarded-Proto` (M4 cần để rate-limit đúng IP).
- [ ] `.env.example` đầy đủ theo quy ước, thêm `TEST_REDIS_URL` (Redis database 1) và các biến mới của nhóm khi được chốt.
- [ ] `.dockerignore`, `.gitignore` đúng (`.env`, `node_modules`, `__pycache__`, `.venv`, báo cáo tải).
- [ ] **Kiểm chứng:** một thành viên khác (M4 review) chạy từ đầu theo README trên máy sạch/Windows; sửa mọi chỗ vấp.

### 1.2 Khung `core/` dùng chung (Ngày 1–2)
Đề xuất M5 dựng (Mục 9, D17) để mọi người code theo "các file mẫu có sẵn trong repo" như quy ước nói:
- [ ] `backend/app/main.py`: khởi tạo FastAPI, đăng ký router (rỗng) dưới `/api/v1`, CORS đọc từ `CORS_ORIGINS`.
- [ ] `core/config.py`: đọc `.env` bằng Pydantic Settings; mọi giá trị cố định đi qua đây.
- [ ] `core/db.py`: engine + session **async** (SQLAlchemy), dependency `get_session`; cấu hình `pool_size`/`max_overflow` đọc từ biến môi trường (M3/M4 chỉnh sau).
- [ ] `core/redis.py`: client async dùng chung (đọc `REDIS_URL`, chọn database 1 khi chạy test); **M2, M3, M4 đều cần** — dựng sớm để không ai viết trùng.
- [ ] `core/errors.py`: bộ xử lý ngoại lệ đưa **mọi lỗi** về dạng chung `{ "detail": { "code", "message", ... } }` — kể cả lỗi kiểm tra dữ liệu mặc định của FastAPI (`{ "detail": [...] }`, dạng khác) và lỗi 500 (`INTERNAL_ERROR`, **không** lộ stack trace).
- [ ] `GET /health`: kiểm tra DB và Redis; dùng cho healthcheck của Compose.
- [ ] Cấu hình log ra stdout, không in mật khẩu/token.

### 1.3 CI (GitHub Actions) — chạy được từ ngày đầu
- [ ] Workflow `.github/workflows/ci.yml` chạy khi push và khi mở PR vào `main`:
  - **backend:** dịch vụ PostgreSQL 15 + Redis 7; `ruff check`, `ruff format --check`, `alembic upgrade head`, `alembic check` (khi M4 xong migration), `pytest`;
  - **frontend:** `npm ci`, ESLint, `prettier --check`, `tsc --noEmit`, build Vite (và test đơn vị khi M1 thêm — Mục 9, D22).
- [ ] Dùng giá trị từ `.env.example` trong CI, **không có bí mật thật**; cache `pip`/`npm` để chạy nhanh; ghim phiên bản Python 3.11 và Node LTS.
- [ ] **Bảo vệ nhánh `main`:** yêu cầu PR, CI xanh, tối thiểu một lượt duyệt; không push thẳng.
- [ ] **PR template:** chứa nguyên checklist Mục 8 quy ước, ô "có thay đổi hợp đồng API không?", ô "người review theo vòng".
- [ ] Quét bí mật (ví dụ gitleaks) ở CI và gợi ý `pre-commit` (ruff, Prettier, quét bí mật) để chặn commit nhầm `.env`/mật khẩu.
- [ ] Nhãn issue: `owner:M1…M5`, `type:bug|task|decision`, `severity:blocker|major|minor`, `week:1…7`.

### 1.4 Quản trị dự án: bảng tiến độ và nhật ký quyết định
- [ ] Dựng bảng (GitHub Projects): cột *Todo / Doing / Review / Done / Blocked*; tạo **mỗi sản phẩm bàn giao hàng tuần của mỗi thành viên thành một issue** (lấy từ file công việc M1–M5).
- [ ] Tạo `docs/decisions.md` từ **bảng Mục 9** của file này (28 điểm tổng hợp); đặt hạn cho từng điểm; theo dõi hằng ngày trong Tuần 1.
- [ ] Mẫu báo cáo tiến độ tuần: *đã xong / đang làm / bị chặn bởi ai / rủi ro mới / điểm cần chốt*.

### 1.5 Khung kiểm thử backend
- [ ] `pytest` cấu hình: `asyncio_mode = auto`, `pytest-timeout` (tránh test khóa treo vô hạn), `pytest-cov`; **marker:** `unit`, `integration`, `concurrency`, `stress`, `slow`, `e2e`.
- [ ] `backend/tests/conftest.py`:
  - đầu phiên: kết nối `TEST_DATABASE_URL`, chạy `alembic upgrade head` **một lần** (kiểm thử cả migration, không dùng `create_all`);
  - mỗi test: dọn dữ liệu (`TRUNCATE ... RESTART IDENTITY CASCADE`) và `FLUSHDB` Redis database 1; **không dùng rollback bọc ngoài**, vì test tranh chấp cần nhiều kết nối và commit thật;
  - `async_client` (httpx + ASGI), ghi đè dependency xác thực khi cần;
  - **hàm dựng dữ liệu (factory):** `make_student(role, max_credits)`, `make_course`, `make_offering(capacity, schedule)`, `add_prereq(course, prereq, type, group_no)`, `complete(student, course)`, `login_as(student)`;
  - tiện ích `run_concurrently(n, factory)`: mỗi tác vụ **một session riêng**, dùng rào chắn để tất cả xuất phát cùng lúc.
- [ ] Hướng dẫn viết test (`docs/test-guide.md`, 1 trang): đặt tên, dùng factory, đặt marker; để mọi người tự viết test cho phần của mình.
- [ ] Không chạy song song (xdist) trên cùng một DB — ghi rõ.

### Sản phẩm bàn giao cuối tuần
- `docker compose up` dùng được cho cả nhóm (đã thử trên Windows); `core/` mẫu; CI xanh; khung test + factory + hướng dẫn; bảng tiến độ và `docs/decisions.md`.

### Tiêu chí hoàn thành
- Một thành viên khác dựng được hệ thống từ máy sạch chỉ theo README, **trong 2 ngày đầu**.
- CI chạy trên PR đầu tiên của mỗi người; `main` được bảo vệ.

### Phối hợp
- **M1:** dịch vụ `web`, polling Vite, Vitest/Playwright (D22); **M2/M3:** `core/redis.py`, `core/db.py`, fixture; **M4:** `core/errors.py`, `core/config.py`, DB test, thêm migration vào CI.

---

## Tuần 2 (Tuần 4 kế hoạch) — Kế hoạch test, bất biến, nghiệm thu, hợp đồng, Locust nháp

**Mục tiêu:** Có "luật chơi" kiểm thử rõ ràng cho cả nhóm; bắt đầu đo được (SR-NF-03, tiêu chí nghiệm thu).

### 2.1 Kế hoạch kiểm thử (`docs/test-plan.md`)
- [ ] **Tháp kiểm thử:** đơn vị (logic thuần: engine tiên quyết, trùng lịch) → tích hợp (API + DB + Redis) → **bất biến** (sau tranh chấp) → hợp đồng (OpenAPI) → E2E (trình duyệt) → tải (Locust).
- [ ] Ai viết gì (mỗi người test logic của mình; M5 viết nghiệm thu/bất biến/tích hợp/hợp đồng/E2E/tải); quy ước đặt tên, marker, dữ liệu dùng chung.
- [ ] Ánh xạ **yêu cầu → test** (mỗi UR/SR có ít nhất một test hoặc phương pháp kiểm chứng đã nêu: *Kiểm thử / Thanh tra / Phân tích / Chứng minh*).
- [ ] Tiêu chí hoàn thành ở từng mức; chính sách xử lý **test không ổn định (flaky):** không tắt test, gắn nhãn, tìm nguyên nhân gốc trong 48 giờ.

### 2.2 Bộ bất biến — `find_invariant_violations`
**Nguồn sự thật duy nhất** cho "không vi phạm dữ liệu"; M3 dùng trong test tranh chấp, M4 dùng cho báo cáo toàn vẹn, M5 dùng sau mỗi lần chạy tải. Đặt tại `backend/app/tools/invariants.py`, có CLI `python -m app.tools.invariants` (thoát mã khác 0 nếu có vi phạm).

| # | Bất biến | Gắn với |
|---|---|---|
| I1 | `enrolled_count ≤ capacity` với mọi lớp | SR-NF-04 |
| I2 | `enrolled_count` = số đăng ký `ACTIVE` của lớp | SR-NF-04, SR-NF-05 |
| I3 | Không có hai đăng ký `ACTIVE` cùng `(student_id, offering_id)` | UR-F-04 |
| I4 | Với mỗi sinh viên và mỗi kỳ: tổng tín chỉ `ACTIVE` ≤ `max_credits` | UR-F-05 |
| I5 | Không có hai đăng ký `ACTIVE` của một sinh viên trùng lịch (theo quy tắc đã chốt) | SR-F-07 |
| I6 | Hàng chờ mỗi lớp: `position` liên tục 1…n, khớp thứ tự `(enqueued_at, id)` | SR-F-06 |
| I7 | Sinh viên không vừa `ACTIVE` vừa trong hàng chờ của cùng một lớp | UR-F-04 |
| I8 | Độ dài hàng chờ ≤ giới hạn theo `WAITLIST_MAX_RATIO` | SR-F-05 |
| I9 | Mọi đăng ký `ACTIVE` thỏa tiên quyết (đối chiếu bằng engine/oracle của M2) | SR-F-02 |
| I10 | Không có hai đăng ký `ACTIVE` của cùng một môn (khác lớp) trong cùng kỳ — **chỉ khi nhóm chốt quy tắc này** (D10) | UR-F-04 |

- [ ] Viết hàm trả danh sách vi phạm có mô tả; test chính hàm này (cố tình tạo dữ liệu sai để chắc nó bắt được).
- [ ] **Chỉ số "tỷ lệ ghi đúng sĩ số" (SR-NF-05)** được định nghĩa là: số lớp thỏa I1 và I2 / tổng số lớp, phải bằng 100%.

### 2.3 Bộ nghiệm thu tiên quyết (cùng M2)
- [ ] Lấy **bảng ca nghiệm thu** của M2 (21 ca + 5 ca chu trình, Mục 6.1 file M2) → viết file test tham số hóa chạy trên **đồ thị trong bộ nhớ**, không phụ thuộc seed.
- [ ] **Rà chéo từng ca với M2** (đây là "pairing review M2×M5" nêu ở phần rủi ro của kế hoạch); ghi rõ ca nào phụ thuộc quyết định "bắc cầu" (D04).
- [ ] Đưa vào CI: **thất bại thì chặn merge**.

### 2.4 Hợp đồng API (SR-NF-03)
- [ ] Script xuất OpenAPI từ ứng dụng (`app.openapi()`) → lưu **snapshot** `docs/openapi.json`; CI so sánh: thay đổi hợp đồng mà không cập nhật snapshot trong cùng PR → **thất bại**.
- [ ] Mọi PR đổi hợp đồng phải gắn nhãn `contract-change` và **thông báo M1** (nhiều điểm trong Mục 9 là thay đổi hợp đồng: D01–D03, D05–D07, D15).
- [ ] Kiểm tra hình dạng lỗi: mọi mã lỗi trong bảng (kể cả mã mới) có dạng `{ "detail": { "code", "message" } }`.

### 2.5 Locust bản nháp (`loadtest/`)
- [ ] `locustfile.py` chạy thử với **vài chục người dùng ảo** trên seed nhỏ: đăng nhập → tra cứu → kiểm tra tiên quyết → đăng ký → xem thời khóa biểu.
- [ ] Đọc tài khoản từ tệp do M4 xuất (Mục 4.1 file M4); **mỗi người dùng ảo một tài khoản riêng**.
- [ ] **Cách tính thành công/thất bại:** các kết quả nghiệp vụ hợp lệ (`201`, `200 WAITLISTED`, `409 ALREADY_ENROLLED`, `422 PREREQ_NOT_MET`…) **không phải lỗi hệ thống**; chỉ `5xx`, hết thời gian chờ, và vi phạm bất biến mới là thất bại (dùng `catch_response`).

### 2.6 Buổi review lần 1 (cuối Tuần 2)
- [ ] Chuẩn bị chương trình: tiến độ từng người so với file công việc; rủi ro; **các điểm Mục 9 còn mở**; quyết định cần chốt; ghi biên bản vào `docs/decisions.md`.

### Sản phẩm bàn giao cuối tuần
- `docs/test-plan.md`; `find_invariant_violations` + CLI + test; bộ nghiệm thu tiên quyết trong CI; snapshot OpenAPI + kiểm tra trong CI; Locust chạy thử được.

### Tiêu chí hoàn thành
- M3 dùng được `find_invariant_violations` cho test tranh chấp Tuần 3.
- CI chặn đúng các thay đổi hợp đồng chưa thông báo.
- Hơn một nửa số điểm Mục 9 đã có quyết định.

### Phối hợp
- **M2:** bảng ca nghiệm thu; **M3:** bất biến, vector trùng lịch; **M4:** tài khoản tải, xuất seed; **M1:** hợp đồng, Vitest/Playwright.

---

## Tuần 3 (Tuần 5 kế hoạch) — Pipeline tích hợp, hợp đồng, phân quyền, hạ tầng E2E

**Mục tiêu:** Mỗi PR được kiểm tra **tích hợp thật** (API + DB + Redis); chuẩn bị nền cho E2E và tải.

### 3.1 Pipeline kiểm thử tích hợp
- [ ] Job CI dựng DB trống → `alembic upgrade head` → seed hồ sơ **rất nhỏ** (do M4) → chạy `pytest -m "integration or concurrency"`; ghi kết quả và độ bao phủ.
- [ ] Chạy test với Redis thật (database 1); kiểm tra cả khi **Redis bị tắt** (hợp tác M2/M3: test phải xanh).
- [ ] **Thời gian CI hợp lý** (mục tiêu vài phút cho mỗi lần): tách job song song, cache, chỉ chạy bộ "stress" khi cần (Mục 3.4).
- [ ] Báo cáo bao phủ cho `services/`; **mức tối thiểu chốt cùng nhóm** (đề xuất thiết lập sau khi có số liệu đầu tiên, không đặt con số tùy ý).

### 3.2 Ma trận phân quyền tự động
- [ ] Lấy danh sách endpoint **từ OpenAPI**; với mỗi endpoint: chưa đăng nhập → 401; sinh viên gọi `/admin/*` → 403; token hết hạn → `TOKEN_EXPIRED`; admin → được. Endpoint mới thêm sau **tự được kiểm tra** mà không phải viết lại.
- [ ] **IDOR:** sinh viên A không xóa được đăng ký/hàng chờ của sinh viên B, không hỏi `check`/`explain` hộ người khác (cùng M4).

### 3.3 Hợp đồng giữa frontend và backend
- [ ] Kiểm tra **các phản hồi giả (MSW) của M1 khớp OpenAPI** (kiểm tra schema tự động) — chặn sớm rủi ro "lệch hợp đồng giữa FE và BE" của kế hoạch.
- [ ] Hỗ trợ M1 chuyển sang API thật (M1 làm trong tuần này): chạy cùng nhau và ghi mọi chỗ lệch thành issue gắn đúng owner.

### 3.4 Chuẩn bị tải và các job định kỳ
- [ ] **Môi trường tải tách biệt:** database riêng (ví dụ `course_reg_loadtest`), **Redis database 2**, seed hồ sơ tải ≥ 2.000 sinh viên (D23); script `reset-loadtest` dựng lại từ đầu trước mỗi lần chạy. Không dùng chung với DB demo hay DB test.
- [ ] Dịch vụ `locust` trong Compose (profile `loadtest`) chạy headless, xuất CSV/HTML vào `loadtest/reports/` (không commit báo cáo lớn).
- [ ] Mở rộng kịch bản Locust (Mục 4.1) và kiểm chứng trên quy mô vài trăm người dùng.
- [ ] Job **định kỳ hằng đêm** (`schedule`): chạy bộ test tranh chấp **lặp 20 lần**, quét thư viện (`pip-audit`, `npm audit`, không chặn merge ở giai đoạn đầu), quét bí mật.

### 3.5 Hạ tầng E2E (cùng M1)
- [ ] Chốt Playwright (D22); thư mục `frontend/e2e/` do M5 dựng hạ tầng, **M1 viết các luồng**.
- [ ] Cách **đặt lại dữ liệu trước mỗi kịch bản** (script chạy seed nhỏ, ổn định, nhanh); tài khoản kịch bản cố định do M4 cung cấp.
- [ ] Job CI E2E chạy trên profile giống production (tuần 6 mới bắt buộc xanh); lưu ảnh chụp/trace khi thất bại.

### Sản phẩm bàn giao cuối tuần
- CI tích hợp + hợp đồng + ma trận phân quyền chạy trên mỗi PR; kiểm tra MSW khớp OpenAPI; môi trường và script tải; hạ tầng E2E; job định kỳ.

### Tiêu chí hoàn thành
- Mỗi PR vào `main` được kiểm tra tích hợp tự động; thay đổi hợp đồng không báo trước bị chặn.
- Chạy được kịch bản tải thử vài trăm người dùng trên môi trường tách biệt và kiểm tra bất biến sau khi chạy.

### Phối hợp
- **M1:** chuyển API thật, MSW so với OpenAPI, E2E; **M2/M3:** test với Redis tắt/bật; **M4:** ma trận phân quyền, hồ sơ seed.

---

## Tuần 4 (Tuần 6 kế hoạch) — Spike test 2.000 người dùng (baseline), bug bash

**Mục tiêu:** Có **số liệu baseline** đáng tin cậy và danh sách lỗi hệ thống (SR-NF-05; kịch bản "2.000 sinh viên trong 30 giây").

### 4.1 Kịch bản tải
- [ ] **Giai đoạn chuẩn bị:** đăng nhập trước toàn bộ 2.000 người dùng (có kiểm soát tốc độ) và giữ token — đăng nhập tốn CPU băm mật khẩu và là thao tác khác với khoảnh khắc "mở đăng ký"; đo riêng và báo cáo riêng.
- [ ] **Spike mở đăng ký:** 2.000 người dùng ảo xuất phát trong 30 giây (`LoadTestShape`, tốc độ khởi tạo ~67 người/giây), tập trung vào nhóm lớp "nóng" (vài chục lớp có ít chỗ so với nhu cầu, trong đó có vài lớp chỉ 1–5 chỗ); mỗi người: tra cứu → kiểm tra tiên quyết → `POST /enroll` → xem thời khóa biểu.
- [ ] **Cơn bão hủy:** một phần người dùng hủy đồng loạt → kiểm tra đôn waitlist chạy đúng dưới tải.
- [ ] **Kịch bản đọc nhiều** (tra cứu/lọc liên tục) để đo UR-NF-07.
- [ ] Có một ca **"tất cả vào cùng 5 lớp"** — cực đoan nhất cho tranh chấp.

### 4.2 Quy trình đo (để kết quả so sánh được)
- [ ] Chạy trên **cấu hình giống production** (không `--reload`, nhiều worker — dùng profile `prod` nếu đã có hoặc bản tạm), cùng máy, cùng bộ dữ liệu; ghi cấu hình máy (CPU/RAM/Docker Desktop).
- [ ] **Chạy ít nhất 3 lần**, báo cáo trung vị và dải; đặt lại môi trường (`reset-loadtest`) trước mỗi lần.
- [ ] Đo: P50/P95/P99 từng endpoint, số yêu cầu/giây, tỷ lệ lỗi theo nhóm mã (`2xx`/`4xx` nghiệp vụ/`5xx`/hết thời gian), số `CONCURRENT_UPDATE`, số `WAITLISTED`/`WAITLIST_FULL`; trạng thái DB khi chạy (`pg_stat_activity`, khóa chờ), CPU/RAM container (`docker stats`).
- [ ] **Sau mỗi lần chạy** chạy `python -m app.tools.invariants`: **tỷ lệ ghi đúng sĩ số phải bằng 100%** (và không có vi phạm I1–I9).
- [ ] **Ngưỡng "P95 chấp nhận được"** kế hoạch chưa nêu số: M5 **đề xuất sau khi có baseline** (ví dụ: tỷ lệ `5xx` = 0, P95 của `/enroll` trong ngưỡng nhóm đồng ý — gợi ý khởi điểm ~2 giây, điều chỉnh theo thực tế); cả nhóm chốt (D28).

### 4.3 Bug bash (cuối tuần, khoảng 60–90 phút, cả 5 người)
- [ ] Chuẩn bị **danh sách kịch bản** (từ file công việc từng người), tài khoản demo và dữ liệu sạch; mỗi người thử theo vai trò sinh viên/admin trên giao diện thật.
- [ ] Ghi lỗi thành issue với: các bước tái hiện, kết quả mong đợi/thực tế, ảnh chụp, mức độ (`blocker/major/minor`), owner.
- [ ] Phân loại cuối buổi: lỗi nào phải sửa trước Tuần 5 (M1 sửa UX theo kết quả; M2/M3/M4 sửa theo báo cáo tải).

### 4.4 Báo cáo baseline và review lần 2
- [ ] Bản nháp **báo cáo tải baseline** (bảng + biểu đồ + nhận xét điểm nghẽn); gửi M2, M3, M4 để họ có căn cứ tối ưu Tuần 5.
- [ ] Buổi review lần 2 (cuối tuần): tiến độ, kết quả tải, lỗi bug bash, quyết định còn mở.

### Sản phẩm bàn giao cuối tuần
- Số liệu baseline có thể tái lập; kịch bản tải hoàn chỉnh; danh sách lỗi bug bash; ngưỡng đề xuất; biên bản review.

### Tiêu chí hoàn thành
- Chạy được spike 2.000 người dùng đến hết mà không sập hệ thống; có số liệu cho cả 3 lần chạy.
- Mọi lỗi nghiêm trọng được gán owner và hạn sửa.

### Phối hợp
- **M2, M3, M4:** báo cáo baseline, ngưỡng, rate-limit không chặn nhầm tải (`APP_ENV=loadtest`); **M1:** kết quả UX khi tải.

---

## Tuần 5 (Tuần 7 kế hoạch) — Chạy lại tải, so sánh trước/sau, xử lý test không ổn định

**Mục tiêu:** Chứng minh **cải thiện có số liệu** sau tối ưu (báo cáo "trước/sau" mà kế hoạch yêu cầu).

### 5.1 Chạy lại tải và so sánh
- [ ] Khi M2 (N+1, cache hit), M3 (Redis lock, pool), M4 (chỉ mục, cấu hình DB), M1 (UX) báo đã tối ưu: **chạy lại đúng kịch bản baseline** (cùng dữ liệu, cùng cấu hình máy, ≥ 3 lần).
- [ ] Bảng **trước/sau** theo từng chỉ số (P95, tốc độ xử lý, tỷ lệ lỗi, `CONCURRENT_UPDATE`, tỷ lệ cache hit từ M2, tỷ lệ ghi đúng sĩ số); ghi rõ **thay đổi nào gây ra cải thiện nào** (hỏi từng người ghi lại), tránh kết luận chung chung.
- [ ] Nếu kết quả không cải thiện/xấu đi: phối hợp phân tích (đo từng thay đổi riêng), không âm thầm bỏ qua.
- [ ] Gộp **số liệu trước/sau do M2 và M3 tự đo** vào cùng bảng.

### 5.2 Độ ổn định của bộ test
- [ ] Xem kết quả job hằng đêm (lặp 20 lần): với mỗi test đỏ ngẫu nhiên → issue `flaky`, tìm nguyên nhân gốc cùng chủ test (thường là thứ tự khóa, thời gian chờ, dọn dữ liệu); sửa trước khi đóng băng.
- [ ] Rà thời gian CI; loại phần chậm không cần thiết.

### 5.3 Kiểm thử bảo mật phối hợp M4
- [ ] Biến các lỗ hổng M4 tìm được thành **test tự động** trong CI (IDOR, quyền, rate-limit, dùng lại refresh token).
- [ ] Rà `pip-audit`/`npm audit`; ghi kết quả cho báo cáo bảo mật.

### 5.4 Bản nháp báo cáo tải
- [ ] Cấu trúc: mục tiêu (SR-NF-05); môi trường; kịch bản; baseline; các tối ưu; kết quả trước/sau; bất biến sau tải; hạn chế; kết luận. Điền trước các phần đã có số liệu.

### Sản phẩm bàn giao cuối tuần
- Bảng trước/sau; danh sách test không ổn định đã xử lý; test bảo mật tự động; bản nháp báo cáo tải.

### Tiêu chí hoàn thành
- Có số liệu so sánh có thể tái lập; **tỷ lệ ghi đúng sĩ số = 100%** ở mọi lần chạy.
- Không còn test không ổn định chưa có nguyên nhân.

### Phối hợp
- **M2, M3, M4:** thông báo từng thay đổi tối ưu; **M1:** E2E cho các luồng đã sửa UX.

---

## Tuần 6 (Tuần 8 kế hoạch) — Docker prod profile, E2E smoke, CI xanh, đóng băng

**Mục tiêu:** Một lệnh `docker compose up` dựng được bản demo ổn định, **không cần internet** (SR-NF-07); CI xanh, tính năng đóng băng.

### 6.1 Docker production profile
- [ ] Profile `prod` trong Compose (dev mặc định không đổi): 
  - **web:** build nhiều giai đoạn (Node build → Nginx phục vụ tệp tĩnh), SPA fallback (`try_files` → `index.html`), nén gzip, cache tệp có hash tên;
  - **api:** ảnh gọn, chạy **người dùng không phải root**, **không `--reload`**, nhiều worker (số đọc từ biến môi trường), `APP_ENV=prod`;
  - **chỉ mở cổng 8080** ra ngoài; **không công khai cổng `db` và `redis`**; Redis đặt mật khẩu nếu mở; dữ liệu DB trên volume;
  - Nginx: tiêu đề bảo mật (`X-Content-Type-Options`, `X-Frame-Options`, CSP cơ bản — phối hợp M4/M1), giới hạn kích thước body, thời gian chờ hợp lý, chuyển `/api/` về `api`, **chỉ tin IP từ chính Nginx này**.
- [ ] **Một lệnh dựng demo (SR-NF-07):** dịch vụ chạy một lần `alembic upgrade head` và seed **khi DB còn trống** (D24); healthcheck cho mọi dịch vụ; `restart: unless-stopped`.
- [ ] Tùy chọn: tắt Swagger `/docs` ở `prod` (phối hợp M4).
- [ ] **Script đặt lại demo nhanh** (`down -v` → `up` → seed) và script `reset-loadtest`.

### 6.2 Chạy offline (SR-NF-07)
- [ ] Khi còn mạng: `docker compose --profile prod build` và kéo mọi ảnh về máy demo; kiểm tra **ảnh đã có sẵn trong bộ nhớ cục bộ**.
- [ ] **Ngắt mạng rồi chạy lại từ đầu** (`down -v` → `up`): ứng dụng phải chạy đầy đủ; kiểm tra không có CDN/font/ảnh ngoài (nhắc M1), không bước nào gọi internet lúc chạy.
- [ ] Thử trên **máy demo thật** và trên một máy sạch khác; ghi thời gian từ lệnh đến khi dùng được.

### 6.3 E2E smoke cùng M1 và CI xanh
- [ ] Các luồng M1 liệt kê (đăng nhập → tra cứu → xem trước → trùng lịch; đăng ký thành công; thiếu tiên quyết; lớp đầy → waitlist → hủy → được đôn; vượt tín chỉ; admin thêm môn + tiên quyết, sinh viên không vào được `/admin`; hết phiên) → **chạy tự động trong CI**, **bắt buộc xanh**.
- [ ] CI xanh: lint, test, tích hợp, hợp đồng, **bất biến (chặn merge khi thất bại)**, E2E. Biến E2E và bộ nghiệm thu thành điều kiện bắt buộc của `main`.
- [ ] **Đóng băng tính năng:** chỉ nhận PR sửa lỗi; gắn nhãn `freeze`.

### 6.4 Kiểm tra cuối từng thành phần
- [ ] Danh sách chung "sẵn sàng bảo vệ" (từ tiêu chí nghiệm thu Mục 8 kế hoạch): engine tiên quyết 100% (bộ nghiệm thu), spike test không vượt sĩ số, trùng lịch tức thời không dương/âm tính giả, waitlist đôn đúng, `docker compose up` một lệnh, mỗi người thuyết minh được phần mình. Kiểm từng mục cùng người phụ trách.
- [ ] Buổi review lần 3.

### Sản phẩm bàn giao cuối tuần
- Profile `prod` chạy offline; E2E smoke xanh trong CI; `main` đóng băng với CI xanh; danh sách "sẵn sàng bảo vệ" đã tick.

### Tiêu chí hoàn thành
- Từ máy sạch (không mạng, ảnh đã có), một lệnh dựng được ứng dụng và đăng nhập được.
- Không còn lỗi mức nghiêm trọng đang mở.

### Phối hợp
- **M1:** E2E, tài nguyên không phụ thuộc internet, SPA qua Nginx; **M4:** bảo mật Nginx, seed khi trống; **M2, M3:** chốt test nghiệm thu/tranh chấp trong CI.

---

## Tuần 7 (Tuần 9 kế hoạch) — Báo cáo tải cuối, tài liệu tổng hợp, hậu cần bảo vệ

**Mục tiêu:** Nộp bộ tài liệu hoàn chỉnh; buổi bảo vệ trơn tru.

### 7.1 Báo cáo tải cuối (SR-NF-05)
- [ ] Hoàn thiện từ bản nháp Tuần 5: số liệu cuối trên phiên bản đóng băng; bảng trước/sau; kết quả bất biến; môi trường; hạn chế; biểu đồ.
- [ ] Chạy một lần **xác nhận cuối** trên bản `main` đã đóng băng và ghi kết quả.

### 7.2 Tài liệu tổng hợp cuối kỳ
- [ ] Thu từ các thành viên: M1 (frontend), M2 (`docs/prerequisite-engine.md`), M3 (`docs/enrollment-design.md`), M4 (`docs/database.md`, `docs/security.md`), M5 (kế hoạch test, báo cáo tải).
- [ ] **Sơ đồ phụ lục (PlantUML trong `docs/`):** Use Case (Hình 1), ERD (Hình 2, M4 cập nhật cho khớp DDL), kiến trúc (Hình 3), tuần tự đăng ký học phần (Hình 4), tuần tự kiểm tra tiên quyết (Hình 5), hoạt động waitlist (Hình 6), lớp domain (Hình 7). **Cập nhật cho khớp các quyết định đã chốt** (D01–D29: ví dụ mã lỗi mới, `DELETE /waitlist`, `PREREQ_CYCLE`); xuất ảnh sẵn (không phụ thuộc mạng khi mở).
- [ ] Rà **tính nhất quán** giữa kế hoạch gốc, quy ước và sản phẩm thực tế: cập nhật bảng mã lỗi, khóa Redis (Mục 7 quy ước), danh sách endpoint, biến môi trường; ghi rõ những gì **khác kế hoạch ban đầu** và lý do.
- [ ] Bố cục báo cáo cuối kỳ đề xuất: giới thiệu & yêu cầu → kiến trúc → thiết kế CSDL (M4) → engine tiên quyết (M2) → đăng ký & tranh chấp (M3) → frontend (M1) → bảo mật (M4) → kiểm thử & tải (M5) → kết quả so với tiêu chí nghiệm thu → rủi ro & bài học.
- [ ] `README.md` gốc: giới thiệu, yêu cầu cài đặt, chạy nhanh, tài khoản demo, cách chạy test, cách đặt lại demo, xử lý sự cố thường gặp (cổng bận, volume cũ, Windows LF/polling).

### 7.3 Hậu cần buổi bảo vệ
- [ ] **Thứ tự thuyết minh** và thời lượng từng người (M1 → M5 hoặc theo luồng sản phẩm); chuyển phần mượt; kịch bản demo chung nối các đoạn của từng người (mỗi người đã có kịch bản riêng).
- [ ] **Danh sách kiểm tra trước ngày bảo vệ:** máy demo cài sẵn, ảnh Docker đã build, cổng 8080/5173/8000/5433/6380 rảnh, `docker compose --profile prod up` đã thử offline, DB đặt lại về dữ liệu demo, tài khoản demo hoạt động, sạc/dây/chuyển đổi hình, slide đã gộp thành một bộ.
- [ ] **Phương án dự phòng:** video quay màn hình toàn bộ demo, ảnh chụp từng bước, máy dự phòng cài sẵn, bản mã nguồn và slide trên USB.
- [ ] **Diễn tập toàn nhóm ít nhất 2 lần** có bấm giờ; luyện câu hỏi chéo (mỗi người có thể trả lời cơ bản về phần của người khác).
- [ ] Gắn tag phiên bản cuối trên `main` sau khi kiểm tra lần cuối.

### Sản phẩm bàn giao
- Báo cáo tải cuối; bộ tài liệu tổng hợp + sơ đồ; README; kịch bản demo chung; bản dự phòng; danh sách kiểm tra.

---

## 8. Ánh xạ yêu cầu → công việc của M5

| Yêu cầu | Nội dung | Làm ở |
|---|---|---|
| SR-NF-02 | Mã nguồn dễ kiểm thử độc lập; khung test và fixture | Tuần 1 |
| SR-NF-03 | OpenAPI đóng băng; kiểm thử hợp đồng | Tuần 2–3 |
| SR-NF-04 | Không race condition: bất biến + test tranh chấp trong CI | Tuần 2, 3, 6 |
| SR-NF-05 | Spike 2.000 sinh viên trong 30 giây; tỷ lệ ghi đúng sĩ số 100%; P95 | Tuần 4–5, 7 |
| SR-NF-07 | `docker compose up` một lệnh, không phụ thuộc internet | Tuần 1, 6 |
| SR-F-02 (kiểm chứng) | Engine đúng 100% trên bộ nghiệm thu | Tuần 2, 6 |
| UR-NF-06/07 (kiểm chứng) | Cảnh báo trùng lịch tức thì; tra cứu đủ nhanh (E2E và tải) | Tuần 3–6 |
| Tiêu chí nghiệm thu (Mục 8 kế hoạch) | Danh sách "sẵn sàng bảo vệ" | Tuần 6 |
| Rủi ro "lệch hợp đồng FE–BE" | Snapshot OpenAPI, MSW so với OpenAPI | Tuần 2–3 |
| Rủi ro "race condition" | Bất biến chạy trong CI, spike test | Tuần 2–6 |

---

## 9. Bảng tổng hợp các điểm cần chốt toàn nhóm

Các file M1–M4 đều có mục "điểm cần chốt" riêng; có nhiều điểm **trùng nhau**. M5 giữ danh sách hợp nhất dưới đây, sao thành `docs/decisions.md` và theo dõi đến khi chốt. **Hạn:** "T1" = trong 2 ngày đầu Tuần 1 (vì chặn việc làm ngay); "T1 cuối" = hết Tuần 1; "T2" = hết Tuần 2.

Nguồn ghi theo mẫu *M1-2* = điểm 2 trong Mục 9 của file M1.

| ID | Nội dung cần chốt | Nguồn | Chủ trì | Hạn | Đề xuất |
|---|---|---|---|---|---|
| D01 | Endpoint tra cứu `/courses` hay `/courses/search`; tên tham số lọc (`q, section, credits, instructor, day, from, to, term`) | M1-1, M3-1 | M3 | T1 | `/courses` theo quy ước |
| D02 | `explain` dùng `GET` hay `POST` | M1-2, M2-2 | M2 | T1 | `POST` (body `course_id`) |
| D03 | Schema JSON của `explain` | M1-3, M2-3 | M2 + M1 | T1 | Dùng bản nháp ở Mục 1.1(d) file M2 |
| D04 | Ngữ nghĩa "bắc cầu": đã học là đủ, hay mọi tổ tiên đều phải có | M2-1 | M2 + M5 | T1 | "Đã học là đủ" |
| D05 | `GET /timetable` trả gì; nơi chứa `max_credits` (login hay timetable) | M1-4, M3-3, M4-5 | M3 + M1 | T1 | `/timetable` trả `total_credits`, `max_credits` |
| D06 | Cách vào hàng chờ: `/enroll` tự đưa vào hay có `POST /waitlist` xác nhận | M1-5, M3-9 | M3 + M1 | T1 | `/enroll` trả `200 WAITLISTED` (theo quy ước) |
| D07 | Thêm `DELETE /waitlist/{id}` vào hợp đồng | M3-10 | M3 | T1 | Thêm |
| D08 | Quy tắc nghỉ giữa hai ca; biến `MIN_BREAK_MINUTES` | M1-6, M3-6 | M3 + M1 | T1 | Mặc định `0` (liền kề không trùng); FE theo cùng quy tắc |
| D09 | `Idempotency-Key` gửi ở header hay body | M1-10, M3-2 | M3 + M1 | T1 | Header |
| D10 | Thứ tự kiểm tra lỗi; chặn đăng ký hai lớp cùng môn trong kỳ; môn đã học xong có đăng ký lại không | M3-5, M2-9 | M3 | T1 cuối | Thứ tự: đã đăng ký → tiên quyết → trùng lịch → tín chỉ → sĩ số; chặn cùng môn; không cho đăng ký lại môn đã đạt |
| D11 | Người đầu hàng chờ không còn đủ điều kiện: giữ chỗ hay xóa khỏi hàng | M3-6 | M3 + M1 | T2 | Giữ chỗ, `GET /waitlist` trả `blocked_reason` |
| D12 | Giới hạn waitlist: `ceil` hay `floor` của `sĩ số × WAITLIST_MAX_RATIO` | M3-7 | M3 | T2 | `ceil` |
| D13 | `check` trả `200` + `eligible=false` hay `422`; tham số `course_id` | M2-8, M2-10 | M2 + M3 | T1 | `200`; tham số `course_id` |
| D14 | Điểm tối thiểu: `completed_courses` chỉ có môn đạt, engine không xét điểm | M2-11 | M2 | T1 cuối | Không xét điểm |
| D15 | **Mã lỗi mới:** `PREREQ_CYCLE`, `WAITLIST_FULL`, `ALREADY_WAITLISTED`, `RATE_LIMITED` (429), `ALREADY_EXISTS`, `IN_USE`, `VALIDATION_ERROR`, `INTERNAL_ERROR` — cập nhật Mục 5 quy ước và bảng lỗi của M1 | M2-4, M3-4, M4-4 | M5 | T1 cuối | Thêm tất cả |
| D16 | **Khóa Redis mới:** `prereqgraph:v1`, `metrics:prereq:*`, `idem:enroll:*`, `refresh:*`, `ratelimit:*`; **Redis database 2 cho tải** — cập nhật Mục 7 quy ước | M2-5, M3-8, M4-3 | M5 | T1 cuối | Thêm; khóa đồ thị không dùng tiền tố `prereq:` |
| D17 | Ai dựng khung `core/` (`db`, `redis`, `errors`, `config`, `main`) | M2-6, M4-11 | M5 | T1 | M5 dựng Ngày 1–2; `core/security.py` do M4 |
| D18 | Nơi gọi invalidation khi `completed_courses`/DAG đổi | M2-7 | M4 + M2 | T2 | Seed/import và admin gọi hàm của M2 |
| D19 | Nơi lưu token ở frontend (cookie `HttpOnly` hay `localStorage`) | M1-7, M4-1 | M4 + M1 | T1 cuối | Cookie nếu kịp, ngược lại `localStorage` + ghi rủi ro |
| D20 | Có cần đăng ký tài khoản công khai (`/auth/register`) | M4-2 | M4 | T1 cuối | Không |
| D21 | Import seed qua giao diện admin | M1-8, M4-8 | M4 + M1 | T2 | Không |
| D22 | Công cụ test: Vitest (FE đơn vị), Playwright (E2E), TanStack Query, `hypothesis` | M1-9, M2-12 | M5 + nhóm | T1 cuối | Đồng ý Vitest và Playwright; còn lại tùy |
| D23 | Seed hồ sơ tải ≥ 2.000 sinh viên (mỗi người dùng ảo một tài khoản) và DB tải riêng | M4-7 | M4 + M5 | T2 | Đồng ý |
| D24 | Tạo DB `course_reg_test`; "một lệnh `docker compose up`" so với lệnh migrate/seed thủ công | M4-9, M4-10 | M5 | T1 | Script khởi tạo; profile `prod` tự migrate/seed khi trống |
| D25 | Hiệu suất đôn waitlist không đo được từ dữ liệu | M3-12, M4-6 | M3 + M5 | T2 | Log có cấu trúc + số liệu Locust |
| D26 | Router `timetable.py` (chưa có trong cấu trúc quy ước) | M3-11 | M3 | T1 | Thêm |
| D27 | (Tùy chọn) `CHECK (jsonb_typeof(schedule) = 'array')` cho `course_offerings` | M4-12 | M4 | T2 | Làm nếu cả nhóm đồng ý |
| D28 | Ngưỡng "P95 chấp nhận được" và các mức tối thiểu (độ bao phủ test) | M5 | M5 + nhóm | Sau baseline (Tuần 4) | Đặt dựa trên số liệu thực, không đặt trước |
| D29 | Số sinh viên và kịch bản tải: "2.000 người dùng/30 giây" tính từ lúc nào (sau khi đã đăng nhập) | M5 | M5 | T2 | Đăng nhập trước, đo spike từ lúc bắt đầu đăng ký |

**Khi một điểm được chốt:** ghi vào `docs/decisions.md` (ngày, người chốt, quyết định); nếu liên quan hợp đồng thì cập nhật OpenAPI và gắn nhãn `contract-change`; thông báo người bị ảnh hưởng (thường là M1).

---

## 10. Rủi ro riêng của M5 và cách giảm thiểu

| Rủi ro | Biện pháp |
|---|---|
| Môi trường Docker không chạy trên một số máy (đặc biệt Windows) làm cả nhóm bị chặn | Ưu tiên tuyệt đối Ngày 1–2; thử trên Windows; ghi sẵn cách xử lý (LF, polling, cổng bận, volume cũ) trong README |
| CI chậm hoặc hay đỏ làm cả nhóm né CI | Cache, tách job, xử lý test không ổn định trong 48 giờ, không tắt test; theo dõi thời gian CI |
| Số liệu tải không tái lập hoặc không so sánh được trước/sau | Môi trường tách biệt, cấu hình giống production, ≥ 3 lần chạy, ghi cấu hình máy, bộ dữ liệu cố định |
| Rate-limit hoặc đăng nhập (băm mật khẩu) làm hỏng kết quả tải | Đăng nhập trước, chế độ nới rate-limit cho môi trường tải (`APP_ENV=loadtest`), đo riêng từng giai đoạn |
| Các điểm cần chốt kéo dài làm FE/BE lệch hợp đồng | Danh sách hợp nhất (Mục 9) có hạn từng điểm; snapshot OpenAPI + nhãn `contract-change`; kiểm tra MSW so với OpenAPI |
| Demo không chạy khi không có internet | Build và kéo ảnh sẵn; **thử ngắt mạng** từ Tuần 6; bản dự phòng (video/ảnh) |
| M5 quá tải vì vừa làm hạ tầng, vừa theo dõi nhóm, vừa viết test | Mỗi người tự viết test cho phần mình (đã thống nhất); M5 ưu tiên đường găng (Compose, CI, bất biến, tải); dùng mẫu và script để giảm lặp lại |
| Chậm tiến độ | Cặp dự phòng chéo (ví dụ M5 hỗ trợ M2 trong bộ nghiệm thu, M4 duyệt PR của M5); báo sớm ở buổi review 2 tuần/lần; nếu thiếu thời gian, cắt kịch bản tải phụ và bộ job định kỳ trước, **không cắt** bất biến, spike test baseline và kiểm tra offline |
