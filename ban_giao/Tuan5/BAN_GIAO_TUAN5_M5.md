# Bàn giao Tuần 5 — M5 (Chạy lại tải và kiểm tra độ ổn định)

**Ngày cập nhật:** 26/11/2026
**Trạng thái:** Đang thực hiện. Đã hoàn tất kiểm tra lặp bài concurrency; chưa chạy lại baseline 2.000 người vì máy hiện chỉ còn 1,52 GB RAM trống và các thành viên chưa xác nhận đầy đủ phần tối ưu đã nhập vào `main`.

## 1. Phạm vi M5 có thể làm độc lập

- [x] Đối chiếu trạng thái GitHub: PR #8 của M5 Tuần 4 đã merge; `main` hiện ở commit `b0537ff`, CI mới nhất thành công; không có PR đang mở.
- [x] Tạo nhánh làm việc riêng `m5-week5-loadtest-rerun` từ `origin/main`; không sửa trực tiếp `main`.
- [x] Kiểm tra `docker compose --profile loadtest config -q`; cấu hình profile tải hợp lệ.
- [x] Chạy `tests/test_enrollment_concurrency.py` 20 lượt liên tiếp trên database test cô lập `course_reg_test`; mỗi lượt 13/13 pass, tổng cộng 260 test pass, không ghi nhận flaky failure.
- [ ] Chạy lại ba baseline hot5 2.000 người trên phiên bản hiện tại và lập bảng trước/sau. Tạm hoãn đến khi RAM trống đủ và nhóm xác nhận các thay đổi tối ưu đã tích hợp.
- [ ] Bổ sung peak CPU/RAM và PostgreSQL lock/connection metrics đồng bộ trong lúc tải.
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

## 4. Rủi ro và cách kiểm soát

- **Không so sánh baseline khác phiên bản:** `main` đã nhận các thay đổi lớn sau baseline Tuần 4. Trước khi đo cần ghi commit SHA, xác nhận các tối ưu đã merge, giữ nguyên dữ liệu, kịch bản, cấu hình Docker và tham số tải giữa các lượt.
- **Thiếu RAM:** hiện máy còn 1,52 GB RAM trống; lần baseline trước ghi khoảng 3,9 GB trống. Không chạy spike 2.000 người trong điều kiện hiện tại để tránh quá tải và số đo sai lệch.
- **Reset dữ liệu tải:** chỉ reset `course_reg_loadtest` bằng guard hiện có; không dùng `docker compose down -v` và không đụng `course_reg`/`course_reg_test`.
- **Quyết định nghiệp vụ chưa chốt:** I8/D12 và I10/D10 đang bị hoãn; invariant báo 0 vi phạm chỉ trong phạm vi các quy tắc đã chốt.
- **Ngưỡng đạt:** D28 chưa được nhóm duyệt; không tuyên bố hiệu năng đạt/nghẽn chỉ dựa trên đề xuất cũ của M5.

## 5. Kế hoạch chạy lại baseline

Sau khi đủ RAM và nhóm xác nhận phạm vi tối ưu:

1. Ghi commit SHA, phiên bản Docker, RAM trống, giới hạn Docker và cấu hình DB/pool.
2. Dùng cùng kịch bản `hot5`, 2.000 tài khoản, ramp 30 giây, hold 150 giây; chạy ba lượt với ID khác nhau.
3. Chỉ chấp nhận mỗi lượt có 2.000 request cho từng endpoint, 0 lỗi request/exception và invariant không vi phạm các quy tắc đã chốt.
4. Ghi P50/P95/P99, request rate, outcome nghiệp vụ, peak CPU/RAM, DB connections/lock waits; so sánh median và dải giữa các lượt với baseline Tuần 4.
5. Trình số liệu cho nhóm để chốt D28; cập nhật báo cáo tải sau khi đã thống nhất.
