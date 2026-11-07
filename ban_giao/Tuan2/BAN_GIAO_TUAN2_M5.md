# Bàn giao Tuần 2 — M5 (QA Engineer & DevOps)

**Dự án:** Hệ thống Đăng ký Học phần & Kiểm tra Điều kiện Tiên quyết

**Người bàn giao:** M5  |  **Ngày cập nhật:** 07/11/2026  |  **Căn cứ:** `chitietcongviec/M5_cong_viec_7_tuan.md` và `chitietcongviec/QUY_UOC_DU_AN.md`
**Nhánh:** `trung-devops-compose-ci`  |  **PR:** #4 — M4 đã merge vào `main` ngày 07/11/2026

> **Trạng thái chung: ĐANG LÀM — các test cục bộ và snapshot hiện tại đã đạt; chưa hoàn tất Tuần 2.** PR đã tách riêng commit tuần 2, không đưa lại các thay đổi tuần 1 vào diff. CI và GitGuardian của PR #4 đã qua; GitGuardian quét 2 commit và không phát hiện secret. Locust đầy đủ và pairing review nghiệm thu còn phụ thuộc M2/M3/M4.

---

## 1. Tóm tắt

Tuần 2 thiết lập kế hoạch kiểm thử, bộ kiểm tra bất biến, nghiệm thu tiên quyết, hợp đồng OpenAPI và bản nháp Locust. Phần đã làm trên nhánh hiện tại:

1. Thêm `docs/test-plan.md`, ma trận yêu cầu → kiểm chứng, rủi ro, tiêu chí thoát và các phụ thuộc.
2. Thêm `find_invariant_violations` dạng CLI chỉ đọc cùng test cho I1–I7 và I9. I8/D12 và I10/D10 được hoãn rõ ràng đến khi nhóm chốt quy tắc.
3. Bổ sung ca API tiên quyết #21: môn không tồn tại trả `404 NOT_FOUND`; không sao chép test lõi của M2.
4. Thêm công cụ sinh/so sánh OpenAPI và snapshot cho các endpoint hiện có; CI có bước kiểm tra snapshot.
5. Xác nhận cục bộ: `docker compose config -q`; API container khởi động; OpenAPI snapshot khớp; Ruff format/check đạt; **87 backend tests passed**.

