# Thiết kế đăng ký học phần — M3

## Phạm vi và hợp đồng

M3 sở hữu tra cứu lớp, đăng ký/hủy, tín chỉ, lịch, tranh chấp và hàng chờ. Dùng nguyên `check_eligibility` của M2, JWT/role của M4 và công cụ bất biến của M5. Hai model `Enrollment` và `Waitlist` hiện có đã khớp DDL: không cần migration mới. Thay đổi `main.py`, cấu hình và snapshot chỉ để nối API M3 vào ứng dụng.

| Endpoint `/api/v1` | Hành vi |
|---|---|
| `GET /courses` | Đăng nhập; lọc đồng thời `q`, `section`, `credits`, `instructor`, `day/from/to`; phân trang tối đa 100 |
| `POST /enroll` | Role student; `{offering_id}`; 201 ACTIVE hoặc 200 WAITLISTED |
| `DELETE /enroll/{id}?version=0` | Chủ sở hữu; version tùy chọn, sai phiên bản ACTIVE trả CONCURRENT_UPDATE; hủy lặp thành công |
| `GET /timetable?term=2026-1` | ACTIVE trong kỳ, `total_credits`, `max_credits` |
| `GET /waitlist` | Hàng của người đang đăng nhập, phân trang, `blocked_reason` |
| `DELETE /waitlist/{id}` | Chủ sở hữu rời hàng, đánh lại position |

