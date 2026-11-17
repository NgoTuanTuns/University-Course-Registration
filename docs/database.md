# Tài liệu Thiết kế & Tối ưu Cơ sở Dữ liệu (M4 — Tuần 5)

**Đề tài:** Hệ thống Đăng ký Học phần & Kiểm tra Điều kiện Tiên quyết  
**Vai trò phụ trách:** M4 (Database & Security Engineer)  
**Ngày cập nhật:** 09/11/2026  
**RDBMS:** PostgreSQL 15.16 (Alpine Linux)  
**ORM / Driver:** SQLAlchemy 2.0 Async + Asyncpg 0.30+

---

## 1. Kiến trúc CSDL & 7 Bảng Cốt lõi

Hệ thống tuân thủ chặt chẽ nguyên tắc đóng băng 7 bảng (Mục 6 Quy ước dự án):

```
       +-----------------+
       |    students     |
       +--------+--------+
                |
     +----------+----------+
     |                     |
     v                     v
+----+-------------+ +----+-------------+
| completed_courses| |   enrollments   |<---+
+----+-------------+ +----+-------------+    |
     |                     |                 |
     |   +-------------+   |   +-------------+----+
     +-->|   courses   |<--+   | course_offerings |
         +------+------+       +--------+---------+
                |                       |
        +-------+-------+               |
        | prerequisites |               v
        +---------------+      +--------+---------+
                               |     waitlist     |
                               +------------------+
```

1. **`students`**: Lưu trữ tài khoản người dùng, phân quyền (`student`, `admin`), thông tin sinh viên (`mssv`, `max_credits`), `password_hash` băm bcrypt.
2. **`courses`**: Danh mục học phần đại học (`code`, `name`, `credits`, `description`).
3. **`course_offerings`**: Lớp học phần mở theo từng học kỳ (`term`, `section`, `capacity`, `enrolled_count`, `schedule` JSONB, `room`).
4. **`prerequisites`**: Cạnh có hướng trong đồ thị tiên quyết (DAG), loại `AND` (`group_no = 0`) hoặc `OR` (`group_no >= 1`).
5. **`completed_courses`**: Điểm và lịch sử các môn học sinh viên đã hoàn thành.
6. **`enrollments`**: Đăng ký học phần của sinh viên (`status`: `ACTIVE`, `CANCELLED`).
7. **`waitlist`**: Hàng đợi đăng ký khi lớp học phần đã đủ sĩ số (`position >= 1`).

---

## 2. Chiến lược Đánh chỉ mục (Indexing Strategy)

Mọi truy vấn chính trong hệ thống đều được hỗ trợ bởi các chỉ mục chuyên dụng:

| Tên chỉ mục / Khóa | Bảng áp dụng | Cột | Mục đích & Loại chỉ mục |
|---|---|---|---|
| `pk_students` | `students` | `id` | Khóa chính (B-tree) |
| `uq_students_email` | `students` | `email` | Tra cứu đăng nhập tức thì $O(1)$ |
| `uq_students_mssv` | `students` | `mssv` | Ràng buộc duy nhất mã số sinh viên |
| `pk_courses` | `courses` | `id` | Khóa chính (B-tree) |
| `uq_courses_code` | `courses` | `code` | Tra cứu học phần theo mã môn ($O(1)$) |
| `pk_course_offerings` | `course_offerings` | `id` | Khóa chính (B-tree) |
| `uq_offerings_course_term_section` | `course_offerings` | `course_id, term, section` | Ngăn tạo trùng lớp học phần trong kỳ |
| `ix_offerings_term` | `course_offerings` | `term` | Lọc danh sách lớp theo học kỳ hiện tại |
| `ix_offerings_course` | `course_offerings` | `course_id` | Kết nối lớp với môn học cha |
| `pk_prerequisites` | `prerequisites` | `course_id, prereq_course_id` | Khóa chính phức hợp, truy xuất quan hệ tiên quyết |
| `ix_prereq_prereq` | `prerequisites` | `prereq_course_id` | Tra cứu ngược (fan-out: môn này là tiên quyết của ai) |
| `pk_completed_courses` | `completed_courses` | `student_id, course_id` | Khóa chính phức hợp, kiểm tra lịch sử học tập tức thì |
| `pk_enrollments` | `enrollments` | `id` | Khóa chính (B-tree) |
| `uq_enrollments_active` | `enrollments` | `student_id, offering_id` | **Chỉ mục duy nhất từng phần** (`WHERE status = 'ACTIVE'`): ngăn chặn đăng ký trùng lặp lớp |
| `ix_enrollments_student` | `enrollments` | `student_id` | Lấy danh sách đăng ký và thời khóa biểu sinh viên |
| `ix_enrollments_offering` | `enrollments` | `offering_id` | Đếm và khóa danh sách đăng ký của một lớp |
| `pk_waitlist` | `waitlist` | `id` | Khóa chính (B-tree) |
| `uq_waitlist_offering_student` | `waitlist` | `offering_id, student_id` | Chặn một sinh viên xếp hàng hai lần vào cùng một lớp |
| `ix_waitlist_queue` | `waitlist` | `offering_id, position` | Lấy đầu hàng chờ để đôn sinh viên vào lớp khi có chỗ trống ($O(1)$) |

---

## 3. Cơ chế Khóa & Kiểm soát Đồng thời (Concurrency Control)

Nhằm chịu tải trong kịch bản mở cổng đăng ký đồng thời 2.000 sinh viên (Spike Test):

