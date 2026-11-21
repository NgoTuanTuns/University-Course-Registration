# Bug bash Tuần 4 — Checklist M5 (bản chuẩn bị)

**Trạng thái:** Chưa chạy; cần M1–M4 cùng tham gia buổi 60–90 phút.
**Mục tiêu:** Ghi lỗi có thể tái hiện trên frontend/backend đã tích hợp; không thay thế CI, invariant hay test tải.

## An toàn và chuẩn bị

- Dùng môi trường tích hợp với dữ liệu demo đã thống nhất. Không chạy reset trên `course_reg`/`course_reg_test`; không dùng `docker compose down -v`.
- Tạo trước tài khoản sinh viên thường, sinh viên thiếu tiên quyết, sinh viên gần hạn mức tín chỉ, admin; chuẩn bị lớp còn chỗ, lớp đầy có waitlist, và hai lớp trùng lịch.
- Bật log API và ghi commit SHA, trình duyệt, role/tài khoản giả định, thời điểm thử. Không chụp token, mật khẩu hoặc dữ liệu cá nhân thật.
- Sau các ca thay đổi enrollment/waitlist, chạy kiểm tra invariant trên DB test/tải đã chọn đúng; lưu kết quả cùng issue.
- D10 (đăng ký cùng môn ở nhiều lớp) và D12 (làm tròn giới hạn waitlist) còn mở; ghi lại hành vi quan sát được, chưa phân loại thành bug cho tới khi nhóm chốt.
- D10 (đăng ký cùng môn ở nhiều lớp) và D12 (làm tròn giới hạn waitlist) còn mở; ghi lại hành vi quan sát được, chưa phân loại thành bug cho tới khi nhóm chốt.

## Ma trận chạy

| ID | Vai trò | Thao tác | Kết quả mong đợi |
|---|---|---|---|
| BB-01 | Sinh viên | Đăng nhập, tải trang và làm mới trang | Thông tin tài khoản và trạng thái phiên đúng; lỗi API hiển thị rõ, không làm trắng trang |
| BB-02 | Sinh viên | Tìm môn theo mã/tên, lọc term/khoa, mở kiểm tra tiên quyết | Kết quả khớp truy vấn; thiếu tiên quyết được giải thích và không bị nhầm với lỗi hệ thống |
| BB-03 | Sinh viên đủ điều kiện | Đăng ký lớp còn chỗ | Server trả ACTIVE; lớp xuất hiện trong TKB và tín chỉ cập nhật một lần |
| BB-04 | Sinh viên | Gửi lại đăng ký cùng lớp hoặc cùng môn ở lớp khác | Server từ chối theo quy tắc hiện hành; UI không tạo dòng trùng hoặc cộng tín chỉ sai |
| BB-05 | Sinh viên thiếu điều kiện / vượt giới hạn | Đăng ký lớp không đủ điều kiện | Mã và thông báo nghiệp vụ đúng; dữ liệu enrollment/sĩ số không đổi |
| BB-06 | Sinh viên | Đăng ký lớp trùng lịch với lớp ACTIVE | Cảnh báo/từ chối khớp quy tắc nhóm; TKB không nhận dữ liệu sai |
| BB-07 | Sinh viên | Đăng ký lớp đã đầy | Trạng thái WAITLISTED; vị trí hàng chờ hiển thị; lớp không bị tính như ACTIVE trong TKB/tín chỉ |
| BB-08 | Sinh viên + người trong waitlist | Hủy lớp ACTIVE khi có người chờ | Người đầu hàng được promote đúng một lần; sĩ số và TKB/tín chỉ cập nhật nhất quán |
| BB-09 | Sinh viên trong waitlist | Rời hàng chờ rồi tải lại trang | Dòng bị xóa; không ảnh hưởng enrollment ACTIVE hoặc vị trí người khác ngoài quy tắc đã định |
| BB-10 | Sinh viên | Bấm hủy rồi xác nhận/đóng hộp thoại | Xác nhận hủy chỉ gửi khi đồng ý; thao tác đóng không đổi dữ liệu |
| BB-11 | Sinh viên thường | Mở route/API admin trực tiếp | Backend trả 403; frontend không cho sửa dữ liệu admin |
| BB-12 | Admin | Tạo/sửa/xóa môn với dữ liệu hợp lệ và không hợp lệ | CRUD và validation đúng; lỗi xóa môn đang được tham chiếu giải thích rõ |
| BB-13 | Admin | Xem/thêm/xóa cạnh tiên quyết; thử tạo chu trình | AND/OR group hiển thị đúng; chu trình bị chặn; cache/graph được làm mới sau thay đổi |
| BB-14 | Sinh viên | Refresh token; thử dùng lại token đã rotate hoặc đã logout | Token hết hạn/tái sử dụng bị từ chối theo hợp đồng; phiên UI xử lý an toàn |

## Thông tin ghi cho mỗi issue

| Trường | Nội dung |
|---|---|
| Tóm tắt / mức độ | `[blocker]`, `[major]`, hoặc `[minor]` |
| Phiên bản | Commit SHA, môi trường, trình duyệt, thời điểm |
| Dữ liệu giả lập | Vai trò và các bản ghi test; không đưa credential thật |
| Tái hiện | Các bước ngắn, đánh số |
| Kỳ vọng / thực tế | Kết quả mong đợi và quan sát được |
| Bằng chứng | Ảnh/log đã che thông tin nhạy cảm |
| Theo dõi | Owner đề xuất và có chặn Tuần 5 không |

Mỗi lỗi cần một issue riêng, có owner và mức độ. Chưa gán owner trước khi buổi bug bash diễn ra.
