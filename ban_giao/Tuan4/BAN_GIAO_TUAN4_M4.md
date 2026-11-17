# Bàn giao Tuần 4 — M4 (Seed Ca Khó, API Quản trị Tiên quyết & Báo cáo Thống kê)

**Dự án:** Hệ thống Đăng ký Học phần & Kiểm tra Điều kiện Tiên quyết  
**Người bàn giao:** M4 (Database & Security Engineer)  |  **Ngày bàn giao:** 09/11/2026  
**Căn cứ:** *Quy ước chung của nhóm* và kế hoạch Tuần 4 của M4 (*M4_cong_viec_7_tuan.md*)  
**Nhận bàn giao:** M1 (xây dựng giao diện quản trị DAG Tuần 5), M2 (Prerequisite Engine), M3 (Enrollment), M5 (Test tải Locust & CI)

---

## 1. Tóm tắt công việc hoàn thành

Tuần 4 của M4 hoàn thành 100% các mục tiêu trọng tâm theo kế hoạch:

1. **Seed Ca Khó & Hồ sơ Kiểm thử Tải 2.000 Sinh viên (`seed_data.py` & `seed.py`):**
   - Hỗ trợ hồ sơ `--profile loadtest`: sinh 2.000 sinh viên phục vụ nghiệm thu spike test theo tiêu chuẩn SR-NF-05 của M5.
   - Thêm tham số `--export-users <file.csv>`: xuất danh sách tài khoản (email, password, role, mssv) để M5 nạp trực tiếp vào kịch bản Locust.
   - Đảm bảo đầy đủ các ca thử nghiệm phức tạp:
     + Chuỗi tiên quyết bắc cầu sâu ($\ge 6$ tầng), đồ thị kim cương, môn có nhiều nhóm OR, nhóm OR có tiên quyết riêng.
     + Kịch bản sinh viên: đủ điều kiện, thiếu môn bắc cầu, thỏa / không thỏa nhóm OR, sát hạn mức tín chỉ.
     + Kịch bản lớp học phần: sắp đầy ($29/30$), đã đầy kèm hàng chờ $\ge 3$ sinh viên, trùng lịch, liền kề giờ, nhiều buổi/tuần, lớp chỉ 1 chỗ để demo tranh suất.
     + Nhất quán 100%: `enrolled_count` luôn bằng số đăng ký `ACTIVE`.

2. **Bộ API Quản trị Điều kiện Tiên quyết (`/api/v1/admin/prereqs`):**
   - Toàn bộ router được bảo vệ bởi dependency `require_role("admin")`. Sinh viên truy cập nhận `403 FORBIDDEN`.
   - `GET /api/v1/admin/prereqs`: Lấy danh sách toàn bộ các cạnh tiên quyết hoặc lọc theo `course_id`.
   - `GET /api/v1/admin/prereqs/{course_id}`: Trả về cấu trúc tiên quyết chi tiết của môn học, phân tách rành mạch `and_prerequisites` và danh sách các nhóm `or_groups` (`group_no`), kèm danh sách phẳng `items` để frontend dễ dàng dựng giao diện.
   - `POST /api/v1/admin/prereqs`: Thêm cạnh tiên quyết mới.
     + Kiểm tra ràng buộc hợp lệ: loại `AND` bắt buộc `group_no = 0`, loại `OR` bắt buộc `group_no >= 1` (sai trả `422 VALIDATION_ERROR`).
     + Chặn tự trỏ: `course_id == prereq_course_id` (trả `422 VALIDATION_ERROR`).
     + Kiểm tra tồn tại môn học (trả `404 NOT_FOUND`), chống trùng lặp cạnh (trả `409 ALREADY_EXISTS`).
     + **Chặn chu trình (Cycle Detection):** Tích hợp hàm `ensure_edge_allowed` của M2. Nếu việc thêm cạnh tạo thành vòng lặp (ví dụ $A \rightarrow B \rightarrow A$), API từ chối với HTTP `422` mã `PREREQ_CYCLE` kèm danh sách chuỗi môn học `cycle_path`.
     + **Bảo vệ đồng thời bằng PostgreSQL Advisory Lock:** Giữ khóa `pg_advisory_xact_lock` trong suốt transaction ghi để tuần tự hóa hai admin cùng thêm cạnh đồng thời, ngăn chặn việc cả hai cùng thấy đồ thị cũ rồi tạo vòng.
     + **Tự động xóa cache Redis:** Gọi `invalidate_graph()` ngay sau khi commit thành công.
   - `PUT /api/v1/admin/prereqs/{course_id}/{prereq_course_id}`: Cập nhật loại (`AND`/`OR`) hoặc số nhóm `group_no`.
   - `DELETE /api/v1/admin/prereqs/{course_id}/{prereq_course_id}`: Xóa cạnh tiên quyết an toàn và dọn cache Redis.

