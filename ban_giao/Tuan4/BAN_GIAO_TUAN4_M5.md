# Bàn giao Tuần 4 — M5 (Baseline tải 2.000 người dùng)

**Căn cứ:** `chitietcongviec/M5_cong_viec_7_tuan.md`, mục Tuần 4; `chitietcongviec/QUY_UOC_DU_AN.md`
**Trạng thái:** Đã chạy đủ 3 baseline hot5 sau khi sửa Locust; mỗi endpoint có 2.000 request, mỗi lượt có 0 request failure/exception và invariant báo 0 vi phạm. Bug bash, review lần 2 và chốt D28 vẫn cần nhóm phối hợp.

## 1. Phạm vi M5 có thể làm độc lập

- [x] Đối chiếu phần M1–M4 đã được tích hợp vào `main`; cập nhật nhánh M5 theo `origin/main` mà không sửa ref `main`.
- [x] Tạo profile Compose tải riêng: API không `--reload`, PostgreSQL `course_reg_loadtest`, Redis DB 2, Locust image được ghim phiên bản.
- [x] Thêm guard reset: chỉ chấp nhận `APP_ENV=loadtest`, host `db`, database `course_reg_loadtest` và Redis DB 2.
- [x] Tách pre-login khỏi spike; token chỉ ghi vào dữ liệu cục bộ bị Git bỏ qua, không in credential ra log.
- [x] Dựng `LoadTestShape` ramp 2.000 người trong 30 giây; thêm scenario registration, cancellation, read-heavy, hot5 và ghi outcome nghiệp vụ riêng.
- [x] Chạy Ruff check/format cho reset guard, pre-login, test guard; kiểm tra cú pháp Locust, Compose config và `git diff --check`.
- [x] Smoke test mixed 50 user xác nhận reset → pre-login → đăng ký/hot5/đọc/hủy → invariant hoạt động.
- [x] Chạy 3 lượt baseline sơ bộ; mỗi lượt có 6.025 request và invariant báo 0 vi phạm.
- [x] Ghi nhận lỗi bao phủ TKB trong kịch bản cũ; sửa Locust để vẫn gọi `/timetable` sau cả kết quả từ chối đăng ký.
- [x] Chạy lại 3 baseline hot5 sau sửa; xác nhận mỗi lượt có 2.000 request `/timetable`, đủ 8.000 request, 0 lỗi và invariant pass; cập nhật số liệu chính thức trong báo cáo.
- [x] Lưu P50/P95/P99, request rate, lỗi và outcome nghiệp vụ của ba baseline chính thức trong CSV/HTML cục bộ; ghi số tổng hợp vào báo cáo.
- [x] Đối chiếu các PR/nhánh thành viên trên GitHub ngày 20/11/2026: PR #1–#7 đã đóng; nhánh M2/M3/M4 hiện phía sau `main`, `feature/frontend-ui` không chung lịch sử. Không có phần chưa tích hợp an toàn để ghép.
- [ ] Thu đủ số liệu peak CPU/RAM API và DB lock/connection trong lúc tải; ảnh baseline #3 chụp sau khi API loadtest không còn số đo.

## 2. Việc cần phối hợp

- [ ] Bug bash 60–90 phút với M1–M4; tạo issue có bước tái hiện, mức độ và owner.
- [ ] Review lần 2, chốt D28/P95 sau khi xem baseline; không đặt ngưỡng trước số liệu.
- [ ] Gửi baseline cho M2/M3/M4 để họ dùng làm mốc tối ưu Tuần 5.

## 3. Rủi ro đã xử lý và giới hạn

- Reset có thể xóa sạch DB đích; guard giới hạn vào DB tải riêng. Không dùng `docker compose down -v`.
- `APP_ENV=loadtest` tắt rate limit; chỉ service `api-loadtest` được nhận biến này.
- Tệp export của M4 có mật khẩu; nằm dưới `loadtest/data/` bị ignore, bị xóa sau khi tạo token thành công.
- Ba baseline hot5 sơ bộ có P95 tổng hợp 260–270 ms, 0 failure và 0 exception. Các số này chưa phải baseline cuối vì luồng TKB thiếu 1.975 request mỗi lượt; cần thay bằng số liệu sau khi chạy lại.
- Smoke test sơ bộ ghi nhận 50 lần `POST /enroll`, 0 request failure; P95 `/enroll` 26 ms. Login được đo riêng: P95 0,204 giây. Lượt này dùng 50 tài khoản kit đứng đầu CSV nên chỉ xác nhận kỹ thuật, không dùng làm mốc tải.
- Kiểm tra invariant sau smoke test: 0 vi phạm được phát hiện; I8 (D12) và I10 (D10) đang được hoãn vì quyết định nhóm chưa chốt.
- Kịch bản smoke registration sinh nhiều kết quả nghiệp vụ hợp lệ (`MIN_ACCUMULATED_CREDITS_NOT_MET`, `PREREQ_NOT_MET`); cần phân biệt chúng với lỗi hệ thống trong baseline.
- Kết quả tải cần phân biệt lỗi hệ thống với mã nghiệp vụ hợp lệ; invariant sau mỗi lượt phải đạt 100% nhất quán sĩ số và không vi phạm các bất biến đã được chốt.
- Smoke `smoke-50-v3` kết thúc exit 1 vì 15 tài khoản không được khoa cho phép xem môn `INT`; API có 0 request failure. Đã chuyển luồng chung và 5 lớp hot sang BAS dùng chung cho các khoa; smoke này không dùng làm baseline.
- Smoke mixed cuối cùng chạy 50 user: 206 request, 0 request failures/exceptions; 50 `POST /enroll`, 5 hủy ACTIVE, 1 hủy waitlist; có 4 `WAITLISTED`, 11 `WAITLIST_FULL`. P95 `/enroll` 35 ms, P95 login 0,207 giây.

