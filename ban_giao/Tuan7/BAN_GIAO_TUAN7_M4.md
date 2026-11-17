# BÀN GIAO CÔNG VIỆC M4 — TUẦN 7 (CHUẨN BỊ BẢO VỆ)

**Vai trò:** M4 (Database & Security Engineer)  
**Nội dung:** Kịch bản demo 3–4 phút phần CSDL/Auth và bộ câu hỏi – trả lời bảo vệ đồ án.

---

## 1. Kịch bản Demo CSDL & Bảo mật (3–4 phút)

1. **Phân quyền RBAC 2 vai trò (`student` / `admin`):**
   - Đăng nhập bằng `sv0001@uni.edu.vn` (`Student@123`) $\rightarrow$ Gọi `GET /api/v1/admin/prereqs` hoặc truy cập trang quản trị $\rightarrow$ Hệ thống chặn với mã HTTP `403 Forbidden`.
   - Đăng nhập bằng `admin@uni.edu.vn` (`Admin@123`) $\rightarrow$ Cho phép truy cập đầy đủ các API `/admin/*`.
2. **Bảo vệ toàn vẹn DAG & Ràng buộc DB:**
   - Dùng tài khoản Admin thử thêm cạnh tiên quyết tạo vòng (cycle) qua `POST /api/v1/admin/prereqs` $\rightarrow$ Hệ thống dùng PostgreSQL advisory lock (`0x50524551`) + kiểm tra DFS và trả về HTTP `422 PREREQ_CYCLE` kèm đường đi chu trình.
   - Ràng buộc `CHECK` tầng PostgreSQL (`enrolled_count BETWEEN 0 AND capacity`) bảo đảm không bao giờ vượt sĩ số ngay cả khi thao tác trực tiếp dưới DB.
3. **Refresh Token Rotation & Rate Limit:**
   - Gọi `POST /api/v1/auth/refresh` cấp cặp token mới và vô hiệu hóa token cũ (chống replay attack).
   - Gửi liên tiếp vượt ngưỡng đăng nhập $\rightarrow$ Middleware trả về HTTP `429 Too Many Requests`.
4. **Đặt lại dữ liệu demo giữa chừng (Phương án dự phòng):**
   - Chạy một lệnh `docker compose exec api python -m app.seed --reset` để đưa toàn bộ 7 bảng về trạng thái chuẩn ban đầu trong ~3 giây.

---

## 2. Bộ Câu hỏi & Trả lời Bảo vệ (Q&A)

### Q1: Vì sao sử dụng `VARCHAR + CHECK` thay vì kiểu `ENUM` của PostgreSQL?
- `ENUM` trong PostgreSQL khó thay đổi/xóa giá trị khi chạy Alembic migration về sau (`ALTER TYPE` bị hạn chế trong transaction). `VARCHAR + CHECK CONSTRAINT` linh hoạt hơn khi mở rộng nhưng vẫn bảo đảm toàn vẹn dữ liệu tuyệt đối ở tầng DB.

### Q2: Vì sao dùng chỉ mục duy nhất từng phần (`uq_enrollments_active`) cho `status = 'ACTIVE'`?
- Cho phép một sinh viên có thể **hủy đăng ký** (`status = 'CANCELLED'`) rồi **đăng ký lại** cùng lớp học phần đó nhiều lần mà vẫn giữ được lịch sử hủy, trong khi đảm bảo tại một thời điểm chỉ có tối đa **1 bản ghi `ACTIVE`** cho cặp `(student_id, offering_id)`.

### Q3: Cơ chế chống Deadlock và Race Condition ở tầng CSDL hoạt động thế nào?
- Sử dụng **Two-Phase Locking theo thứ tự ID tăng dần** (`ORDER BY id ASC`) khi khóa sinh viên bị ảnh hưởng (người hủy và người đầu hàng chờ), sau đó mới khóa `course_offerings` bằng `SELECT ... FOR UPDATE`. Nhờ thứ tự khóa nhất quán, hai transaction đồng thời không bao giờ chờ vòng nhau (zero deadlock).

### Q4: Access Token và Refresh Token khác nhau thế nào? Chuyện gì xảy ra khi Refresh Token bị đánh cắp?
- **Access Token** có thời hạn ngắn (15–30 phút), dùng để xác thực mỗi API request.
- **Refresh Token** có thời hạn dài (7 ngày), lưu kèm `jti` trong Redis và áp dụng **Refresh Token Rotation**: mỗi lần dùng sẽ sinh cặp token mới và thu hồi `jti` cũ. Nếu phát hiện token cũ bị dùng lại (dấu hiệu bị đánh cắp), hệ thống lập tức thu hồi toàn bộ phiên đăng nhập của người dùng đó (`revoke_all_user_tokens`).

### Q5: Vì sao thông báo lỗi đăng nhập không nói rõ sai email hay sai mật khẩu?
- Để chống tấn công dò tìm tài khoản hợp lệ (**Account Enumeration** — OWASP A07). Cả trường hợp sai email và sai mật khẩu đều trả về cùng mã `401` với thông điệp chung và vẫn chạy kiểm tra băm để tránh timing attack.