3. **Công cụ Báo cáo Thống kê Cơ sở Dữ liệu (`backend/app/reports.py`):**
   - Chạy bằng lệnh: `python -m app.reports` (hỗ trợ cờ `--json` và `--check-only`).
   - Báo cáo 4 nhóm chỉ số quan trọng:
     + **Sĩ số & Lớp học phần:** Tổng sức chứa, tổng số đăng ký, tỷ lệ lấp đầy toàn hệ thống, danh sách lớp đã đầy (100%) và sắp đầy ($\ge 80\%$).
     + **Cấu trúc DAG tiên quyết:** Sử dụng truy vấn đệ quy (`WITH RECURSIVE`) tính độ sâu từng môn học, xác định độ sâu lớn nhất của đồ thị, tổng số cạnh AND/OR, số nhóm OR, môn có nhiều tiên quyết nhất (fan-in max) và môn làm tiên quyết cho nhiều môn nhất (fan-out max).
     + **Hàng chờ (Waitlist):** Tổng số lượt chờ, các lớp có hàng chờ dài nhất, thời gian chờ trung bình và lâu nhất (`now() - enqueued_at`).
     + **Toàn vẹn hệ thống (Invariants):** Tích hợp trực tiếp bộ kiểm tra bất biến từ `app.tools.invariants` của M5 để đảm bảo số liệu thống nhất 100%.

---

## 2. Danh sách file bàn giao (trong `backend/` và `src/`)

### File mới:
| File | Nội dung | Ai dùng |
|---|---|---|
| `app/services/prerequisite_admin_service.py` | Nghiệp vụ quản trị tiên quyết: kiểm tra chu trình, advisory lock, CRUD, dọn cache | Router admin |
| `app/reports.py` | Công cụ dòng lệnh thống kê cơ sở dữ liệu, đo độ sâu DAG và kiểm tra toàn vẹn | Cả nhóm, M2, M5 |
| `tests/test_admin_prereqs.py` | 10 bài unit test kiểm tra toàn diện API `/admin/prereqs` | CI, M4, M5 |
| `tests/test_reports.py` | 4 bài unit test kiểm tra các hàm thống kê báo cáo | CI, M4, M5 |

### File đã cập nhật:
| File | Nội dung cập nhật |
|---|---|
| `app/api/v1/admin.py` | Tích hợp subrouter `/admin/prereqs` song song với `/admin/courses` | M1 (kết nối UI) |
| `app/schemas/prerequisite.py` | Bổ sung các Pydantic schema cho quản trị tiên quyết | M1, M4 |
| `app/seed_data.py` | Bổ sung profile `loadtest` sinh 2.000 sinh viên cho spike test | M5 (Locust) |
| `app/seed.py` | Thêm tùy chọn `--profile loadtest` và `--export-users` xuất file CSV | M5 (Locust) |
| `src/api/admin.ts` | Thêm TypeScript client cho `/admin/prereqs` (`getAdminCoursePrerequisites`, `createAdminPrerequisite`, `updateAdminPrerequisite`, `deleteAdminPrerequisite`) | M1 (UI Tuần 5) |

---

## 3. Hướng dẫn sử dụng cho các thành viên

### 3.1 Dành cho M1 (Frontend Engineer)
1. **Trang Quản trị Điều kiện Tiên quyết (`/admin/prereqs` ở Tuần 5):**
   - Đã có sẵn client trong `src/api/admin.ts`.
   - Xem tiên quyết của một môn: gọi `getAdminCoursePrerequisites(courseId)`. Dữ liệu trả về có sẵn:
     + `and_prerequisites`: danh sách các môn bắt buộc (`type: "AND"`).
     + `or_groups`: danh sách các nhóm tự chọn (`type: "OR"`), mỗi nhóm có `group_no` và danh sách môn `options`.
   - Thêm tiên quyết: gọi `createAdminPrerequisite({ course_id, prereq_course_id, type, group_no })`.
   - Khi admin vô tình tạo chu trình: API trả về HTTP `422` với `detail.code = "PREREQ_CYCLE"` và `detail.cycle_path = ["INT101", "INT131", "INT101"]`. M1 lấy mảng `cycle_path` này hiển thị thông báo trực quan: *"Điều kiện này tạo vòng lặp: INT101 -> INT131 -> INT101"*.
   - Xóa tiên quyết: gọi `deleteAdminPrerequisite(courseId, prereqCourseId)`.

### 3.2 Dành cho M2 & M3 (Prerequisites & Enrollment)
- Bất kỳ thao tác thêm/sửa/xóa nào trên `/admin/prereqs` đều tự động kích hoạt `invalidate_graph()`, đảm bảo cache Redis được làm mới ngay lập tức.
- Truy vấn đệ quy đo độ sâu DAG trong `app.reports` sẵn sàng cung cấp số liệu phân tích độ sâu phục vụ benchmark của M2.

### 3.3 Dành cho M5 (DevOps, Test Tải & CI)
1. **Sinh dữ liệu tải 2.000 sinh viên & xuất tài khoản:**
   ```bash
   python -m app.seed --reset --profile loadtest --export-users locust_users.csv
   ```
2. **Chạy kiểm tra toàn vẹn nhanh trong CI:**
   ```bash
   python -m app.reports --check-only
   ```

---

## 4. Kết quả kiểm thử

- **10/10 tests** `test_admin_prereqs.py`: Passed.
- **4/4 tests** `test_reports.py`: Passed.
- **202/202 unit tests toàn dự án**: Passed 100%.
- **Frontend Typecheck & Prettier**: 100% Passed.
