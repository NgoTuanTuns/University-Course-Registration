# Kế hoạch triển khai Nhóm tính năng 1 — UniFlow (Học kỳ 2026-2)

Tài liệu này mô tả chi tiết thiết kế dữ liệu, API, thuật toán, giao diện và kế hoạch kiểm thử cho **4 tính năng trọng tâm** mở rộng cho hệ thống đăng ký học phần **UniFlow** theo mô hình Trường Đại học Tôn Đức Thắng (TDTU):

1. **Quản lý giai đoạn đợt đăng ký trên giao diện Admin (Registration Phase Control)**
2. **Đổi lớp học phần an toàn nguyên tử (Atomic Section Swap)**
3. **Gợi ý xếp lịch tự động không trùng ca (Smart Auto-Scheduler)**
4. **Học phí tạm tính theo tín chỉ (Tuition Estimator)**

---

## 0. Thứ tự triển khai khuyến nghị

Để các tính năng liên kết chặt chẽ và không phải sửa đi sửa lại luồng kiểm tra quyền:

```
Giai đoạn 1: Registration Phase Control (DB + API + Admin UI + Student Banner)
     │
     ▼
Giai đoạn 2: Atomic Section Swap (Deadlock-free DB lock + API + Modal Đổi lớp)
     │
     ▼
Giai đoạn 3: Smart Auto-Scheduler (MRV Backtracking + Scoring + Modal Gợi ý TKB)
     │
     ▼
Giai đoạn 4: Tuition Estimator (Pricing Engine + API + Bảng học phí tạm tính)
     │
     ▼
Giai đoạn 5: Kiểm thử tổng thể (Unit + Integration + Concurrency + CI Gates + Re-seed)
```

---

## 1. Quản lý giai đoạn đợt đăng ký (Registration Phase Control)

### 1.1. Mục tiêu nghiệp vụ
Thay vì cố định trạng thái đợt đăng ký qua biến môi trường (`STUDY_PLAN_EDITABLE`), Phòng Đào tạo (Admin) có thể điều hành trực tiếp vòng đời đăng ký của học kỳ `2026-2` ngay trên giao diện quản trị:

| Giai đoạn (`phase`) | Nhãn hiển thị | Quyền Sinh viên (KHHT) | Quyền Sinh viên (ĐKMH & Đổi lớp) | Hành động Admin |
| :--- | :--- | :--- | :--- | :--- |
| `STUDY_PLAN_OPEN` | **Đợt ĐKKHHT** | Thêm / Xóa môn trong KHHT | Khóa (chưa mở ĐKMH) | Theo dõi nhu cầu đăng ký |
| `CLASS_OPENING_REVIEW` | **Chốt mở lớp** | Chỉ xem (đã khóa) | Khóa (đang phân bổ lớp) | Chạy **Chốt mở lớp** (`finalize`) |
| `ENROLLMENT_OPEN` *(mặc định demo)* | **Đợt ĐKMH chính thức** | Chỉ xem (đã khóa) | Đăng ký / Hủy / Đổi lớp / Gợi ý TKB | Giám sát sĩ số, mở thêm lớp |
| `LOCKED` | **Đã khóa sổ học kỳ** | Chỉ xem | Chỉ xem TKB (không đổi/hủy) | Xuất báo cáo cuối đợt |

### 1.2. Cơ sở dữ liệu & Migration
- **Migration mới**: `backend/alembic/versions/0005_add_registration_phases.py` (`down_revision = "0004_add_study_plans"`).
- **Bảng mới**: `term_registration_settings`
  - `id`: `Integer` PK
  - `term`: `String(20)` UNIQUE, NOT NULL (mặc định `"2026-2"`)
  - `phase`: `String(32)` NOT NULL (`STUDY_PLAN_OPEN`, `CLASS_OPENING_REVIEW`, `ENROLLMENT_OPEN`, `LOCKED`)
  - `phase_ends_at`: `DateTime(timezone=True)` NULLABLE (mốc đếm ngược hiển thị cho sinh viên)
  - `note`: `String(300)` NULLABLE (thông báo ngắn của Phòng Đào tạo)
  - `updated_by_id`: `Integer` FK → `students.id` NULLABLE
  - `updated_at`: `DateTime(timezone=True)` NOT NULL
