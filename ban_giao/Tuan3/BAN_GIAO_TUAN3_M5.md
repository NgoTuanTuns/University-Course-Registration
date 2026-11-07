# Bàn giao Tuần 3 — M5 (QA Engineer & DevOps)

**Dự án:** Hệ thống Đăng ký Học phần & Kiểm tra Điều kiện Tiên quyết<br>
**Người phụ trách:** M5  |  **Ngày bắt đầu:** 06/11/2026  |  **Căn cứ:** `chitietcongviec/M5_cong_viec_7_tuan.md`, `chitietcongviec/QUY_UOC_DU_AN.md`<br>
**Nhánh:** `trung-devops-compose-ci`  |  **PR:** cập nhật sau khi bắt đầu thay đổi Tuần 3

> **Trạng thái: ĐANG THỰC HIỆN — đã phân loại marker, điều chỉnh cấu hình deprecation và cập nhật workflow CI trong working tree.** Các thay đổi cần chạy lại cục bộ và được GitHub Actions xác nhận sau khi push. Auth matrix, MSW, tải và E2E còn phụ thuộc contract/API M1–M3, seed/tài khoản M4 và quyết định D22/D23; không tạo endpoint, tài khoản hay quy tắc nghiệp vụ giả định.

---

## 1. Hiện trạng trước khi code

- CI có PostgreSQL/Redis, tạo `course_reg_test`, chạy migration/check model và kiểm tra OpenAPI. Working copy hiện thêm marker guard, chạy pytest unit và integration/concurrency; giữ job ID/name `backend` và các service DB/Redis. Workflow mới chưa được xác nhận trên GitHub Actions.
- `pytest` có cấu hình marker `unit`, `integration`, `concurrency`, `stress`, `slow`, `e2e`. Đã rà soát và gắn `unit` cho các suite thuần/mock: admin courses, rate limit, refresh rotation, models metadata, prerequisite engine và seed data. Acceptance API và phần đọc DB của invariant được gắn `integration`.
- Chưa có test tranh chấp `concurrency`. Workflow working copy chạy cả `unit` và `integration or concurrency` trong cùng job; marker guard phải thất bại khi còn test chưa phân loại. Giữ nguyên tên job/check hiện tại để giảm rủi ro branch protection.
- Người dùng đã chạy collection: `unit` thu 85/87 test, `integration` thu 2/87, bộ lọc không thuộc ba marker thu 0 test (87 deselected). Như vậy hiện không còn test chưa phân loại; chưa có concurrency tests.
- `origin/main` có commit M4 `9b52e72` bổ sung `UNIT_TESTS_ONLY=1` trong `conftest.py` để bỏ qua DB guard/Alembic cho unit thuần. Working copy đã nhận đúng nội dung M4; workflow chỉ bật cờ cho collection guard và unit tests, không bật cho integration. Cần chạy lại unit command với cờ này để kiểm chứng.
- Collection trước khi sửa cấu hình báo hai deprecation warning. Đã khai báo fixture loop scope `function`, `path_separator = os` và nâng minimum versions lên pytest 8.2, pytest-asyncio 0.24, Alembic 1.16; cần rebuild image và chạy lại để xác nhận warning đã hết.
- Repo hiện chưa có thư mục frontend và package manifest trong root; job frontend được detect/skipped. Chưa thể kiểm tra MSW của M1.
- Bộ OpenAPI hiện là baseline của router đang có; các luồng course search, enrollment, timetable và waitlist cần xác nhận theo contract/API của M1–M3 trước khi sinh ma trận phân quyền cuối.
- Locust/load profile cần DB riêng, Redis DB 2, tài khoản/seed M4 và API M3. Chưa tạo reset script để tránh xóa nhầm DB demo/test.
- Playwright phụ thuộc quyết định D22 và frontend M1.
- PR Tuần 2 #4 đã được M4 merge vào `main`; GitHub Actions/GitGuardian đều qua và GitGuardian không phát hiện secret. Các thay đổi Tuần 3 vẫn ở nhánh M5.

## 2. Cổng rủi ro trước khi triển khai

