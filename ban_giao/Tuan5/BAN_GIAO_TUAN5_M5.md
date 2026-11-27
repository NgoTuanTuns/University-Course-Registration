# Bàn giao Tuần 5 — M5 (Chạy lại tải và kiểm tra độ ổn định)

**Ngày cập nhật:** 26/11/2026
**Trạng thái:** Đang thực hiện. Đã hoàn tất kiểm tra lặp bài concurrency và ba lượt baseline hot5 trên `main` hiện tại (`b0537ff`). Chưa thể quy kết mức thay đổi cho tối ưu cụ thể nào vì M1–M4 chưa xác nhận phạm vi tối ưu đã tích hợp.

## 1. Phạm vi M5 có thể làm độc lập

- [x] Đối chiếu trạng thái GitHub: PR #8 của M5 Tuần 4 đã merge; `main` hiện ở commit `b0537ff`, CI mới nhất thành công; không có PR đang mở.
- [x] Tạo nhánh làm việc riêng `m5-week5-loadtest-rerun` từ `origin/main`; không sửa trực tiếp `main`.
- [x] Kiểm tra `docker compose --profile loadtest config -q`; cấu hình profile tải hợp lệ.
- [x] Chạy `tests/test_enrollment_concurrency.py` 20 lượt liên tiếp trên database test cô lập `course_reg_test`; mỗi lượt 13/13 pass, tổng cộng 260 test pass, không ghi nhận flaky failure.
- [x] Thêm `.github/workflows/nightly-stability.yml`: chạy lặp bộ concurrency 20 lượt mỗi đêm hoặc thủ công; `pip-audit`/`npm audit` chỉ báo cáo, không chặn merge; secret scan vẫn chặn khi phát hiện lỗi.
- [ ] Xác nhận workflow mới chạy xanh trên GitHub. Lịch tự động chỉ bắt đầu sau khi workflow được merge vào `main`.
- [x] Chạy ba lượt hot5 2.000 người trên `b0537ff`; mỗi endpoint có 2.000 request, 0 failure, invariant 0 vi phạm; ghi median P95 so với baseline Tuần 4.
- [x] Bổ sung mẫu CPU/RAM đồng bộ cho API, DB, Redis và Locust trong từng lượt; số liệu là peak trong mẫu 4 giây, không phải peak liên tục chính xác.
- [ ] Bổ sung PostgreSQL connection/lock-wait metrics đồng bộ trong lúc tải.
- [ ] Nhận xác nhận M1–M4 về commit/optimize đã tích hợp để phân tích nhân quả trước/sau; số hiện tại chỉ chứng minh mốc lặp trên `main` mới.
- [ ] Phân tích, sửa hoặc ghi nhận owner cho mọi test không ổn định nếu các lượt sau phát hiện lỗi.

## 2. Việc cần phối hợp với nhóm

- [ ] **M2/M3:** gửi commit/PR đã tích hợp có thay đổi ảnh hưởng hiệu năng (truy vấn N+1, cache, đăng ký, Redis/DB), cùng bằng chứng test; xác nhận hạng mục nào cần so sánh trước/sau.
- [ ] **M4:** xác nhận chỉ mục và cấu hình DB hiện có trên `main`, đặc biệt cấu hình pool thực tế của `api-loadtest` (`DB_POOL_SIZE=5`, `DB_MAX_OVERFLOW=0`) so với cấu hình trong báo cáo M4. Cho biết có cần điều chỉnh cấu hình đo không.
- [ ] **M1:** xác nhận phần frontend/E2E/performance nào đã thực sự vào `main`; nhánh `feature/frontend-ui` đã bị xóa nên cần nêu commit hoặc bằng chứng hiện có trên `main`.
- [ ] **Cả nhóm:** bug bash và review lần 2; ghi issue, mức độ và người xử lý.
- [ ] **Cả nhóm chốt D10:** quy tắc cùng môn trong kỳ và đăng ký lại môn đã hoàn tất; hiện invariant I10 bị hoãn.
- [ ] **Cả nhóm chốt D12:** giới hạn waitlist dùng `ceil` hay `floor`; hiện invariant I8 bị hoãn.
- [ ] **Cả nhóm chốt D28:** ngưỡng P95 và mức độ bao phủ tối thiểu sau khi xem baseline; đề xuất M5 trước đây chưa phải quyết định nhóm.

### Tin nhắn gợi ý gửi nhóm

> M5 chuẩn bị chạy baseline Tuần 5. Nhờ M1–M4 gửi commit/PR đã nhập vào `main` có ảnh hưởng tới hiệu năng hoặc luồng kiểm thử, kèm test/evidence; M4 xác nhận cấu hình index/pool đang dùng trong `api-loadtest`. Cả nhóm cần chốt D10 (cùng môn/đăng ký lại), D12 (ceil/floor waitlist), D28 (P95/coverage), và thống nhất lịch bug bash + review lần 2. Khi xác nhận xong, M5 sẽ chạy lại cùng kịch bản hot5 ba lần trên commit và cấu hình đã ghi nhận.

## 3. Bằng chứng kiểm tra độ ổn định