- **Model**: `backend/app/models/registration_phase.py`, đăng ký trong `backend/app/models/__init__.py`.
- **Seed mặc định** (`backend/app/seed_data.py`): tạo sẵn bản ghi kỳ `2026-2` ở trạng thái `ENROLLMENT_OPEN`, `phase_ends_at = now + 7 ngày`, giữ nguyên bối cảnh demo hiện tại (sinh viên đã xong ĐKKHHT và đang vào ĐKMH).

### 1.3. Backend API & Kiểm soát quyền
- `GET /api/v1/registration-phase?term=2026-2` (mọi user đã đăng nhập):
  - Trả về: `term`, `phase`, `phase_label`, `phase_ends_at`, `note`, `can_edit_study_plan`, `can_enroll`, `updated_at`.
- `PATCH /api/v1/admin/registration-phase` (chỉ `admin`):
  - Body: `{ term, phase, phase_ends_at?, note? }`.
  - Ghi nhận `updated_by_id` và `updated_at`.
- **Áp dụng ràng buộc tập trung** (`backend/app/services/phase_service.py`):
  - `study_plan_service.py`: thay kiểm tra `settings.study_plan_editable` bằng kiểm tra `phase == "STUDY_PLAN_OPEN"` (fallback về `settings.study_plan_editable` nếu bảng chưa có dòng cho term trong unit test).
  - `enrollment_service.py`: các hành động `enroll`, `drop`, `swap`, `join_waitlist` yêu cầu `phase == "ENROLLMENT_OPEN"`; nếu không trả `403` với mã lỗi `REGISTRATION_PHASE_CLOSED` kèm thông báo tiếng Việt rõ ràng.

### 1.4. Giao diện Frontend
- **Admin (`/admin/phases` — "Điều hành đợt đăng ký")**:
  - Thanh tiến trình 4 bước (Stepper kiến trúc vuông TDTU) đánh dấu giai đoạn đang hoạt động.
  - Form cập nhật mốc kết thúc đợt (`datetime-local`), ghi chú thông báo và nút chuyển giai đoạn có hộp thoại xác nhận.
- **Sinh viên**:
  - Dải trạng thái gọn ở đầu trang **Tổng quan / Tra cứu học phần / Kế hoạch học tập** hiển thị giai đoạn hiện tại + đồng hồ đếm ngược thời gian còn lại (ví dụ: `Đợt ĐKMH chính thức · Còn 6 ngày 23 giờ`).
  - Tự động ẩn/khóa nút tương tác phù hợp với `can_edit_study_plan` và `can_enroll`.

---

## 2. Đổi lớp học phần an toàn nguyên tử (Atomic Section Swap)

### 2.1. Mục tiêu nghiệp vụ
Cho phép sinh viên đang đăng ký một lớp (ví dụ `INT131 - Lớp 01`) chuyển sang một lớp khác cùng môn (`INT131 - Lớp 02`) trong **1 thao tác duy nhất** mà **không bao giờ bị mất chỗ cũ** nếu lớp mới hết chỗ hoặc bị trùng lịch.

### 2.2. Backend API & An toàn đồng thời (Concurrency & Deadlock-free)
- **Endpoint**: `POST /api/v1/enroll/swap` (hỗ trợ header `Idempotency-Key` giống `POST /api/v1/enroll`).
- **Request**: `{ from_enrollment_id: number, to_offering_id: number }`.
- **Luồng xử lý nguyên tử trong 1 PostgreSQL Transaction** (`backend/app/services/enrollment_service.py`):
  1. Kiểm tra `phase == "ENROLLMENT_OPEN"`.
  2. Khóa hàng sinh viên (`SELECT ... FROM students WHERE id = :sid FOR UPDATE`) để chống đăng ký/đổi song song từ nhiều tab.
  3. Tìm `from_enrollment` (`ENROLLED`, thuộc đúng `student_id`) → lấy `from_offering_id`.
  4. Kiểm tra `from_offering_id != to_offering_id`, cùng `course_id`, cùng `term`, và `to_offering` có trạng thái `OPENED`.
  5. **Khóa 2 bản ghi `course_offerings` theo thứ tự ID tăng dần** (`ORDER BY id ASC FOR UPDATE`) → đảm bảo **tuyệt đối không xảy ra deadlock** khi 2 sinh viên đổi chéo lớp cho nhau (`01 → 02` và `02 → 01`) cùng lúc!
  6. Kiểm tra sĩ số `to_offering.enrolled_count < to_offering.capacity` (nếu đầy → rollback, trả `409 SECTION_FULL`, giữ nguyên lớp cũ).
  7. Kiểm tra trùng lịch của `to_offering` với các lớp đang `ENROLLED` khác **loại trừ `from_enrollment`** (nếu trùng → rollback, trả `409 SCHEDULE_CONFLICT` kèm mã môn bị trùng).
  8. Thực thi nguyên tử:
     - Đánh dấu `from_enrollment.status = "DROPPED"`, `dropped_at = now()`.
     - Giảm `from_offering.enrolled_count -= 1`.
     - Tạo bản ghi `Enrollment` mới cho `to_offering_id` với `status = "ENROLLED"`.
     - Tăng `to_offering.enrolled_count += 1`.
     - Kích hoạt `promote_waitlist(from_offering_id)` để đôn người đầu hàng chờ của lớp cũ (nếu có).
  9. Trả về `200 OK` gồm thông tin lớp mới, lớp cũ và `promoted_waitlist_count`.