| Hạng mục | Nguy cơ nếu làm quá sớm | Cổng cần đạt trước khi code/đổi CI |
|---|---|---|
| Tách CI theo `integration or concurrency` | Pytest bỏ qua test DB/API chưa gắn marker hoặc job chạy 0 test | Kiểm kê từng test, gắn marker theo fixture/phụ thuộc thật; xác nhận số test được thu thập; giữ job pytest đầy đủ cho tới lúc đó |
| Redis bật/tắt | Test có thể chỉ xanh do Redis local hoặc nhầm kiểm tra graceful degradation | M2/M3 xác nhận hành vi khi Redis down; service được bật/tắt có chủ đích; không dùng chung Redis DB demo |
| Seed CI | Dữ liệu lớn/nondeterministic làm CI chậm hoặc flaky | M4 cung cấp seed nhỏ, lặp lại được; dùng DB test mới và reset rõ ràng |
| Ma trận auth từ OpenAPI | Không phải endpoint nào cũng cần auth; kỳ vọng 401/403/200 phụ thuộc role và contract | Contract/router ổn định; lập expectation theo endpoint/method/role, không áp một quy tắc chung mù quáng |
| IDOR | Test sai đối tượng nếu API ID/ownership chưa chốt | M3/M4 xác nhận endpoint và quyền sở hữu; dùng hai fixture sinh viên riêng |
| MSW so OpenAPI | Frontend chưa có hoặc mock chưa được chuẩn hóa | M1 cung cấp package, MSW fixtures và contract; không dựng schema frontend thay M1 |
| Load profile/reset | Xóa nhầm DB hoặc dùng chung Redis; số liệu sai do seed/account dùng lại | Tách DSN `course_reg_loadtest`, Redis DB 2, có guard xác thực tên DB trước reset; M4 cung cấp tài khoản/seed |
| Nightly concurrency/security | Job chạy bộ test chưa có hoặc cảnh báo bị hiểu là chặn merge | Có test concurrency ổn định; audit dependencies phù hợp manifest; quét ban đêm không chặn merge giai đoạn đầu |
| Playwright/E2E | Công cụ chưa được nhóm chốt; frontend flows chưa sẵn sàng | Nhóm chốt D22, M1 cung cấp app/luồng và M4 cấp tài khoản kịch bản |

## 3. Checklist Tuần 3 theo kế hoạch M5

### 3.1 Pipeline kiểm thử tích hợp

- [x] CI nền đã có PostgreSQL/Redis và migration. Working copy đang thêm marker guard cùng các lệnh pytest có phân loại; job ID/name được giữ nguyên.
- [x] Rà marker các suite hiện có; gắn `unit` cho sáu suite thuần/mock, xác nhận suite acceptance API và invariant DB là `integration`.
- [x] Chạy lại Ruff lint, kiểm tra format và toàn bộ backend tests sau thay đổi marker: All checks passed, 42 files already formatted, 87 passed in 5.15s (kết quả người dùng chạy bằng Docker).
- [x] Kiểm tra thu thập theo marker: 85 unit, 2 integration, 0 test chưa phân loại; bộ lọc không thuộc ba marker trả 0 test (không dùng bộ lọc rỗng này làm job CI).
- [x] Dùng cờ M4 `UNIT_TESTS_ONLY=1` cho bước marker-check và unit step trong workflow; integration step không dùng cờ.
- [x] Chạy test riêng theo marker: `pytest -m unit` — 85 passed, 2 deselected; `pytest -m "integration or concurrency"` — 2 passed, 85 deselected.
- [x] Xác nhận sau khi nhận `conftest.py` M4: unit với `UNIT_TESTS_ONLY=1` đạt 85 passed, 2 deselected; integration/concurrency không cờ đạt 2 passed, 85 deselected.
- [x] Sau khi lấy `conftest.py` M4: Ruff lint `All checks passed`; format `42 files already formatted`.
- [ ] Xác nhận collection sau khi rebuild không còn hai deprecation warning; xác nhận workflow mới xanh trên GitHub Actions sau khi push.
- [ ] Sau khi M4 có seed nhỏ: thêm bước seed CI có thể lặp lại và chỉ chạy sau migration trên DB test cô lập.
- [ ] Phối hợp M2/M3 kiểm tra hành vi khi Redis bị tắt; dùng job/fixture riêng, không làm ảnh hưởng job CI chuẩn.
- [ ] Xác nhận check `backend` mới xanh trên GitHub Actions sau khi push; xử lý log nếu marker guard/test selection thất bại.
- [ ] Thu số liệu thời gian và coverage `services/`; đề xuất ngưỡng sau baseline, không tự đặt số.

### 3.2 Ma trận phân quyền tự động

- [ ] Sinh danh sách endpoint/method từ OpenAPI.
- [ ] Khai báo kỳ vọng auth theo endpoint và role; xác nhận 401, 403, token hết hạn và admin được phép theo contract.
- [ ] Thêm kiểm thử IDOR A/B sau khi M3/M4 xác nhận endpoint và ownership.
- [ ] Endpoint mới phải được phát hiện tự động; endpoint chưa có expectation phải làm CI fail rõ ràng thay vì bị bỏ qua.

### 3.3 Hợp đồng frontend/backend

- [ ] Chờ M1 có MSW fixtures/package và contract API ổn định.
- [ ] Chọn công cụ kiểm tra schema phù hợp dependency thực tế; kiểm tra mock và OpenAPI trong CI.
- [ ] Chạy cùng M1, ghi lệch thành issue có owner; không tự sửa mock/UI của M1.

