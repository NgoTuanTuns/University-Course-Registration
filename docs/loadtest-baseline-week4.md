# M5 — Báo cáo baseline tải tuần 4

**Ngày chạy:** 20/11/2026
**Trạng thái:** Hoàn tất 3 lượt baseline đã sửa luồng Locust; số liệu bên dưới là kết quả chính thức của M5. Bug bash, review lần 2 và chốt D28 vẫn cần nhóm phối hợp.
**Kịch bản:** `hot5`, 2.000 tài khoản đã pre-login, ramp 30 giây, hold 150 giây; mỗi sinh viên chạy một luồng đăng ký vào một trong 5 lớp hot, rồi đọc thời khóa biểu.

## Phương pháp và kiểm tra hợp lệ

- Mỗi lượt dùng database riêng `course_reg_loadtest`, reset trước khi tạo dữ liệu và pre-login.
- Pre-login chạy ở 20 tài khoản/giây, concurrency 20; thời gian khoảng 100,2 giây. Login P95 là số đo riêng, không gộp vào spike.
- Chỉ chấp nhận lượt có 2.000 request cho từng endpoint, tổng 8.000 request, 0 request failure và 0 Locust exception.
- Locust đã được sửa để gọi `/timetable` sau mọi lần thử đăng ký, kể cả khi kết quả nghiệp vụ bị từ chối. Ba baseline sơ bộ trước sửa chỉ có 25 request `/timetable`; không dùng chúng làm số liệu chính thức.
- Sau mỗi lượt, `python -m app.tools.invariants` báo `Found 0 invariant violation(s)`. I8 (D12 waitlist rounding) và I10 (D10 same-course enrollment) được hoãn theo quyết định nhóm.

## Latency theo từng lượt

Đơn vị: mili giây. Mỗi ô ghi `P50 / P95 / P99`.

| Endpoint | `baseline-hot5-fixed-01` | `baseline-hot5-fixed-02` | `baseline-hot5-fixed-03` | Median P95 (dải) |
|---|---:|---:|---:|---:|
| `GET /courses (search)` | 160 / 330 / 460 | 160 / 350 / 440 | 150 / 290 / 360 | 330 (290–350) |
| `GET /prerequisites/check` | 130 / 270 / 350 | 140 / 290 / 390 | 130 / 240 / 310 | 270 (240–290) |
| `GET /timetable` | 45 / 120 / 180 | 48 / 120 / 170 | 42 / 110 / 150 | 120 (110–120) |
| `POST /enroll` | 93 / 200 / 270 | 99 / 210 / 290 | 92 / 170 / 230 | 200 (170–210) |
| Aggregated | 99 / 270 / 360 | 100 / 280 / 390 | 95 / 240 / 310 | 270 (240–280) |

## Kết quả và outcome nghiệp vụ

| Kết quả mỗi lượt | Lần 1 | Lần 2 | Lần 3 |
|---|---:|---:|---:|
| Virtual users tối đa | 2.000 | 2.000 | 2.000 |
| Request mỗi endpoint | 2.000 | 2.000 | 2.000 |
| Tổng request | 8.000 | 8.000 | 8.000 |
| Request failures | 0 | 0 | 0 |
| Locust exceptions | 0 | 0 | 0 |
| Invariant violations sau tải | 0 | 0 | 0 |
| Aggregate request rate | 260,4/s | 260,4/s | 261,3/s |
| Đỉnh RPS trong history | 268,4/s | 268,8/s | 268,7/s |

Các outcome của 2.000 lần `POST /enroll` mỗi lượt:

| Outcome nghiệp vụ | Lần 1 | Lần 2 | Lần 3 |
|---|---:|---:|---:|
| `ACTIVE` | 20 | 20 | 20 |
| `ALREADY_COMPLETED` | 532 | 529 | 500 |
| `WAITLISTED` | 5 | 5 | 5 |
| `WAITLIST_FULL` | 1.442 | 1.445 | 1.474 |
| `ALREADY_ENROLLED` | 1 | 1 | 1 |

Các từ chối nghiệp vụ này được đếm riêng và không phải lỗi HTTP/hạ tầng. Mỗi cột cộng thành 2.000 lần thử.

## Pre-login và môi trường

- Login P50/P95 lần lượt: `baseline-hot5-fixed-01` 204/211 ms; `baseline-hot5-fixed-02` 205/212 ms; `baseline-hot5-fixed-03` 204/215 ms.
- Máy: Intel Core 5 210H, 8 core/12 logical processor; Docker Engine thấy 12 CPU và giới hạn memory 7,57 GiB. Host có 15,6 GB RAM; lần đo ban đầu có khoảng 3,9 GB trống.
- Chưa có số đo peak CPU/RAM và `pg_stat_activity`/lock waits đồng bộ với ba lượt chính thức. Các ảnh Docker stats cũ chỉ là snapshot, không đại diện peak; không suy diễn rằng không có lock contention.

## Diễn giải và giới hạn

1. P95 `POST /enroll` trong ba lượt là 170–210 ms; P95 tổng hợp là 240–280 ms. Đây là baseline, chưa phải so sánh trước/sau tối ưu.
2. Các từ chối `WAITLIST_FULL` và `ALREADY_COMPLETED` chiếm phần lớn kết quả do dữ liệu seed và hot course; đó là outcome nghiệp vụ được chấp nhận, không phải lỗi server.
3. Hot5 thực hiện một lần đăng ký/người dùng rồi giữ VU đến hết thời gian chạy; đây là spike đăng ký một lần, không phải tải đọc liên tục suốt 180 giây.
4. Invariant báo 0 vi phạm cho cả ba lượt; I8/D12 và I10/D10 vẫn bị hoãn vì nhóm chưa chốt quy tắc.
5. Chưa đủ số liệu để kết luận về peak CPU/RAM hoặc DB lock waits.

## Đề xuất M5 cho D28 — chờ nhóm chốt

- P95 `POST /enroll` không quá **2 giây** trong cấu hình baseline.
- **0** lỗi 5xx, timeout và 4xx ngoài danh sách mã nghiệp vụ hợp lệ.
- Invariant sau tải không có vi phạm và sĩ số lớp khớp 100% với enrollment `ACTIVE`.

Đây là đề xuất M5, chưa phải quyết định đã thống nhất. Nhóm cần xem số liệu baseline và chốt D28 trong `docs/decisions.md`.

## Tái lập và artifacts

Run IDs: `baseline-hot5-fixed-01`, `baseline-hot5-fixed-02`, `baseline-hot5-fixed-03`. Artifacts Locust (CSV stats/history/failures/exceptions, HTML, business outcomes, login JSON) nằm trong `loadtest/reports/`, thư mục bị Git ignore vì có dữ liệu phát sinh cục bộ. Không commit token hay file tài khoản.

Trước mỗi lượt: reset database tải riêng, chờ API healthy, pre-login 2.000 tài khoản, chạy Locust, rồi chạy invariant. Không dùng `docker compose down -v`. Guard và lệnh tái lập được mô tả trong `loadtest/README.md`.