### 2.3. Giao diện Frontend
- **Vị trí kích hoạt**:
  - Trên mỗi thẻ lớp ở trang **Thời khóa biểu** (`Lớp đang đăng ký`): thêm nút **`Đổi lớp`** bên cạnh **`Hủy đăng ký`**.
  - Trên dòng lớp đã tô xám ở trang **Tra cứu học phần**: thêm nút **`Đổi lớp`** nhỏ bên cạnh nhãn `Đã đăng ký`.
- **Hộp thoại Đổi lớp (`SwapSectionModal.tsx`)**:
  - Hiển thị lớp hiện tại ở trên cùng.
  - Liệt kê các lớp `OPENED` khác của cùng học phần (sĩ số, giảng viên, ca học chuẩn TDTU, phòng học).
  - Tự tính và gắn nhãn ngay từng lớp: `Không trùng lịch` (xanh lá), `Trùng với <MÃ MÔN>` (đỏ, khóa nút chọn), hoặc `Đã đầy` (xám, khóa nút chọn).
  - Bấm **`Xác nhận đổi lớp`** → gọi `POST /api/v1/enroll/swap` → cập nhật ngay TKB, bảng Tra cứu học phần và Học phí.

---

## 3. Gợi ý xếp lịch tự động không trùng ca (Smart Auto-Scheduler)

### 3.1. Mục tiêu nghiệp vụ
Sinh viên chọn tập môn muốn học (mặc định tự nạp các môn `OPENED` trong **KHHT** mà sinh viên chưa đăng ký) và các ưu tiên cá nhân → hệ thống tự động tìm ra **tối đa 3 phương án thời khóa biểu tối ưu, hoàn toàn không trùng ca**, cho xem trước trực quan và đăng ký hàng loạt.

### 3.2. Thuật toán & Thiết kế Backend
- **Service mới**: `backend/app/services/scheduler_service.py` (tách thuần logic để viết unit test dễ dàng).
- **Endpoint**: `POST /api/v1/scheduler/suggest`
  - **Request**:
    ```json
    {
      "course_ids": [12, 18, 25],
      "preferences": {
        "avoid_shift_1": true,
        "avoid_shift_5": true,
        "avoid_saturday": false,
        "minimize_days": true,
        "time_of_day": "ANY"
      },
      "max_results": 3
    }
    ```
    *(Nếu `course_ids` để trống, tự lấy toàn bộ môn `OPENED` trong KHHT kỳ `2026-2` mà sinh viên chưa đăng ký).*
