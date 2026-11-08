# Nội dung slide concurrency M3

Bản slide chỉnh sửa trực tiếp được đính kèm trong chat. Tệp này là nội dung dự phòng theo từng trang, dùng cùng `enrollment-design.md` và `demo.md`.

## 1. Đăng ký học phần an toàn

M3: Enrollment, Concurrency & Waitlist. Hệ thống đăng ký học phần đại học.

## 2. Một chỗ, nhiều yêu cầu

Hai request cùng đọc sĩ số còn trống có thể cùng ghi. UPDATE có điều kiện giữ chỗ nguyên tử trong PostgreSQL. Cột version ở enrollments bảo vệ thao tác sửa/hủy.

## 3. Các lớp bảo vệ

Khóa dòng sinh viên tuần tự hóa kiểm tra tín chỉ và lịch. UPDATE `enrolled_count < capacity` bảo vệ sĩ số. Version bảo vệ hủy bằng phiên bản mong đợi. Idempotency-Key lưu kết quả theo sinh viên trong Redis.

## 4. Thứ tự khóa và thử lại

Khóa student ID tăng dần rồi offering. Hủy khóa cả người hủy và tập người chờ. Đọc lại hàng sau khóa offering, tập sinh viên thay đổi thì thử lại. Deadlock/serialization có tối đa 3 lượt xử lý.

## 5. Hủy và đôn trong một transaction

Hủy ACTIVE theo version, giảm sĩ số đúng một lần. Xét FIFO theo enqueued_at và id. Giữ người bị chặn, xét tiếp người đủ điều kiện. Tạo enrollment, xóa waitlist và đánh lại position trước commit.

## 6. Redis và tính đúng đắn

Gate chỉ bật cho lớp gần đầy khi cấu hình cho phép. TTL 5 giây, Lua kiểm tra token khi release. Redis lỗi chuyển về DB. READ COMMITTED kết hợp khóa dòng và UPDATE có điều kiện.

## 7. Kiểm thử và nghiệm thu

T1–T12 bao phủ tranh chỗ, gửi trùng, tín chỉ, lịch và đôn hàng. Mỗi race kiểm tra invariant của M5. Spike 200 request qua ASGI dùng PostgreSQL thật. Tải 2.000 sinh viên và P95 triển khai cần phối hợp M5.

Số đo bản cuối: 292/292 test backend; 20 lượt x 12 ca tranh chấp đạt; trung vị P95 ba lượt 200 request là 3,60 giây (DB) và 3,83 giây (gate Redis). Cả sáu lượt đo không vi phạm invariant. Nguồn: performance.md và các JSON benchmark cùng thư mục.