`term` mặc định kỳ lớn nhất trong DB. Khung giờ khớp khi cùng **một buổi** có ngày phù hợp và nằm trọn trong khoảng truyền vào. Từ khóa escape `%`, `_`, `\`; truy vấn dùng SQLAlchemy. Search dùng 3 truy vấn (kỳ, count, joined page), không tăng theo số lớp. Search trả mã môn ở `code`, ID lớp ở `id`; timetable thêm `enrollment_id`, waitlist thêm `waitlist_id`. M1 cần nối adapter theo hợp đồng này; M3 không sửa frontend.

## Các lớp bảo vệ

| Rủi ro | Cơ chế |
|---|---|
| Vượt sĩ số | Một UPDATE có điều kiện `enrolled_count < capacity RETURNING id` |
| Cùng sinh viên đăng ký hai lớp vượt tín chỉ/trùng lịch | `students FOR UPDATE` trước mọi kiểm tra và ghi |
| Hủy/ghi đè đồng thời | UPDATE enrollments theo `version` và ACTIVE, tăng version một đơn vị |
| Gửi trùng | Redis `idem:enroll:{student_id}:{key}` TTL 600 giây, partial unique index ACTIVE |
| Hàng chờ vượt giới hạn/trùng vị trí | Khóa dòng offering trước đếm, thêm, xóa, đánh lại thứ tự |
| Cao điểm | Gate Redis tùy chọn cho lớp còn tối đa LOCK_SEAT_THRESHOLD chỗ |

Giữ READ COMMITTED. Optimistic version thích hợp khi sửa một enrollment; không tự bảo vệ được sĩ số nằm ở bảng offering. Khóa bi quan theo sinh viên bảo vệ tập đăng ký đang thay đổi. SERIALIZABLE làm tăng phạm vi retry và chưa có bằng chứng tải cần đổi mức cô lập.

Thứ tự kiểm tra: lớp tồn tại, cùng môn ACTIVE trong kỳ, môn đã đạt, tiên quyết, lịch, tín chỉ, đã chờ, giữ chỗ hoặc vào hàng. Môn đã đạt bị từ chối với ALREADY_COMPLETED. Lịch dùng khoảng nửa mở, liền giờ không xung đột khi MIN_BREAK_MINUTES=0. Tín chỉ chỉ cộng ACTIVE cùng kỳ.

## Khóa và transaction

Đăng ký: gate Redis tùy chọn, students, kiểm tra điều kiện, offering, hàng chờ. Kiểm tra điều kiện của các sinh viên khác nhau chạy song song trước khóa offering; sau khóa đọc lại course_id/term/schedule, nếu đã đổi thì rollback và retry. Khóa students vẫn giữ nguyên nên kiểm tra lịch/tín chỉ của cùng sinh viên luôn tuần tự. Gate dùng một kết nối đọc ngắn lấy gợi ý sĩ số rồi đóng trước khi đợi Redis. Khóa DB luôn áp dụng ngay cả khi gate hết hạn hoặc Redis lỗi. Tiên quyết của M2 được gọi khi giữ khóa để kiểm tra lại trạng thái hiện hành; đây là lựa chọn ưu tiên đúng đắn, cần đo thời gian giữ khóa trước tối ưu thêm.

Hủy: đọc snapshot tất cả sinh viên trong hàng, khóa tập gồm người hủy và người chờ theo ID tăng dần, rồi khóa offering. Đọc lại hàng; nếu có sinh viên chưa khóa thì rollback và thử lại với tập mới. Khóa toàn bộ ứng viên giúp an toàn khi phải bỏ qua nhiều người bị chặn. Đánh đổi: hàng dài làm tăng contention; đo trước khi tối ưu.

Hủy ACTIVE bằng version, giảm sĩ số, xét FIFO `(enqueued_at, id)`. Người không đủ điều kiện giữ nguyên trong hàng, xét tiếp người sau. Người được đôn giữ chỗ bằng UPDATE có điều kiện, tạo enrollment, xóa waitlist và đánh lại position. Tất cả dùng **một commit**. Lỗi rollback cả hủy và đôn. Người mới chỉ lấy được chỗ trống sau transaction này.

FIFO dùng `clock_timestamp()` lúc thêm hàng, tránh timestamp đầu transaction làm đảo thứ tự sau chờ khóa. Giới hạn `ceil(capacity * WAITLIST_MAX_RATIO)`. Người bị chặn nhận mã lý do khi đọc GET waitlist. Sau khi commit thành công, log một JSON chứa event `waitlist_promoted`, `offering_id`, `student_id`, `wait_seconds`. Không log đôn thành công cho transaction đã rollback.

Deadlock `40P01`, serialization `40001`, lock timeout `55P03` và hàng đổi tập khóa được retry trong tối đa 3 lượt xử lý, có jitter. Hết lượt trả 409 CONCURRENT_UPDATE. Vi phạm unique trả 409 ALREADY_ENROLLED.

## Redis và idempotency

Gate dùng `SET lock:offering:{id} token NX PX 5000`, chờ tối đa 1,5 giây. Redis trả bận đến hết hạn trả CONCURRENT_UPDATE. Redis mất kết nối/timeout chuyển về DB. Release dùng Lua so token, không xóa khóa của chủ mới. Mặc định tắt gate vì chưa có benchmark tải mạng của M5 để quyết định bật.

Key idempotency tối đa 128 ký tự, tách theo sinh viên. Khác offering dùng cùng key trả IDEMPOTENCY_KEY_REUSED. Kết quả thành công được lưu trước commit trong khóa sinh viên để request song song đọc lại được; cache chưa đánh dấu committed chỉ replay khi DB đã có dòng tương ứng. Sau commit đánh dấu kết quả đã xác nhận để replay cả khi hàng chờ sau đó bị xóa/đôn. Redis lỗi hoặc hết TTL: không bảo đảm replay cùng response, nhưng DB vẫn ngăn đăng ký trùng, vượt tín chỉ/lịch/sĩ số. Đây là cache best effort, không phải nhật ký idempotency bền vững qua sự cố Redis/process. Nếu nhóm cần bảo đảm tuyệt đối qua crash ở cửa sổ commit/cache, cần M4 phối hợp bảng idempotency/outbox có migration.

## Kiểm chứng và giới hạn nghiệm thu

Các test M3 gắn marker unit/integration/concurrency nên workflow backend hiện tại tự chạy, không cần sửa CI của M5. T1–T12 dùng PostgreSQL thật, session riêng, công cụ `find_invariant_violations` sau race. Spike nhỏ gửi 200 request qua httpx ASGI, không đo Nginx/TCP hay máy chủ triển khai. Bộ vector lịch dùng chung nằm ở `docs/schedule-test-vectors.json`.

Benchmark/demo riêng: `python -m app.tools.m3_benchmark --students 200 --rounds 3 --output ../docs/m3/benchmark-db.json`, thêm `--redis-lock` để so gate. Chỉ chạy khi APP_ENV=test và DATABASE_URL trỏ course_reg_test. Công cụ tạo tài khoản riêng, dọn đúng dữ liệu nó tạo, đo P50/P95 và kiểm tra đôn sau hủy. Xem các file kết quả kèm bàn giao để biết số đo thực tế.

Chưa tự xác nhận: tải 2.000 sinh viên trong 30 giây, ngưỡng P95 chung, chỉnh pool/max_connections, branch protection, review M2, tích hợp frontend và diễn tập nhóm. Các việc này cần phối hợp M1/M4/M5 hoặc trạng thái GitHub bên ngoài. Không ghi nhận đã merge hoặc được thành viên khác nghiệm thu.