- **Các bước thuật toán**:
  1. **Lọc điều kiện đầu vào**:
     - Giữ các môn thuộc khoa sinh viên, trạng thái `OPENED`, đã đạt điều kiện tiên quyết & tín chỉ tích lũy, và chưa đăng ký.
     - Môn không đạt điều kiện hoặc hết chỗ ở mọi lớp được đưa vào danh sách `unschedulable` kèm lý do rõ ràng (`NOT_OPENED`, `PREREQ_UNMET`, `ALL_SECTIONS_FULL`, `CONFLICT_WITH_ENROLLED`).
  2. **Kiểm tra hạn mức tín chỉ**: cảnh báo nếu tổng tín chỉ vượt `max_credits` (25 TC).
  3. **Cắt tỉa sớm (Pre-pruning)**: loại bỏ các `CourseOffering` đã đầy (`enrolled_count >= capacity`) hoặc trùng lịch với các lớp sinh viên đang `ENROLLED`.
  4. **Tìm kiếm Backtracking theo heuristic MRV (Minimum Remaining Values)**:
     - Sắp xếp các môn theo số lớp hợp lệ tăng dần (môn ít lựa chọn nhất xếp trước để cắt nhánh sớm).
     - Giới hạn ngân sách duyệt tối đa `5.000` trạng thái (`MAX_NODES = 5000`) → thời gian phản hồi ổn định `< 30ms`.
  5. **Hàm chấm điểm đa tiêu chí (`score_plan`)**:
     - Điểm cơ sở: `100`.
     - Phạt theo tùy chọn người dùng: `-15` mỗi ca thuộc Ca 1 (nếu bật `avoid_shift_1`), `-20` mỗi ca thuộc Ca 5 (nếu bật `avoid_shift_5`), `-18` mỗi ca học Thứ 7 (nếu bật `avoid_saturday`), `-8 × số_ngày_đi_học` (nếu bật `minimize_days`), thưởng `+8` cho ca khớp `MORNING` (Ca 1–2) hoặc `AFTERNOON` (Ca 3–4), cộng điểm nhẹ cho lớp còn nhiều chỗ trống.
  6. **Chọn Top 3 phương án khác biệt** (khác nhau ít nhất 1 lớp học phần), sắp xếp theo điểm giảm dần.
- **Response**:
  - `plans[]`: mỗi phương án gồm `rank`, `score`, `total_credits`, `study_days_count`, `tags[]` (ví dụ: `"Chỉ đi học 3 ngày/tuần"`, `"Không có Ca 1"`), và `offerings[]` (đầy đủ thông tin để vẽ lên TKB).
  - `unschedulable[]`: danh sách môn không thể xếp kèm `reason`.

### 3.3. Đăng ký hàng loạt từ phương án gợi ý
- Dùng vòng lặp gọi tuần tự `POST /api/v1/enroll` với `Idempotency-Key` riêng cho từng lớp (hoặc endpoint `POST /api/v1/enroll/batch` bọc lại logic enroll chuẩn), hiển thị kết quả từng môn (`Thành công` / `Vào danh sách chờ` / `Lỗi`) để minh bạch tuyệt đối nếu có lớp vừa bị người khác giành chỗ.

### 3.4. Giao diện Frontend (`AutoSchedulerModal.tsx`)
- Nút **`Gợi ý xếp lịch tự động`** nổi bật (màu Đỏ TDTU hoặc Xanh TDTU) ở thanh tiêu đề của trang **Tra cứu học phần** và **Thời khóa biểu**.
- Bố cục 2 cột trong modal rộng (`1180px`, góc vuông sắc nét):
  - **Cột trái**:
    - Danh sách môn mục tiêu (mặc định tích sẵn các môn trong KHHT chưa đăng ký, cho phép tích thêm/bỏ bớt).
    - Các nút tùy chọn ưu tiên (`Tránh Ca 1 (06:50)`, `Tránh Ca 5 (Tối)`, `Nghỉ Thứ 7`, `Ít ngày đi học nhất`, `Ưu tiên sáng / chiều`).
    - Nút **`Tìm lịch tối ưu`**.
  - **Cột phải**:
    - Tab chọn `Phương án 1`, `Phương án 2`, `Phương án 3` kèm tóm tắt (số ngày học, số tín chỉ, điểm phù hợp).
    - Lưới Thời khóa biểu 5 ca TDTU hiển thị đồng thời **lớp đã đăng ký (Xanh TDTU)** và **lớp gợi ý (Vàng hổ phách nét đứt)** độ tương phản cao.
    - Nút **`Đăng ký toàn bộ phương án này`** (1 chạm).

---

## 4. Học phí tạm tính theo tín chỉ (Tuition Estimator)

### 4.1. Mục tiêu nghiệp vụ
Cung cấp bảng tạm tính học phí minh bạch cho Học kỳ `2026-2` theo số tín chỉ đang đăng ký, tự động cập nhật ngay khi sinh viên đăng ký, đổi lớp hoặc hủy học phần.