- Lệnh mỗi lượt: `docker compose exec -T api pytest tests/test_enrollment_concurrency.py -q --no-cov`
- Nơi chạy: container API local; fixture test kiểm tra URL và chỉ cho phép `course_reg_test`. Bộ test tự làm sạch dữ liệu kiểm thử giữa các test.
- Kết quả: 20/20 lượt thành công; mỗi lượt 13 passed; tổng cộng 260 test case executions, không có failure.
- Đây là bằng chứng ổn định cục bộ cho riêng bộ concurrency, chưa thay cho nightly workflow hoặc toàn bộ integration suite.
- Workflow mới chưa được chạy trên GitHub; PR review và CI vẫn cần xác nhận trước khi xem là đã tích hợp.

## 4. Baseline hot5 trên `main` hiện tại

- Commit đo: `b0537ff` (`origin/main`, 2026-11-25); máy: Docker Engine 29.8.2, 12 CPU logic, Docker memory limit 7,57 GiB. RAM trống trước các lượt xấp xỉ 3,8 GB; sau mỗi lượt vẫn trên 4 GB.
- Cấu hình giữ nguyên giữa ba lượt: 2.000 user, `hot5`, ramp 30 giây, hold 150 giây; pre-login 20 tài khoản/giây. Mỗi lượt có 2.000 request trên mỗi endpoint, tổng 8.000; zero request failures; invariant 0 vi phạm. D10/I10 và D12/I8 vẫn deferred theo quyết định nhóm.

| Endpoint — P95 (ms) | Lượt 1 | Lượt 2 | Lượt 3 | Median 3 lượt | Tuần 4 median | Chênh lệch median |
|---|---:|---:|---:|---:|---:|---:|
| `GET /courses (search)` | 320 | 340 | 310 | 320 | 330 | -10 ms (-3,0%) |
| `GET /prerequisites/check` | 270 | 300 | 270 | 270 | 270 | 0 ms (0%) |
| `GET /timetable` | 110 | 120 | 110 | 110 | 120 | -10 ms (-8,3%) |
| `POST /enroll` | 190 | 210 | 190 | 190 | 200 | -10 ms (-5,0%) |
| Aggregated | 260 | 290 | 260 | 260 | 270 | -10 ms (-3,7%) |

| Run ID | Login P50/P95 (ms) | Aggregate requests/s | P95 `/enroll` | P95 aggregate | API peak mẫu | DB peak mẫu | Invariant |
|---|---:|---:|---:|---:|---:|---:|---|
| `week5-preopt-hot5-01` | 204/221 | 268,4 | 190 ms | 260 ms | 362,7 MiB | 156,3 MiB | 0 vi phạm |
| `week5-preopt-hot5-02` | 204/208 | 257,4 | 210 ms | 290 ms | 364,5 MiB | 152,2 MiB | 0 vi phạm |
| `week5-preopt-hot5-03` | 204/210 | 267,9 | 190 ms | 260 ms | 364,0 MiB | 152,7 MiB | 0 vi phạm |

Artifacts Locust và mẫu tài nguyên từng lượt nằm cục bộ trong `loadtest/reports/` (Git ignored): `*_stats.csv`, `*_stats_history.csv`, `*_failures.csv`, `*_exceptions.csv`, `*_business_outcomes.json`, `*_login.json`, `*.html`, `*_resource.csv`. Không có credential được commit.

So với baseline Tuần 4, median P95 các endpoint bằng hoặc thấp hơn 0–10 ms. Chênh lệch nhỏ này chưa đủ để khẳng định tối ưu do M1–M4 gây ra: cần xác nhận thay đổi đã merge, lock cấu hình/môi trường và kiểm tra biến thiên máy. Các giá trị CPU là tỷ lệ trên nhiều core; tài nguyên chỉ lấy mẫu mỗi 4 giây nên đây không phải số peak chính xác. Chưa thu được số liệu PostgreSQL lock waits.

## 5. Rủi ro và cách kiểm soát

- **Không so sánh baseline khác phiên bản:** `main` đã nhận các thay đổi lớn sau baseline Tuần 4. Trước khi đo cần ghi commit SHA, xác nhận các tối ưu đã merge, giữ nguyên dữ liệu, kịch bản, cấu hình Docker và tham số tải giữa các lượt.
- **Thiếu RAM:** trước khi chạy lại đã kiểm tra RAM trống 3,78 GB, gần baseline Tuần 4 khoảng 3,9 GB; sau cả ba lượt còn trên 4 GB. Không chạy thêm spike nếu RAM xuống thấp hoặc máy/Docker có dấu hiệu quá tải.
- **Reset dữ liệu tải:** chỉ reset `course_reg_loadtest` bằng guard hiện có; không dùng `docker compose down -v` và không đụng `course_reg`/`course_reg_test`.
- **Quyết định nghiệp vụ chưa chốt:** I8/D12 và I10/D10 đang bị hoãn; invariant báo 0 vi phạm chỉ trong phạm vi các quy tắc đã chốt.
- **Ngưỡng đạt:** D28 chưa được nhóm duyệt; không tuyên bố hiệu năng đạt/nghẽn chỉ dựa trên đề xuất cũ của M5.

## 6. Bước tiếp theo

Để kết luận trước/sau tối ưu hoặc chốt D28:

1. Nhóm xác nhận commit/tối ưu M1–M4 nào cần đánh giá; M4 xác nhận DB pool/index áp dụng cho profile tải.
2. Thu DB connections/lock waits cho lượt tiếp theo nếu cần phân tích điểm nghẽn.
3. Đối chiếu số liệu median và dải ba lượt; trình D28 cho nhóm chốt, không tự nhận đề xuất là tiêu chí đã duyệt.