**Chưa hoàn tất:** M2 rà chéo bộ nghiệm thu (đặc biệt #6/D04 và #16); Locust chạy được với tài khoản/luồng thật; buổi review vòng 1 và quyết định đủ hơn nửa D01–D29.

---

## 2. Danh sách bàn giao

| File/nhóm file | Nội dung | Trạng thái |
|---|---|---|
| `docs/test-plan.md` | Tháp kiểm thử, ánh xạ yêu cầu, rủi ro, phụ thuộc và cổng tuần | Đã thêm; còn phụ thuộc chờ nhóm |
| `backend/app/tools/invariants.py` | `find_invariant_violations`, CLI read-only; I1–I7/I9 | Cục bộ test đạt; I8/I10 chờ D12/D10 |
| `backend/tests/test_invariants.py` | Dữ liệu snapshot hợp lệ, vi phạm giả lập và integration test | Đã chạy; nằm trong tổng 87 test |
| `backend/tests/test_prerequisite_acceptance.py` | API acceptance case #21, môn không tồn tại → 404 | Đã chạy đạt |
| `backend/app/tools/openapi_snapshot.py`, `docs/openapi.json` | Sinh JSON ổn định, so sánh snapshot | Snapshot khớp cục bộ; baseline chỉ bao gồm API đang có |
| `.github/workflows/ci.yml` | Gate kiểm tra OpenAPI trước pytest | Đã thêm; chờ GitHub Actions của PR mới |
| `docker-compose.yml` | Mount `docs/` read-only để API container kiểm tra snapshot cục bộ | `docker compose config -q` đạt; API đã khởi động lại |

---

## 3. Kết quả kiểm chứng cục bộ

| Lệnh/việc | Kết quả | Đạt? |
|---|---|---|
| `docker compose config -q` | Không báo lỗi cấu hình | [x] |
| `docker compose up -d api` | API khởi động; DB và Redis healthy | [x] |
| `docker compose exec api python -m app.tools.openapi_snapshot --check` | `OpenAPI snapshot matches the application.` | [x] |
| `docker compose exec api ruff format --check app tests` | 42 files already formatted | [x] |
| `docker compose exec api ruff check app tests` | All checks passed | [x] |
| `docker compose exec api pytest -q` | 87 passed | [x] |
| GitHub Actions của PR Tuần 2 | PR #4: các check đã qua theo xác nhận và ảnh PR | [x] |
| GitGuardian PR #4 | 2 commit được quét; không phát hiện secret | [x] |


## 4. Nghiệm thu tiên quyết và phối hợp M2

- `backend/tests/test_prerequisite_engine.py` đã có 20 ca đồ thị và 5 ca thêm cạnh chu trình; `pytest` hiện chạy các ca này.
- M5 bổ sung API case #21 cho môn không tồn tại; chưa nhân bản bộ test của M2.
- **Case #6:** test hiện theo ngữ nghĩa engine “môn đã hoàn tất là đủ”; D04 còn Open, M2 cần xác nhận trước khi coi đây là expected result cuối.
- **Case #16:** ma trận yêu cầu đánh giá `can_take_now` cho lựa chọn trong OR-group; test hiện có mới xác nhận nhóm OR chưa thỏa. M2 cần hoàn tất phần explain tương ứng và rà chéo với M5.
- [ ] M2 và M5 pairing review toàn bộ 21+5 ca; ghi kết luận các ca phụ thuộc D04 và OR vào PR/`docs/decisions.md`.

---

## 5. OpenAPI và Locust

### 5.1 OpenAPI

- Snapshot hiện khớp mã ứng dụng trong Compose và CI có bước so sánh.
- Snapshot chỉ đại diện các endpoint hiện có; chưa bao gồm luồng M3 `/courses`, `/enroll`, `/timetable`, `/waitlist`.
- Khi M1/M3 hoàn tất và nhóm chốt D01–D07/D13/D15, cập nhật snapshot cùng PR thay đổi hợp đồng; thông báo M1 theo quy ước.
- [x] Gate OpenAPI xanh trên GitHub Actions của PR #4.

### 5.2 Locust

- Chưa tạo kịch bản giả lập API chưa có hoặc đưa credential vào repo.
- Cần M3 xác nhận endpoint, request/response và các mã lỗi nghiệp vụ; cần M4 cấp tài khoản riêng cho từng VU cùng seed nhỏ.
- Khi đủ đầu vào, kịch bản Tuần 2 chạy vài chục VU trên dữ liệu nhỏ: đăng nhập → tra cứu → kiểm tra tiên quyết → đăng ký → thời khóa biểu. `409`/`422` hợp lệ theo kịch bản không tính là lỗi hệ thống; `5xx`, timeout và vi phạm bất biến mới tính lỗi.
- [ ] Hoàn thiện và chạy Locust draft sau khi có contract M3 và account file M4.

---

## 6. Quyết định và rủi ro còn mở

| Hạng mục | Trạng thái | Rủi ro/việc tiếp theo |
|---|---|---|
| CI + OpenAPI gate | PR #4 checks đã qua | GitGuardian không phát hiện secret; OpenAPI gate xanh |
| M2 nghiệm thu | Pairing review chưa xong | Không chốt D04 hoặc cách hiểu #16 thay M2 |
| M3 API đăng ký/thời khóa biểu | Chưa có trong main được rà | Snapshot cuối và Locust đầy đủ đang chờ contract |
| M4 account file/seed tải nhỏ | Chưa bàn giao cho Locust | Không dùng chung tài khoản hoặc tài khoản ghi cứng |
| D01–D29 | Cần nhóm xem và ghi quyết định | Hơn một nửa cần được chốt trước review cuối tuần 2; M5 không tự quyết thay nhóm |
| M4 review PR M5 | PR #4 đã được M4 merge vào `main` | Đã xong; tiếp tục công việc Tuần 3 trên nhánh M5 |

---

## 7. Việc tiếp theo

1. PR #4 đã được M4 merge vào `main`; giữ các thay đổi Tuần 3 trên nhánh M5.
2. Pairing review 21+5 ca với M2; xác nhận D04 và phần `can_take_now` của case #16.
3. Khi M3/M4 bàn giao contract và tài khoản, hoàn thiện Locust draft và chạy trên seed nhỏ.
4. Chuẩn bị review vòng 1: trạng thái từng thành viên, rủi ro, D01–D29 còn mở, người chốt và hạn.