### 3.4 Môi trường tải và job định kỳ

- [ ] Tạo DSN/database riêng `course_reg_loadtest`, Redis DB 2 và guard cho lệnh reset.
- [ ] Chỉ seed khi M4 cung cấp profile tải ≥2.000 sinh viên; không dùng DB demo hoặc test.
- [ ] Thêm Compose profile `loadtest`, Locust headless, xuất CSV/HTML vào thư mục bị ignore.
- [ ] Mở rộng kịch bản theo API M3 và tài khoản riêng M4; kiểm tra lỗi nghiệp vụ được phân loại đúng.
- [ ] Khi có test concurrency ổn định, thêm nightly lặp 20 lần; thêm pip-audit/npm audit ở chế độ cảnh báo, không chặn merge ban đầu.

### 3.5 Hạ tầng E2E

- [ ] Chờ nhóm chốt D22 (Playwright) và M1 có frontend.
- [ ] Dựng `frontend/e2e/` và cấu hình Playwright sau khi xác nhận cấu trúc repo với M1.
- [ ] Thống nhất reset dữ liệu/tài khoản kịch bản với M4.
- [ ] Cấu hình artifact ảnh/trace khi thất bại; tuần 3 chưa yêu cầu job E2E bắt buộc xanh.

## 4. Việc M5 có thể làm ngay mà không chờ API

1. Hoàn tất kiểm tra marker theo từng hàm; hiện đã phân loại các suite chính, nhưng cần xác nhận collection không để test nào rơi khỏi job.
2. Chuẩn bị thiết kế expectation map cho auth matrix; chỉ điền endpoint và status sau khi contract được chủ sở hữu xác nhận.
3. Chuẩn bị checklist bảo vệ DB/Redis tải và tiêu chí an toàn của reset script; chưa chạy reset trên môi trường hiện tại.
4. Theo dõi các quyết định D22, D23, D25, D28 và các điểm contract D01–D15 trong buổi review.

**Thứ tự đề nghị:** kiểm kê test/marker → hoàn thiện marker → kiểm tra CI vẫn thu thập đầy đủ test → sau đó mới tách integration/concurrency; song song chờ API/seed để làm auth matrix, load profile và E2E.

## 5. Tiêu chí đóng Tuần 3

- [ ] CI kiểm thử tích hợp API + PostgreSQL + Redis; có seed nhỏ do M4 xác nhận.
- [ ] Kiểm tra có chủ đích cả Redis bật và tắt; không có test bị bỏ qua do thiếu marker.
- [ ] Ma trận phân quyền và IDOR lấy dữ liệu từ contract, chạy tự động.
- [ ] MSW của M1 được kiểm tra với OpenAPI.
- [ ] Load environment tách biệt, reset có guard, Locust chạy được và báo cáo không commit vào Git.
- [ ] Playwright/E2E infrastructure được chốt với M1 và D22.
- [ ] Nightly concurrency/security jobs được thêm sau khi các bộ tương ứng sẵn sàng.

## 6. Nhật ký kiểm tra

| Ngày | Thay đổi/kiểm tra | Kết quả | Rủi ro hoặc việc chờ |
|---|---|---|---|
| 06/11/2026 | Rà kế hoạch Tuần 3, CI, marker, cấu trúc frontend | CI nền có DB/Redis và migration; chưa có concurrency tests hoặc frontend | Workflow CI và config warning đang chỉnh; contract/API M1–M3, seed/tài khoản M4, D22/D23 còn chờ |
| 06/11/2026 | Xác minh marker | Ruff check đạt; format đạt; 87 test passed; collection 85 unit, 2 integration, 0 chưa phân loại | CI/config đã thay đổi sau kết quả này; cần chạy lại và xác nhận GitHub Actions trước khi push |
| 07/11/2026 | Chạy riêng theo marker | Unit: 85 passed, 2 deselected (5.14s); integration/concurrency: 2 passed, 85 deselected (3.32s) | Cần xác nhận warning collection đã hết và GitHub Actions mới sau khi push |
| 07/11/2026 | Tích hợp thay đổi M4 từ `origin/main` | Đã lấy `conftest.py` có cờ `UNIT_TESTS_ONLY`; workflow bật cờ riêng cho collection/unit | Cần chạy lại unit theo cờ và integration không cờ; `origin/main` đã fetch, nhưng workflow mới chưa lên GitHub |
| 07/11/2026 | Kiểm tra lại với cờ M4 | Unit: 85 passed, 2 deselected (6.18s); integration/concurrency: 2 passed, 85 deselected | Cần xác nhận workflow CI mới trên GitHub sau khi push |
| 07/11/2026 | Ruff sau khi nhận `conftest.py` M4 | `ruff check app tests`: All checks passed; `ruff format --check app tests`: 42 files already formatted | Workflow mới vẫn cần GitHub Actions xác nhận sau push |
