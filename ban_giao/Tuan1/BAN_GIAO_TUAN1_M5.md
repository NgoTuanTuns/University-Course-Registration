# Bàn giao Tuần 1 — M5 (QA Engineer & DevOps)

**Dự án:** Hệ thống Đăng ký Học phần & Kiểm tra Điều kiện Tiên quyết  
**Người bàn giao:** M5  |  **Ngày cập nhật:** 05/11/2026  |  **Căn cứ:** `chitietcongviec/M5_cong_viec_7_tuan.md` và `chitietcongviec/QUY_UOC_DU_AN.md`  
**Nhánh:** `trung-devops-compose-ci`  |  **Pull request:** #3 — chưa merge vào `main`

> **Trạng thái chung: ĐANG LÀM — chưa hoàn tất Tuần 1, kể cả khi tạm bỏ qua việc M4 review.** Nền tảng Compose, `core/`, CI và test đã được thêm vào PR. Đã xác nhận chạy `db`, `redis`, `api`, migration và seed. Chưa xác nhận chạy đủ 5 dịch vụ, CI lint/test, khung test và GitHub Project trên môi trường sạch.

---

## 1. Tóm tắt

Tuần 1 của M5 dựng môi trường chung để cả nhóm chạy ứng dụng, migration, seed và test bằng Docker Compose; đồng thời tạo CI, khung `core/`, khung test và tài liệu phối hợp.

**Đã làm:**
1. Thêm cấu hình Docker Compose, Dockerfile, Nginx và cấu hình hot reload/polling vào PR #3.
2. Thêm/cập nhật backend `core/`, endpoint health, cấu hình lỗi và cấu hình môi trường.
3. Thêm workflow CI, PR template, fixture/test utilities và hướng dẫn test.
4. Bạn đã chạy được các container `db`, `redis`, `api`; chạy migration và seed thành công. Seed báo 1.001 sinh viên, 200 học phần, 357 lớp học phần, 12.668 môn đã hoàn thành, 53 lượt đăng ký và 3 hàng chờ.
5. PR hiện báo **All checks have passed**, trong đó **GitGuardian là check bị skipped** sau khi được gắn nhãn test credential. Điều này không chứng minh các job lint/test đã chạy thành công.

**Còn thiếu:** xác nhận toàn bộ `nginx`/`web`/`api`/`db`/`redis` chạy cùng nhau; xác nhận job CI backend/frontend; chạy khung test; dựng GitHub Project; M4 chạy thử và review PR.

---

## 2. Danh sách bàn giao

| File/nhóm file trong PR | Nội dung | Trạng thái |
|---|---|---|
| `docker-compose.yml`, `Dockerfile.api`, `Dockerfile.web` | Khung Compose và image cho các dịch vụ | Đã thêm; chỉ `db`, `redis`, `api` được xác nhận chạy |
| `nginx/default.conf`, `vite.docker.config.ts` | Reverse proxy và cấu hình Vite trong container | Đã thêm; chưa xác nhận smoke test toàn bộ UI |
| `.env.example`, `.dockerignore`, `.gitattributes`, `.gitignore` | Mẫu môi trường, bỏ qua file và chuẩn LF | Đã thêm |
| `backend/app/core/config.py`, `db.py`, `redis.py`, `errors.py`; `backend/app/main.py` | Cấu hình dùng chung, DB/Redis, lỗi API, app và health endpoint | Đã thêm; API đã khởi động |
| `backend/tests/conftest.py`, `backend/pyproject.toml`, `backend/docs/test-guide.md` | Fixture, cấu hình pytest/ruff và hướng dẫn test | Đã thêm; chưa xác nhận chạy pytest thành công |
| `backend/requirements.txt` | Bổ sung dependency cho settings và test | Đã cập nhật |
| `.github/workflows/ci.yml`, `.github/pull_request_template.md` | CI và checklist PR | Đã thêm; trạng thái lint/test chưa xác nhận |
| `docs/decisions.md`, `docs/dev-environment.md`, `docs/project-board-setup.md`, `docs/weekly-status-template.md` | Nhật ký quyết định, hướng dẫn môi trường và quản trị | Đã thêm; GitHub Project chưa xác nhận được tạo |

---

## 3. Cách dùng cho nhóm

Theo quy ước nhóm, từ thư mục gốc repo:

```powershell
copy .env.example .env
docker compose up --build
```

