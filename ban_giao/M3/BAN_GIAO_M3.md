# Bàn giao M3 — Enrollment, Concurrency & Waitlist

Ngày thực hiện: 08/11/2026. Nhánh: `m3-enrollment-waitlist`.

## Phần đã triển khai

- Tuần 1: rà model enrollment/waitlist hiện có; API `/courses` đủ 5 nhóm lọc, pagination, escape wildcard, my_status, kiểm tra không N+1; tài liệu thiết kế.
- Tuần 2: đăng ký/hủy, tích hợp tiên quyết M2, lịch, tín chỉ cùng kỳ, timetable, vector lịch dùng chung.
- Tuần 3: khóa sinh viên, UPDATE giữ chỗ nguyên tử, version hủy, idempotency Redis, retry deadlock/serialization và test session PostgreSQL riêng.
- Tuần 4: waitlist giới hạn ceil theo tỷ lệ, rời hàng, FIFO, hủy tự đôn, giữ người bị chặn, blocked_reason và đánh lại position.
- Tuần 5: Redis gate tùy chọn gần đầy, token/Lua/TTL/bounded wait, fallback DB, công cụ benchmark so bật/tắt gate. Mặc định gate tắt, pool hiện có giữ nguyên cho tới khi có số liệu tải triển khai.
- Tuần 6: test T1–T12 dùng lại công cụ invariant của M5, OpenAPI snapshot cập nhật; marker chạy được trong workflow hiện có.
- Tuần 7: slide concurrency trong chat, nội dung dự phòng `docs/m3/slides.md`, kịch bản demo và công cụ demo/benchmark.

## Ranh giới thay đổi

Các file mới thuộc API/schema/service/test/tool/tài liệu M3. Các thay đổi dùng chung giới hạn ở gắn router trong main, biến cấu hình M3 trong config/.env.example và sinh lại OpenAPI do thêm endpoint. Không sửa frontend, engine tiên quyết, auth/admin, migration/seed hay workflow của vai trò khác. `Enrollment` và `Waitlist` hiện có đúng DDL, không tạo model hoặc migration trùng.

## Hợp đồng cần bàn giao

Đọc `docs/enrollment-design.md` để biết schema và quy tắc. Các điểm M3 triển khai theo đề xuất trong phân công: `/courses`, vào hàng tự động từ `/enroll`, Idempotency-Key ở header, min-break mặc định 0, max waitlist dùng ceil, giữ người chờ bị chặn, hủy lặp thành công và không cho đăng ký môn đã đạt. Đây là lựa chọn của bản triển khai để review, không tự đánh dấu các quyết định liên vai trò của M5 đã được nhóm chốt.

## Kiểm chứng

Bản cuối: **292/292 test backend đạt trong 86,12 giây**, trong đó 46 test M3; **20/20 lượt x 12 ca tranh chấp đạt** (240 ca, không gồm spike HTTP 200 request trong vòng lặp). Spike HTTP chạy trong bộ test đầy đủ. Ruff check/format và OpenAPI snapshot đạt; migration/model khớp khi alembic check. Docker API/DB/Redis healthy, seed minimal và đăng nhập + GET courses/timetable/waitlist qua HTTP thật đều thành công. Xem `backend-tests.txt`, `concurrency-20-rounds.txt`, `docker-smoke.json` và `docs/m3/performance.md` cùng các JSON benchmark. Bộ test chạy bằng Python trên Windows kết nối DB/Redis Docker; smoke HTTP chạy ứng dụng trong container. Các số liệu trên là kiểm chứng cục bộ; kết quả CI GitHub xem trong PR của nhánh này. Các phép đo không phải nghiệm thu tải 2.000 sinh viên qua Nginx/TCP. Lệnh chạy lại trong `docs/m3/demo.md`.

## Còn cần nhóm nghiệm thu

- M2 đọc PR, chạy lại và review phần M3 theo vòng review trước khi merge vào main. Kết quả CI và trạng thái review được theo dõi trực tiếp trong PR.
- M1 nối adapter tới `/courses`, `/enroll`, `/timetable`, `/waitlist`, dùng vector lịch chung và chạy E2E giao diện.
- M4 xác nhận pool/timeout/max_connections theo môi trường triển khai; bảng idempotency bền vững chỉ cần nếu nhóm nâng yêu cầu vượt cache best effort hiện tại.
- M5 chốt ngưỡng P95, chạy Locust 2.000 sinh viên/30 giây và đối chiếu trước/sau, cấu hình branch protection và stress định kỳ. Không sửa workflow hay tự nhận các công việc này đã hoàn tất.
- Nhóm tổ chức review, diễn tập giao diện và xác nhận bàn giao/merge. Không đánh dấu các mục phối hợp này là đã xong khi chưa có xác nhận thật.