### 4.2. Quy tắc tính học phí (`backend/app/core/tuition.py`)
Cấu hình đơn giá theo nhóm học phần (sát mức tham khảo đại học công lập tự chủ):
- **Khối Đại cương & Toán – Khoa học cơ bản** (`BAS*`, `MAT*`, `PHY*`, `GEN*`): `950.000 ₫ / tín chỉ`
- **Khối Chuyên ngành Công nghệ & Kỹ thuật** (`INT*`, `ELE*`, `ENG*`): `1.150.000 ₫ / tín chỉ` + phụ phí phòng máy / thực hành `150.000 ₫ / học phần`
- **Khối Kinh tế & Quản trị** (`MAN*`, `ECO*`, `BUS*`): `1.050.000 ₫ / tín chỉ`
- **Mức mặc định khác**: `1.000.000 ₫ / tín chỉ`

### 4.3. Backend API
- **Endpoint**: `GET /api/v1/students/me/tuition?term=2026-2`
- **Response**:
  ```json
  {
    "term": "2026-2",
    "currency": "VND",
    "payment_deadline": "2027-01-15",
    "total_courses": 4,
    "total_credits": 12,
    "tuition_subtotal": 12000000,
    "lab_fee_total": 150000,
    "total_amount": 12150000,
    "items": [
      {
        "enrollment_id": 101,
        "course_code": "INT131",
        "course_name": "Lập trình hướng đối tượng",
        "section": "01",
        "credits": 3,
        "category": "Chuyên ngành Công nghệ & Kỹ thuật",
        "unit_price": 1150000,
        "lab_fee": 150000,
        "subtotal": 3600000
      }
    ]
  }
  ```

### 4.4. Giao diện Frontend
- **Trang Tổng quan (`/`)**: bổ sung thẻ chỉ số **`Học phí tạm tính`** trong dải `.metric-strip` (định dạng tiền tệ `12.150.000 ₫`, bấm vào để xem bảng kê chi tiết).
- **Trang Thời khóa biểu (`/timetable`) & Hồ sơ học tập (`/academic-record`)**: thêm khối **`Bảng kê học phí tạm tính — Học kỳ 2026-2`** hiển thị từng môn (số TC, đơn giá, phụ phí phòng máy, thành tiền), tổng cộng, hạn đóng học phí và nút **In phiếu tạm tính**.

---

## 5. Kế hoạch kiểm thử & tiêu chuẩn nghiệm thu (CI Gates)

| Nhóm kiểm thử | Nội dung cần bao phủ |
| :--- | :--- |
| **Unit tests (`pytest -m unit`)** | • `test_registration_phases.py`: chuyển pha hợp lệ, phân quyền `can_edit_study_plan` / `can_enroll`.<br>• `test_scheduler_service.py`: tìm lịch không trùng ca, MRV pruning, tôn trọng tránh Ca 1 / Thứ 7 / ít ngày, báo đúng `unschedulable`.<br>• `test_tuition.py`: tính đúng đơn giá từng nhóm mã môn, phụ phí phòng máy, tổng tiền 0 khi chưa đăng ký. |
| **Integration & Concurrency (`pytest -m integration`)** | • `POST /api/v1/enroll/swap`: đổi lớp thành công, lớp mới đầy vẫn giữ nguyên lớp cũ, trùng lịch từ chối, **đổi chéo 2 sinh viên đồng thời không deadlock**, tự đôn waitlist lớp cũ.<br>• `PATCH /api/v1/admin/registration-phase`: khi chuyển sang `LOCKED`, `POST /enroll` và `POST /enroll/swap` trả `403 REGISTRATION_PHASE_CLOSED`. |
| **Frontend checks** | • `npx tsc --noEmit`, `npm run lint`, `npm test -- --run`, `npm run build`. |
| **Backend & Schema gates** | • `ruff check`, `ruff format --check`, `alembic heads` (chỉ có 1 head duy nhất: `0005_add_registration_phases`), cập nhật snapshot `docs/openapi.json`. |
| **Seed & Live Demo** | • Chạy `python -m app.seed --reset` trên Docker DB, kiểm chứng trực tiếp trên tài khoản `sv0587@uni.edu.vn` và `admin@uni.edu.vn`. |