Mở terminal thứ hai để khởi tạo database và dữ liệu mẫu:

```powershell
docker compose exec api alembic upgrade head
docker compose exec api python -m app.seed
```

Các địa chỉ theo quy ước:
- Ứng dụng qua Nginx: `http://localhost:8080`
- Swagger: `http://localhost:8000/docs`

Các lệnh test/tắt môi trường:

```powershell
docker compose exec api pytest
docker compose down
```

`docker compose down -v` xóa volume và dữ liệu DB. Chỉ dùng khi muốn xóa dữ liệu để dựng lại từ đầu.

> Các lệnh đầy đủ trên là hướng dẫn bàn giao; hiện mới xác nhận chạy tập dịch vụ `db`, `redis`, `api`, chưa xác nhận toàn bộ stack qua `docker compose up --build`.

---

## 4. Trạng thái chạy trên máy M5

| Việc đã thử | Kết quả | Đạt? |
|---|---|---|
| Docker Engine chạy | Docker Desktop hiển thị Engine running | [x] |
| Khởi động `db`, `redis`, `api` | Container hoạt động; log API báo startup hoàn tất và `/health` trả 200 | [x] |
| `alembic upgrade head` | Đã chạy thành công trước khi seed | [x] |
| `python -m app.seed` | Hoàn tất; số lượng dữ liệu như phần 1 | [x] |
| Mở Swagger tại `http://localhost:8000/docs` | Đã mở và thấy tài liệu API | [x] |
| Khởi động đồng thời đủ `nginx`, `web`, `api`, `db`, `redis` | Chưa có bằng chứng đã chạy cùng lúc | [ ] |
| Thử từ đầu theo README trên máy khác/môi trường sạch | Chưa thực hiện | [ ] |
| `docker compose exec api pytest` | Chưa xác nhận kết quả | [ ] |

---

## 5. Trạng thái kiểm chứng theo checklist Tuần 1

### 5.1 Docker Compose

- [x] Đã thêm cấu hình 5 dịch vụ theo cổng nhóm: Nginx `8080`, web `5173`, API `8000`, PostgreSQL `5433`, Redis `6380`.
- [x] Đã thêm healthcheck/dependency, volume DB, polling/hot reload cho môi trường Windows và cấu hình Nginx.
- [x] Đã thêm cấu hình DB test `course_reg_test` và mẫu biến môi trường.
- [ ] Đã chạy và kiểm tra đủ cả 5 dịch vụ bằng lệnh nhóm `docker compose up --build`.
- [ ] Thành viên khác dựng được hệ thống từ máy sạch theo hướng dẫn.

### 5.2 Khung `core/`

- [x] Đã thêm/cập nhật `main.py`, `core/config.py`, `core/db.py`, `core/redis.py`, `core/errors.py` và `/health`.
- [x] API đã khởi động và log healthcheck trả HTTP 200.
- [ ] Chưa có kiểm chứng đầy đủ các dạng lỗi API, healthcheck phụ thuộc DB/Redis và luồng tắt ứng dụng.

### 5.3 CI và PR

- [x] Đã thêm `.github/workflows/ci.yml` và PR template.
- [x] PR #3 đã mở từ nhánh riêng; không thay đổi `main`.
- [x] GitHub hiện báo “All checks have passed”; check GitGuardian được **skipped** với nhãn test credential.
- [ ] Chưa xác nhận các job backend/frontend thực sự chạy `ruff`, migration, pytest, npm lint/typecheck/build và đều xanh.
- [ ] Chưa xác nhận branch protection của `main` yêu cầu PR, check phù hợp và approval.
- [ ] Chưa xác nhận các nhãn issue và hướng dẫn pre-commit được thiết lập.

### 5.4 Quản trị dự án

- [x] Đã thêm `docs/decisions.md` và mẫu báo cáo tuần.
- [x] Đã thêm hướng dẫn cấu hình GitHub Project.
- [ ] Chưa xác nhận GitHub Project thật đã được tạo, có các cột Todo/Doing/Review/Done/Blocked và các issue bàn giao theo tuần.
- [ ] Các điểm quyết định còn mở cần được nhóm rà soát; cần đối chiếu số điểm trong tài liệu nguồn với `docs/decisions.md` trước khi chốt.

### 5.5 Khung test backend