## 4. Bằng chứng

Smoke mixed cuối cùng: `loadtest/reports/smoke-50-final_stats.csv`, `smoke-50-final.html`, `smoke-50-final_business_outcomes.json`, `smoke-50-final_login.json`; 206 request, 0 failures/exceptions. Invariant trả `Found 0 invariant violation(s)` và hoãn I8/I10 theo D12/D10.

### Baseline hot5 2.000 user

| Lần chạy | P95 `/courses` | P95 `/prerequisites/check` | P95 `/timetable` | P95 `/enroll` | P95 tổng hợp | Tổng request | Invariant |
|---|---:|---:|---:|---:|---:|---:|---|
| `baseline-hot5-fixed-01` | 330 ms | 270 ms | 120 ms | 200 ms | 270 ms | 8.000 | 0 vi phạm |
| `baseline-hot5-fixed-02` | 350 ms | 290 ms | 120 ms | 210 ms | 280 ms | 8.000 | 0 vi phạm |
| `baseline-hot5-fixed-03` | 290 ms | 240 ms | 110 ms | 170 ms | 240 ms | 8.000 | 0 vi phạm |

Mỗi baseline chính thức có 2.000 request cho từng endpoint, tổng 8.000 request; CSV ghi 0 failure và 0 exception. Aggregate khoảng 260,4–261,3 request/giây, history có đỉnh 268,4–268,8 request/giây. Invariant sau cả ba lượt báo 0 vi phạm. Ba lượt cũ `baseline-hot5-01/02/03` chỉ là số liệu sơ bộ vì mỗi lượt có 25 request `/timetable`; không dùng để đánh giá route này. I8 (D12) và I10 (D10) tiếp tục được hoãn theo quyết định nhóm.

Pre-login: cả ba baseline tạo 2.000 tài khoản ở 20 tài khoản/giây; P95 lần lượt khoảng 0,211 / 0,212 / 0,215 giây. Thời gian pre-login khoảng 100 giây là dự kiến ở tốc độ này.

Tài nguyên máy: Docker có 12 CPU logic và 7,57 GiB memory; host có 15,6 GB RAM, trong đó còn trống khoảng 3,9 GB trước baseline. Docker stats baseline #2 ghi nhận API 347,5 MiB, DB 122,3 MiB, Redis 11,4 MiB ở thời điểm chụp. Ảnh baseline #3 chỉ ghi được DB 124,9 MiB và Redis 11,93 MiB; API hiện `--`, nên không có số đo API tại thời điểm đó. Các ảnh là mẫu tại thời điểm chụp, không phải peak. Chưa có bằng chứng lưu riêng về DB locks/peak tài nguyên.

Các report Locust theo run ID nằm trong `loadtest/reports/`: `*_stats.csv`, `*_stats_history.csv`, `*_failures.csv`, `*_exceptions.csv`, `*_business_outcomes.json`, `*_login.json` và HTML. Cả ba file stats ghi Failure Count = 0; failures/exceptions CSV không có bản ghi lỗi. Run hot5 chạy 180 giây; request count tăng trong khoảng 30–31 giây đầu, sau đó các VU giữ trạng thái nhưng không lặp lại thao tác đăng ký. Đây là spike một lượt đăng ký/người dùng, không phải tải truy vấn liên tục suốt 180 giây.

Đề xuất ban đầu của M5 cho D28 là P95 `POST /enroll` ≤ 2 giây, 5xx/timeouts/unexpected 4xx = 0, và invariant/đối chiếu sĩ số đạt 100%. Vì baseline cần chạy lại sau sửa luồng TKB, nhóm chỉ nên chốt ngưỡng sau khi xem số liệu mới.

Kịch bản bug bash và mẫu ghi issue được chuẩn bị tại `ban_giao/Tuan4/BUG_BASH_TUAN4_M5.md`; buổi chạy thật, review lần 2 và chốt D28 vẫn cần thành viên tham gia.