1. **Khóa 2 pha theo thứ tự ID sinh viên (Two-Phase Locking):**
   - Khi đăng ký hoặc hủy đăng ký / đôn hàng chờ: hệ thống gom danh sách ID sinh viên bị ảnh hưởng (người hủy và người đứng đầu hàng chờ), sắp xếp theo thứ tự tăng dần (`ORDER BY id ASC`), và khóa bằng `SELECT ... FOR UPDATE`.
   - Việc luôn khóa sinh viên theo thứ tự tăng dần triệt tiêu hoàn toàn nguy cơ **Deadlock** giữa các tiến trình đồng thời.

2. **Khóa Lớp học phần (`FOR UPDATE`):**
   - Hàng `course_offerings` được khóa sau sinh viên để kiểm tra và cập nhật nguyên tử `enrolled_count` và so sánh với `capacity`.

3. **Khóa tư vấn PostgreSQL cho cấu trúc DAG (Advisory Locks):**
   - Thao tác chỉnh sửa đồ thị tiên quyết `/api/v1/admin/prereqs` sử dụng khóa tư vấn cấp transaction:
     ```sql
     SELECT pg_advisory_xact_lock(0x50524551);
     ```
   - Khóa này tự động nhả khi transaction kết thúc (commit hoặc rollback), bảo đảm hai admin không thể ghi đồng thời làm phát sinh chu trình trong DAG.

---

## 4. Cấu hình Kết nối & Hiệu năng (Connection Pooling)

Trong môi trường chịu tải cao (Spike Test 2.000 Users):

- **Asyncpg Connection Pool:**
  + `pool_size`: 20 kết nối thường trực.
  + `max_overflow`: 10 kết nối phụ trội khi cao điểm.
  + `pool_pre_ping`: Bật `True` để phát hiện và loại bỏ kết nối đứt đoạn trước khi giao request.
  + `pool_recycle`: 3.600 giây (1 giờ).
- **PostgreSQL Server Tuning:**
  + `max_connections = 100` (đảm bảo dung lượng dư thừa so với tổng pool của API backend).
  + `statement_timeout = 30000` (30 giây) ngăn chặn truy vấn treo vô hạn làm cạn kiệt pool.
  + `lock_timeout = 10000` (10 giây) tự động ngắt nếu có tranh chấp khóa quá lâu.

---

## 5. Ràng buộc Toàn vẹn (Integrity Constraints)

PostgreSQL đảm bảo tính đúng đắn ở tầng gốc thông qua các ràng buộc `CHECK`:
- `ck_students_role`: `role IN ('student', 'admin')`
- `ck_students_mssv`: `role <> 'student' OR mssv IS NOT NULL`
- `ck_students_max_credits`: `max_credits BETWEEN 1 AND 40`
- `ck_courses_credits`: `credits BETWEEN 1 AND 10`
- `ck_offerings_capacity`: `capacity > 0`
- `ck_offerings_enrolled_range`: `enrolled_count BETWEEN 0 AND capacity`
- `ck_prerequisites_no_self`: `course_id <> prereq_course_id`
- `ck_prerequisites_type`: `type IN ('AND', 'OR')`
- `ck_prerequisites_group`: `(type = 'AND' AND group_no = 0) OR (type = 'OR' AND group_no > 0)`
- `ck_completed_courses_grade`: `grade BETWEEN 0 AND 10`
- `ck_enrollments_status`: `status IN ('ACTIVE', 'CANCELLED')`
- `ck_waitlist_position`: `position > 0`

---

## 6. Quy trình Migration, Seed Dữ liệu & Tài khoản Demo

### 6.1. Alembic Migration
- Kiểm tra đầu migration hiện tại (chỉ có 1 head duy nhất `4cf23a63c3a3`):
  ```bash
  alembic heads
  alembic upgrade head
  ```
- Tạo migration mới sau khi thay đổi SQLAlchemy models:
  ```bash
  alembic revision --autogenerate -m "mo_ta_thay_doi"
  ```

### 6.2. Seed Dữ liệu & Đặt lại Demo Nhanh
- Chạy an toàn (chỉ nạp khi DB còn trống, không ghi đè dữ liệu hiện có):
  ```bash
  python -m app.seed
  ```
- Xóa sạch 7 bảng và nạp lại dữ liệu demo chuẩn (tái lập 100%, hoạt động offline):
  ```bash
  python -m app.seed --reset
  ```
- Sinh 2.000 sinh viên và xuất CSV cho kiểm thử tải Locust:
  ```bash
  python -m app.seed --reset --profile loadtest --export-users users.csv
  ```

### 6.3. Tài khoản Demo Cố định
- **Quản trị viên (Admin):** `admin@uni.edu.vn` / `Admin@123`
- **Sinh viên mẫu (`sv0001` – `sv1000`):** `sv0001@uni.edu.vn` / `Student@123`
  - `sv0001`: Chưa học `INT101` (dùng để demo chặn thiếu tiên quyết khi đăng ký `INT131`).
  - `sv0002`: Đã hoàn thành `INT101`, `INT131`, `INT221`, `INT222`, `INT231` (demo đăng ký thành công & kiểm tra trùng lịch).
  - `sv0003`: Đủ điều kiện tranh suất lớp còn 1 chỗ (`INT341-01`).
  - `sv0004`: Đạt ngưỡng 24/25 tín chỉ trong kỳ (demo vượt `max_credits`).