- [x] Đã thêm cấu hình pytest, marker, timeout/coverage và `backend/tests/conftest.py` với fixture/factory theo thiết kế.
- [x] Đã thêm `backend/docs/test-guide.md`.
- [ ] Chưa xác nhận toàn bộ fixture chạy thành công trên `course_reg_test` và Redis DB 1.
- [ ] Chưa xác nhận `docker compose exec api pytest` hoặc CI test job đạt.
- [ ] Chưa xác nhận test tranh chấp dùng nhiều session riêng/rào chắn được thực thi thành công.

---

## 6. Điểm lưu ý và rủi ro

1. **PR #3 chưa được M4 review.** Việc M4 xem/chạy thử PR là yêu cầu vòng review của nhóm; PR hiện chưa được merge.
2. **GitGuardian:** có bốn phát hiện trên giá trị mẫu `doi_mat_khau_nay`. Check hiện được skip như test credential; finding vẫn được liệt kê trong lịch sử quét. Trạng thái “All checks have passed” không đồng nghĩa với việc giá trị đã bị xóa hoặc các job lint/test đã chạy.
3. **M1/frontend:** chưa xác nhận source frontend của M1 đã có trên nhánh M5 này; do đó chưa thể xác nhận dịch vụ `web`/Nginx phục vụ UI. Việc này không làm mất kết quả chạy API/DB/Redis đã xác nhận, nhưng chặn kiểm chứng toàn bộ ứng dụng.
4. **Test chưa chạy:** không đánh dấu khung test hoàn tất chỉ vì đã thêm fixture/config; cần chạy thật và ghi lại kết quả.
5. **Dữ liệu seed:** lần seed thành công đã tạo dữ liệu demo; không dùng `docker compose down -v` nếu muốn giữ DB hiện tại.

---

## 7. Việc cần làm để khép Tuần 1

| Ai | Việc | Trạng thái |
|---|---|---|
| **M5** | Xác nhận CI backend/frontend chạy lint, migration và test; ghi lại kết quả cụ thể | [ ] |
| **M5** | Chạy full `docker compose up --build` và xác nhận Nginx/web/API/DB/Redis cùng hoạt động | [ ] |
| **M5** | Chạy `docker compose exec api pytest`; xử lý lỗi fixture/test nếu có | [ ] |
| **M5** | Tạo/cập nhật GitHub Project, cột và issue theo quy ước | [ ] |
| **M4** | Chạy thử theo hướng dẫn trên Windows và review PR #3; gửi góp ý trước khi merge | [ ] |
| **M1** | Xác nhận thời điểm/nhánh tích hợp frontend để M5 kiểm tra dịch vụ web và luồng qua Nginx | [ ] |
| **M5** | Sau góp ý, cập nhật PR; chỉ xem xét merge sau review theo quy ước nhóm | [ ] |

---

## 8. Việc tiếp theo của M5 (Tuần 2)

Chỉ bắt đầu các sản phẩm Tuần 2 theo kế hoạch M5 sau khi xử lý các việc đường găng của Tuần 1:

- [ ] `docs/test-plan.md`: tháp test, ánh xạ yêu cầu–test, tiêu chí đạt và chính sách flaky.
- [ ] Bộ kiểm tra bất biến `find_invariant_violations` có CLI và test.
- [ ] Bộ nghiệm thu tiên quyết, phối hợp M2 rà lại các ca.
- [ ] Snapshot OpenAPI và kiểm tra thay đổi hợp đồng trong CI.
- [ ] Locust bản nháp chạy trên seed nhỏ.
- [ ] Chuẩn bị nội dung review lần 1 cuối Tuần 2 và cập nhật quyết định còn mở.

---

## 9. Điều kiện coi là “bàn giao xong Tuần 1”

- [ ] Full stack 5 dịch vụ chạy được bằng `docker compose up --build` trên Windows theo hướng dẫn nhóm.
- [ ] Migration và seed chạy được; test backend chạy được trên DB test riêng và Redis DB 1.
- [ ] CI backend/frontend thực sự chạy các bước phù hợp và có kết quả xanh; trạng thái skipped được phân biệt rõ với test đã chạy.
- [ ] Thành viên khác, theo vòng là M4, đã đọc và chạy thử PR #3; góp ý đã được xử lý.
- [ ] Bảng GitHub Project/issue và báo cáo tuần đã được tạo/cập nhật.
- [ ] PR chưa được merge vào `main` cho tới khi hoàn tất review theo quy ước nhóm.

