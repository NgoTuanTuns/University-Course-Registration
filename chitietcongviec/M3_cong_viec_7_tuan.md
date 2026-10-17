# M3 — Backend Engineer, Enrollment, Concurrency & Waitlist: Công việc chi tiết 7 tuần coding

**Đề tài:** Hệ thống Đăng ký Học phần & Kiểm tra Điều kiện Tiên quyết
**Vai trò:** M3 — API đăng ký an toàn khi tranh chấp, trùng lịch, giới hạn tín chỉ, waitlist, tra cứu học phần
**Căn cứ:** *Báo cáo kế hoạch dự án* (Mục 4.3, 5, 6) và *Quy ước chung của nhóm*.

> **Cách đánh số tuần.** Kế hoạch gốc có 9 tuần; Tuần 1–2 là thiết kế, nên **7 tuần coding còn lại tương ứng Tuần 3–9 của kế hoạch** (giống file của M1, M2). Phần "khảo sát locking" của Tuần 1 gốc được rút gọn thành một ngày chốt thiết kế ở đầu Tuần 1 coding (Mục 1.1).
>
> **Lưu ý về phạm vi:** bảng hợp đồng API (Mục 5 kế hoạch) giao cho M3 endpoint tra cứu `/courses/search` và `/timetable` (cùng M1), nhưng Mục 4.3 và bảng 9 tuần **không xếp việc này vào tuần nào**. Trong file này tra cứu được xếp vào Tuần 1 và `/timetable` vào Tuần 2 để M1 có API thật từ Tuần 3.

---

## 0. Tổng quan 7 tuần

| Tuần coding | Tuần kế hoạch | Trọng tâm | Sản phẩm chính |
|---|---|---|---|
| 1 | 3 | Model `enrollments`/`waitlist`, **tra cứu học phần**, tài liệu thiết kế khóa | `GET /courses` + model + `docs/enrollment-design.md` (bản nháp) |
| 2 | 4 | **`POST /enroll`** đầy đủ luồng: tiên quyết, trùng lịch, tín chỉ, sĩ số; hủy đăng ký; `/timetable` | Đăng ký/hủy chạy đúng khi **không** tranh chấp |
| 3 | 5 | **Optimistic locking hoàn chỉnh**, khóa theo sinh viên, idempotency, test tranh chấp v1, tích hợp M1 | Đăng ký an toàn khi tranh chấp (DB-only) |
| 4 | 6 | **Waitlist + tự động đôn** | Hàng chờ FIFO, đôn trong transaction |
| 5 | 7 | **Redis lock cho cao điểm**, tối ưu theo kết quả spike test | Phiên bản chịu tải, số liệu trước/sau |
| 6 | 8 | **Chốt test tranh chấp**, đóng băng, tài liệu quyết định thiết kế | Bộ test tranh chấp 100% xanh trong CI |
| 7 | 9 | **Bảo vệ**: slide concurrency, demo | Slide + kịch bản demo |

**Ranh giới với người khác:** M3 quyết định *"đăng ký có thành công không"*: sĩ số, tín chỉ, trùng lịch, tranh chấp, waitlist. M3 **không** viết lại logic tiên quyết mà gọi `check_eligibility` của M2.

**Việc lặp lại mỗi tuần:**
- Đầu buổi làm: `git pull`; làm trên nhánh riêng dạng `khoa-enroll-core` (`ten-tinhnang`); commit nhỏ, mô tả rõ.
- Mỗi PR: một bạn khác đọc và chạy thử rồi mới merge. **Vòng review: M2 xem PR của M3; M3 xem PR của M4.**
- Trước khi gộp: checklist Mục 8 quy ước (`ruff`, test cho logic mới, không `print`, Alembic nếu đổi bảng, `.env.example` nếu thêm biến).
- Tham dự buổi review 2 tuần/lần do M5 tổ chức; cập nhật tiến độ lên bảng của M5.

---

## 1. Quy ước M3 phải bám theo (tóm tắt để tra nhanh)

**Phân lớp backend:**
- `api/v1/courses.py`, `enroll.py`, `waitlist.py` (và `timetable.py` — **file này chưa có trong danh sách của quy ước, báo nhóm khi thêm**): chỉ nhận request, kiểm tra dữ liệu, gọi service, trả kết quả.
- `services/enrollment_service.py`, `services/waitlist_service.py` (và hàm thuần `schedule_conflict.py`): chứa logic và **quyết định khi nào commit/rollback**.
- `models/enrollment.py`, `models/waitlist.py`: định nghĩa bảng.

**Code:** `snake_case`/`PascalCase`/`UPPER_CASE`; `ruff`; hàm công khai có type hint; hàm ≤ ~40 dòng (luồng `/enroll` dài → tách thành các bước nhỏ); `async`/`await` cho DB và Redis; **không ghép chuỗi SQL** (dùng SQLAlchemy, kể cả câu cập nhật có điều kiện); giá trị cố định lấy từ `.env`; chỗ khó (tranh chấp, đôn waitlist) phải có comment giải thích.

**Dữ liệu và quy tắc nghiệp vụ:**
- Giữ chỗ bằng **đúng một câu cập nhật có điều kiện**: `UPDATE course_offerings SET enrolled_count = enrolled_count + 1 WHERE id = :id AND enrolled_count < capacity RETURNING id`. Không có dòng trả về nghĩa là lớp đầy → đưa vào waitlist. Redis lock **không thay thế** câu này.
- Tín chỉ đang đăng ký = tổng `credits` của các đăng ký `ACTIVE` trong cùng kỳ; hạn mức là `students.max_credits` (mặc định `DEFAULT_MAX_CREDITS=25`).
- Mỗi sinh viên chỉ có một đăng ký `ACTIVE` cho mỗi lớp (`uq_enrollments_active`); hủy rồi vẫn đăng ký lại được (tạo dòng mới).
- Waitlist: vào trước ra trước theo `(enqueued_at, id)`; `position` chỉ để hiển thị, cập nhật lại mỗi khi hàng chờ đổi; tỷ lệ tối đa theo `WAITLIST_MAX_RATIO` (0.2).
- Khi hủy: giảm `enrolled_count` và đôn người đầu hàng chờ **trong cùng một transaction**.
- Lịch học `schedule` (JSONB): `[{ "day": 2, "start": "07:00", "end": "09:30" }]`, `day` 1–7.

**Redis:** khóa `lock:offering:{offering_id}`, sống 5 giây (tự hết hạn); database 1 khi chạy test.

**Mã trạng thái và mã lỗi M3 dùng:** `201` đăng ký thành công; `200` + `"status": "WAITLISTED"` khi lớp đầy; `PREREQ_NOT_MET` (422), `CREDIT_LIMIT_EXCEEDED` (422), `SCHEDULE_CONFLICT` (409), `ALREADY_ENROLLED` (409), `CONCURRENT_UPDATE` (409), `NOT_FOUND` (404), `FORBIDDEN` (403). **Cần thêm mã mới:** `WAITLIST_FULL`, `ALREADY_WAITLISTED` (Mục 9, điểm 4).

---

## 1.1 Chốt thiết kế (một ngày đầu Tuần 1) — ghi thành `docs/enrollment-design.md`

**(a) Các lớp bảo vệ, mỗi lớp chống một loại lỗi khác nhau:**

| Rủi ro | Cơ chế | Lý do |
|---|---|---|
| Vượt sĩ số khi nhiều người tranh một chỗ | Câu `UPDATE ... WHERE enrolled_count < capacity` (nguyên tử trong Postgres) | Nguồn đúng đắn duy nhất cho sĩ số. Cột `version` **không** bảo vệ được con số này vì nó nằm ở bảng `enrollments`, không phải `course_offerings` |
| Một sinh viên gửi hai yêu cầu song song (khác lớp) cùng vượt qua kiểm tra tín chỉ/trùng lịch rồi cùng ghi | `SELECT ... FROM students WHERE id = :id FOR UPDATE` ở đầu transaction để **tuần tự hóa mọi thao tác của cùng một sinh viên** | Đây là lỗi kiểu "kiểm tra rồi mới làm" (check-then-act) mà câu cập nhật sĩ số không bắt được |
| Hai phiên cùng sửa/hủy một đăng ký | **Optimistic locking** bằng cột `version`: `UPDATE enrollments SET status = 'CANCELLED', version = version + 1 WHERE id = :id AND version = :v AND status = 'ACTIVE'`; 0 dòng → `CONCURRENT_UPDATE` | Đúng mục đích của cột `version` trong thiết kế |
| Double-submit (bấm đúp, thử lại) | Idempotency key + chỉ mục duy nhất `uq_enrollments_active` | Chỉ mục duy nhất là lưới an toàn cuối cùng |
| Quá tải lúc mở đăng ký, cạn connection pool | Redis lock `lock:offering:{id}` (chỉ dùng lúc cao điểm) | Cho yêu cầu **chờ ngoài DB** thay vì giữ kết nối DB chờ khóa dòng |

**(b) Mức cô lập:** giữ mặc định `READ COMMITTED` của PostgreSQL, dựa vào khóa dòng và câu cập nhật có điều kiện. Không dùng `SERIALIZABLE` (tăng độ phức tạp vì phải thử lại). Ghi lý do vào tài liệu — đây là nội dung "so sánh optimistic vs pessimistic và lý do chọn" mà kế hoạch yêu cầu bàn giao.

**(c) Thứ tự kiểm tra và mã lỗi (đề xuất, cần chốt — Mục 9, điểm 5):**
1. Lớp không tồn tại → `404 NOT_FOUND`.
2. Đã đăng ký lớp này (hoặc **cùng môn ở lớp khác trong cùng kỳ**) → `409 ALREADY_ENROLLED`.
3. Thiếu tiên quyết → `422 PREREQ_NOT_MET` (kèm `missing_courses`).
4. Trùng lịch → `409 SCHEDULE_CONFLICT` (kèm danh sách lớp bị trùng).
5. Vượt tín chỉ → `422 CREDIT_LIMIT_EXCEEDED`.
6. Giữ chỗ: được → `201`; hết chỗ → vào waitlist (`200 WAITLISTED`) hoặc `WAITLIST_FULL`.

Kiểm tra tiên quyết (**chỉ đọc**, có cache) đặt **trước** khi khóa dòng sinh viên để rút ngắn thời gian giữ khóa.

**(d) Thứ tự lấy khóa để tránh deadlock:** `(Redis lock lớp) → dòng students → dòng course_offerings (qua UPDATE) → các dòng waitlist`. Với luồng hủy + đôn trong cùng transaction, hai sinh viên (người hủy và người được đôn) cùng bị khóa → **khóa theo thứ tự `id` tăng dần**: đọc trước (không khóa) người đầu hàng chờ, khóa cả hai theo thứ tự `id`, rồi kiểm tra lại người đó vẫn là đầu hàng. Ngoài ra **bắt lỗi deadlock/serialization (`40P01`/`40001`) và thử lại tối đa 3 lần** với độ trễ ngẫu nhiên nhỏ như lưới an toàn.

**(e) Giao diện với M2** (đã thống nhất trong file của M2): `await check_eligibility(session, student_id, course_id) -> EligibilityResult` (`eligible`, `missing_courses` là **mã môn**, `unmet_or_groups`); hàm chỉ đọc, dùng chung `session` của M3, **không** tự commit/rollback.

---

## Tuần 1 (Tuần 3 kế hoạch) — Model, tra cứu học phần, thiết kế khóa

**Mục tiêu:** Có model đúng DDL; `GET /courses` chạy được với 5 bộ lọc; tài liệu thiết kế khóa bản nháp.

### 1.2 Model `enrollments` và `waitlist`
- [ ] Viết `models/enrollment.py` và `models/waitlist.py` **đúng từng cột và ràng buộc** ở Mục 6 quy ước: `status` `VARCHAR` + `CHECK` (không dùng ENUM), `version INTEGER NOT NULL DEFAULT 0`, `enrolled_at`/`cancelled_at`/`enqueued_at` là `TIMESTAMPTZ`, `UNIQUE(student_id, offering_id)` của `waitlist`, **chỉ mục duy nhất từng phần** `uq_enrollments_active ... WHERE status = 'ACTIVE'`, các chỉ mục `ix_enrollments_student`, `ix_enrollments_offering`, `ix_waitlist_queue`.
- [ ] Chuyển cho **M4** trong 2 ngày đầu để M4 gộp vào **một migration duy nhất** (tránh nhiều đầu Alembic). Nếu M3 chậm, M4 có thể tự viết từ DDL — hai bạn trao đổi trước.
- [ ] Quyết định cách bảo vệ `version` ở tầng ORM: dùng **`version_id_col`** của SQLAlchemy (tự tăng, ném `StaleDataError` → đổi sang `CONCURRENT_UPDATE`) hay **câu `UPDATE ... WHERE version = :v` viết tường minh** (Mục 1.1(a)). Đề xuất viết tường minh cho thao tác hủy (rõ ràng, dễ giải thích khi bảo vệ).

### 1.3 `GET /courses` — tra cứu học phần (UR-F-01, SR-F-01)
- [ ] Chốt tên endpoint và tên tham số với M1 trong 2 ngày đầu (Mục 9, điểm 1). Đề xuất tham số: `term`, `q` (từ khóa trên mã/tên môn), `section` (mã lớp), `credits`, `instructor`, `day` + `from` + `to` (khung giờ), `page`, `page_size`. `term` mặc định là kỳ mới nhất trong DB.
- [ ] **Lọc đồng thời trên đúng 5 trường** (từ khóa, mã lớp, tín chỉ, giảng viên, khung giờ); các tham số bỏ trống thì không lọc.
- [ ] Ngữ nghĩa lọc khung giờ (ghi rõ trong Swagger): lớp **có ít nhất một buổi** vào `day` và nằm trong `[from, to]`. Triển khai trên JSONB (`jsonb_array_elements` trong `EXISTS`).
- [ ] Từ khóa dùng `ILIKE` và **escape ký tự `%`, `_`** do người dùng nhập; không ghép chuỗi SQL.
- [ ] Sắp xếp ổn định (`code`, `section`) để phân trang không bị lặp/sót; `page_size` tối đa 100 (vượt thì lỗi `422`); trả `{ items, total, page, page_size }`.
- [ ] Mỗi phần tử gồm: thông tin môn (`code`, `name`, `credits`), thông tin lớp (`id`, `section`, `instructor`, `room`, `schedule`, `capacity`, `enrolled_count`), và đề xuất thêm `my_status` (`ENROLLED`/`WAITLISTED`/`null` cho sinh viên đang đăng nhập) để M1 không cần gọi riêng — cần M1 đồng ý.
- [ ] **Không để N+1** (tải môn kèm lớp bằng join/eager load); kiểm bằng cách đếm truy vấn trong test.
- [ ] Kiểm thử: từng bộ lọc riêng, kết hợp nhiều bộ lọc, phân trang, bộ lọc trả rỗng, ký tự đặc biệt trong từ khóa.
- [ ] Dùng dependency xác thực của M4 (khi M4 chưa xong, dùng cơ chế override giống M2).

### 1.4 Bản nháp tài liệu thiết kế
- [ ] Viết `docs/enrollment-design.md` theo Mục 1.1 (các lớp bảo vệ, mức cô lập, thứ tự kiểm tra, thứ tự khóa). Gửi cả nhóm để duyệt.

### Sản phẩm bàn giao cuối tuần
- Model `enrollments`/`waitlist` đã chuyển M4; `GET /courses` đã merge (có test); tài liệu thiết kế bản nháp.

### Tiêu chí hoàn thành
- Lọc đúng trên dữ liệu seed; không N+1; M1 đã xem và chấp nhận định dạng phản hồi.
- Model khớp DDL (M4 chạy migration thành công trên DB trống).

### Phối hợp
- **M1:** tên endpoint/tham số, định dạng phản hồi (M1 đang làm giao diện tra cứu trên mock).
- **M4:** model, migration, seed có lớp sắp đầy và lớp trùng lịch.
- **M2:** chữ ký `check_eligibility`.
- **M5:** `core/db.py`, khung test (fixture).

---

## Tuần 2 (Tuần 4 kế hoạch) — `POST /enroll` luồng đầy đủ, hủy, thời khóa biểu

**Mục tiêu:** Đăng ký/hủy chạy **đúng** khi chưa có tranh chấp: kiểm tra tiên quyết, trùng lịch, tín chỉ, sĩ số (UR-F-04, UR-F-05, SR-F-04, SR-F-07).

### 2.1 Hàm phát hiện trùng lịch (thuần, kiểm thử độc lập)
- [ ] `find_schedule_conflicts(candidate, existing) -> list[Conflict]` — hàm thuần trong `services/`: cùng `day` và `a.start < b.end && b.start < a.end`; **hai buổi liền nhau (kết thúc 09:30, bắt đầu 09:30) không trùng**; một lớp có nhiều buổi/tuần.
- [ ] **Quy tắc nghỉ giữa hai ca** (Mục 4.3 kế hoạch nhắc tới): chốt có áp dụng hay không (Mục 9, điểm 6). Nếu có, đặt số phút trong `.env` (ví dụ `MIN_BREAK_MINUTES`, mặc định `0`) rồi cập nhật `.env.example`; **M1 phải áp dụng cùng quy tắc ở client**.
- [ ] Tạo **bộ ca kiểm thử dùng chung** (tệp JSON, ví dụ `docs/schedule-test-vectors.json`: trùng hẳn, trùng một phần, liền kề, khác ngày, nhiều buổi) và gửi M1 để Vitest của M1 chạy **cùng bộ ca** — bảo đảm client và server không lệch (tiêu chí nghiệm thu: 0 dương tính/âm tính giả).
- [ ] Kết quả trả về lớp bị trùng (mã môn, lớp) để M1 tô xung đột.

### 2.2 `POST /enroll` — luồng một luồng (chưa tối ưu tranh chấp)
- [ ] Request: `{ "offering_id": 123 }`; idempotency key gửi qua header `Idempotency-Key` (đề xuất; cần chốt — Mục 9, điểm 2).
- [ ] Service `enroll(session, student_id, offering_id)` làm lần lượt (Mục 1.1(c)): tồn tại lớp → đã đăng ký → **tiên quyết (`check_eligibility` của M2)** → trùng lịch → tín chỉ → giữ chỗ.
- [ ] **Tách bước nhỏ** để mỗi hàm ≤ ~40 dòng: `ensure_not_enrolled`, `ensure_prerequisites`, `ensure_no_schedule_conflict`, `ensure_credit_limit`, `reserve_seat`, `create_enrollment`.
- [ ] Giữ chỗ bằng `sqlalchemy.update(...).where(enrolled_count < capacity).returning(...)`; trả dòng → tạo `enrollments` (`version = 0`) → `201`.
- [ ] Không trả dòng (đầy) → **chưa xử lý waitlist trong tuần này**; tạm trả lỗi rõ ràng và để Tuần 4 hoàn thiện (hoặc trả `WAITLISTED` giả lập có cờ cấu hình nếu M1 cần dựng giao diện sớm).
- [ ] Mọi lỗi nghiệp vụ dùng `HTTPException` với `detail = { code, message, ... }`: `PREREQ_NOT_MET` kèm `missing_courses`; `SCHEDULE_CONFLICT` kèm `conflicts_with` (danh sách `{ offering_id, course_code, section }`); `CREDIT_LIMIT_EXCEEDED` kèm `current_credits`, `max_credits`, `requested_credits` (đề xuất, báo M1).
- [ ] Chỉ có **một điểm commit** ở tầng service; router không commit.

### 2.3 `DELETE /enroll/{id}` (hủy)
- [ ] Chỉ chủ sở hữu hủy được; đăng ký của người khác → trả `404` (không để lộ sự tồn tại). Admin có cần quyền hủy hộ không → chốt khi cần.
- [ ] Hủy bằng câu cập nhật theo `version` (Mục 1.1(a)); thành công → giảm `enrolled_count` (ràng buộc `CHECK` không để âm). Phần **đôn waitlist** để Tuần 4.
- [ ] Hủy lần hai trên đăng ký đã hủy: xử lý như **thành công lặp lại (idempotent)** và ghi rõ trong Swagger (chốt cùng M1, vì M1 có thể bấm đúp).

### 2.4 `GET /timetable?term=2026-1`
- [ ] Trả các đăng ký `ACTIVE` của sinh viên trong kỳ kèm thông tin môn/lớp/lịch; **đề xuất thêm `total_credits` và `max_credits`** để M1 dựng thanh tín chỉ mà không cần endpoint riêng (Mục 9, điểm 3). Phối hợp M1 (chủ sở hữu chung).
- [ ] Router `timetable.py` mới (báo nhóm).

### 2.5 Kiểm thử
- [ ] Test API (`httpx` + `pytest-asyncio`) cho từng nhánh lỗi: đã đăng ký, **cùng môn khác lớp**, thiếu tiên quyết, trùng lịch (có và không liền kề), vượt tín chỉ, lớp không tồn tại; đăng ký thành công; hủy rồi đăng ký lại; hủy lớp của người khác.
- [ ] Test hàm trùng lịch bằng bộ vector dùng chung.
- [ ] Tính tín chỉ chỉ cộng đăng ký `ACTIVE` **trong cùng kỳ**.

### Sản phẩm bàn giao cuối tuần
- `POST /enroll`, `DELETE /enroll/{id}`, `GET /timetable` đã merge, đúng nghiệp vụ khi không tranh chấp.
- Bộ vector trùng lịch đã gửi M1.

### Tiêu chí hoàn thành
- Mọi mã lỗi ở Mục 1 trả đúng mã và nội dung; `missing_courses` là mã môn.
- Trùng lịch: 0 dương tính/âm tính giả trên bộ vector.
- **Có thể dùng được với M1 trước đầu Tuần 3** để M1 chuyển sang API thật.

### Phối hợp
- **M2:** tích hợp `check_eligibility` (dùng bản đã merge; nếu M2 chưa xong, dùng bản giả cùng chữ ký rồi thay).
- **M1:** định dạng phản hồi, bộ vector trùng lịch, hành vi hủy lặp.
- **M4:** token và `get_current_user`; seed có ca khó.
- **M5:** fixture; mục "invariant" (M5 bắt đầu viết trong Tuần 2).

---

## Tuần 3 (Tuần 5 kế hoạch) — Optimistic locking hoàn chỉnh, khóa theo sinh viên, idempotency

**Mục tiêu:** Đăng ký đúng khi **nhiều yêu cầu song song** mà chưa cần Redis lock; tích hợp thật với M1 (SR-F-04, SR-NF-04).

### 3.1 Khóa theo sinh viên (chống check-then-act)
- [ ] Đầu transaction (sau bước kiểm tra tiên quyết): `SELECT ... FROM students WHERE id = :student_id FOR UPDATE`. Mọi bước kiểm tra tín chỉ/trùng lịch/trùng đăng ký phải **nằm sau** khóa này.
- [ ] Giữ transaction **ngắn**: không gọi dịch vụ ngoài trong lúc giữ khóa; đặt `lock_timeout` hợp lý (phối hợp M4) để không chờ vô hạn.
- [ ] Bắt `IntegrityError` của `uq_enrollments_active` → `ALREADY_ENROLLED`.

### 3.2 Optimistic locking
- [ ] Mọi thao tác **sửa** `enrollments` (hủy; trạng thái khác nếu có) dùng điều kiện `version`; 0 dòng ảnh hưởng → đọc lại: nếu đã `CANCELLED` thì coi là thành công lặp lại, nếu khác thì `409 CONCURRENT_UPDATE`.
- [ ] Bắt lỗi deadlock/serialization và **thử lại tối đa 3 lần** (Mục 1.1(d)); hết lượt thử → `CONCURRENT_UPDATE`.

### 3.3 Idempotency (chống double-submit)
- [ ] Cùng `Idempotency-Key` + cùng sinh viên → trả **đúng kết quả của lần đầu**, không xử lý lại. Lưu vào Redis, ví dụ `idem:enroll:{student_id}:{key}`, hết hạn sau ~10 phút (**khóa Redis mới → cập nhật Mục 7 quy ước**, Mục 9, điểm 8).
- [ ] Thiếu key → vẫn chạy bình thường (lưới an toàn là chỉ mục duy nhất).
- [ ] Redis lỗi → bỏ qua cơ chế này, **không** làm hỏng đăng ký (đúng đắn dựa vào DB).

### 3.4 Công cụ kiểm tra bất biến
- [ ] Dùng `find_invariant_violations(session)` do **M5** viết ở Tuần 2 (danh sách bất biến ở file của M5). Nếu chưa có khi cần, tự viết bản tạm và hợp nhất sau. Mọi test tranh chấp phải gọi hàm này sau khi chạy xong.

### 3.5 Test tranh chấp v1
Dùng **nhiều session/kết nối thật** (không dùng chung một session), `asyncio.gather`, dữ liệu dựng bằng fixture, cam kết thật (không rollback) rồi dọn bảng:
- [ ] **50–200 sinh viên khác nhau** cùng đăng ký một lớp **còn 1 chỗ** → đúng 1 `ACTIVE`; `enrolled_count = 1`.
- [ ] **Một sinh viên bấm đăng ký hai lần** cùng lúc (cùng/khác key) → đúng 1 đăng ký.
- [ ] **Một sinh viên đăng ký hai lớp khác nhau cùng lúc** khi tín chỉ chỉ đủ cho một → đúng một lớp thành công.
- [ ] **Một sinh viên đăng ký hai lớp trùng giờ cùng lúc** → đúng một lớp thành công.
- [ ] **Hủy đồng thời hai lần** cùng một đăng ký → `enrolled_count` chỉ giảm một lần.

### 3.6 Tích hợp
- [ ] **M1** chuyển sang API thật trong tuần này: chạy cùng M1 các ca đăng ký thành công/trùng lịch/vượt tín chỉ/đã đăng ký/hủy; sửa mọi lệch hợp đồng trong ngày.
- [ ] **M2:** test chung `PREREQ_NOT_MET` có `missing_courses` đúng với cache bật.
- [ ] Ghi nhận các thông số đo ban đầu (thời gian xử lý một lần đăng ký) làm cơ sở cho Tuần 5.

### Sản phẩm bàn giao cuối tuần
- Đăng ký/hủy an toàn khi tranh chấp (DB-only); bộ test tranh chấp v1; M1 chạy end-to-end trên API thật.

### Tiêu chí hoàn thành
- Mọi test tranh chấp ở 3.5 xanh **ổn định** (chạy lặp ≥ 20 lần không lần nào đỏ).
- `find_invariant_violations` không báo vi phạm sau mỗi test.

### Phối hợp
- **M1:** tích hợp thật; **M5:** pipeline tích hợp, invariant; **M4:** `lock_timeout`, cấu hình pool.

---

## Tuần 4 (Tuần 6 kế hoạch) — Waitlist và tự động đôn

**Mục tiêu:** Hàng chờ FIFO công bằng; hủy lớp tự động đôn người kế tiếp trong transaction (UR-F-04, UR-NF-03, SR-F-05, SR-F-06).

### 4.1 Vào hàng chờ
- [ ] Khi lớp đầy (câu giữ chỗ không trả dòng): **sau khi đã qua mọi kiểm tra** (tiên quyết, trùng lịch, tín chỉ — nếu không, hàng chờ đầy sinh viên không đủ điều kiện) → thêm vào `waitlist` và trả `200` với `"status": "WAITLISTED"`, `position`.
- [ ] Giới hạn: `max_waitlist = ceil(capacity × WAITLIST_MAX_RATIO)` (đề xuất `ceil` để mỗi lớp có ít nhất một chỗ chờ — chốt, Mục 9, điểm 7). Vượt → `WAITLIST_FULL`; đã trong hàng → `ALREADY_WAITLISTED`.
- [ ] Tính `position` **an toàn khi tranh chấp** (không để hai người cùng một vị trí): thao tác trong transaction đang giữ khóa dòng sinh viên **và** khóa dòng lớp (`SELECT ... FOR UPDATE` trên `course_offerings`) khi cần tính vị trí mới.
- [ ] Chốt với M1: dùng `POST /enroll` tự đưa vào hàng chờ, hay có bước xác nhận riêng qua `POST /waitlist` (Mục 9, điểm 9).

### 4.2 Các endpoint hàng chờ
- [ ] `GET /waitlist`: các lớp sinh viên đang chờ, `position`, `enqueued_at`, thông tin lớp.
- [ ] `POST /waitlist` (vào hàng chờ tường minh, nếu nhóm chọn cách đó).
- [ ] **`DELETE /waitlist/{id}`** — M1 có nút "Rời hàng chờ" nhưng hợp đồng gốc chỉ liệt kê `GET/POST`; cần thêm và báo M1/M5 (Mục 9, điểm 10). Sau khi rời, **cập nhật lại `position`** của những người phía sau.
- [ ] Chỉ chủ sở hữu mới thấy/xóa được dòng của mình.

### 4.3 Tự động đôn khi hủy (trong cùng transaction)
Luồng chuẩn trong `waitlist_service.promote_next(...)`, được `cancel` gọi **trước khi commit**:
1. Hủy đăng ký (theo `version`), giảm `enrolled_count`.
2. Đọc (chưa khóa) người đầu hàng theo `(enqueued_at, id)`; khóa **người hủy và người đầu hàng theo thứ tự `id`**; kiểm tra lại người đó vẫn là đầu hàng (Mục 1.1(d)).
3. Kiểm tra người đó **còn đủ điều kiện**: chưa đăng ký lớp này, không trùng lịch với đăng ký hiện tại, không vượt tín chỉ (và tiên quyết nếu dữ liệu đã đổi).
4. Đủ → giữ chỗ bằng câu cập nhật có điều kiện, tạo `enrollments`, xóa dòng `waitlist`, cập nhật lại `position`.
5. **Không đủ (ví dụ đã đăng ký lớp khác trùng giờ khi đang chờ — "case sinh viên waitlist bị khóa bởi học phần khác" ở Mục 4.3 kế hoạch):** bỏ qua người này và **xét người kế tiếp**, lặp đến khi đôn được một người hoặc hết hàng.
- [ ] Cách xử lý người bị bỏ qua cần chốt (Mục 9, điểm 6): **giữ nguyên chỗ trong hàng** (đề xuất — không cần đổi schema; `GET /waitlist` tính thêm `blocked_reason` = `SCHEDULE_CONFLICT`/`CREDIT_LIMIT_EXCEEDED` khi đọc) hay **xóa khỏi hàng**. M1 cần để hiển thị lý do rõ ràng.
- [ ] Quy tắc công bằng: lớp còn chỗ trống mà hàng chờ chưa đôn kịp → ghi rõ trong tài liệu việc người mới có thể "chen" hay không (đề xuất: được phép vì chỗ thực sự còn trống, nhưng đôn luôn chạy ngay trong transaction hủy nên khoảng hở không đáng kể).
- [ ] Mỗi lần đôn ghi **log có cấu trúc** (`offering_id`, `student_id`, thời gian chờ) vì bảng không lưu lịch sử đôn — phục vụ báo cáo của M4/M5 (Mục 9, điểm 12).

### 4.4 Kiểm thử
- [ ] Đôn đúng thứ tự FIFO (nhiều người chờ, nhiều lần hủy).
- [ ] Người đầu hàng bị trùng lịch/vượt tín chỉ → bỏ qua, đôn người sau; vị trí được tính lại.
- [ ] Giới hạn tỷ lệ hàng chờ; vào hàng hai lần; rời hàng và cập nhật `position`.
- [ ] **Tranh chấp:** hai người cùng hủy lúc lớp có 2 người chờ → cả hai chỗ trống được đôn đúng thứ tự, không đôn trùng một người; hủy và đăng ký trực tiếp cùng lúc vào lớp vừa trống.
- [ ] Dùng `find_invariant_violations` sau mỗi test (có thêm bất biến về hàng chờ).

### Sản phẩm bàn giao cuối tuần
- Waitlist chạy end-to-end với M1; hủy tự động đôn đúng FIFO; bộ test hàng chờ.

### Tiêu chí hoàn thành
- Đôn đúng thứ hạng và **xử lý đúng ca không còn đủ điều kiện** (tiêu chí nghiệm thu thứ tư của kế hoạch).
- Không đôn trùng, không vượt sĩ số, `position` liên tục từ 1.

### Phối hợp
- **M1:** hành vi đôn, lý do bị chặn, `DELETE /waitlist`; **M5:** bug bash và spike test lần đầu (số liệu baseline); **M4:** thống kê hàng chờ (Mục 9, điểm 12).

---

## Tuần 5 (Tuần 7 kế hoạch) — Redis lock cho cao điểm, tối ưu theo spike test

**Mục tiêu:** Chịu được spike (2.000 sinh viên trong 30 giây) mà vẫn đúng 100% sĩ số (SR-NF-04, SR-NF-05).

### 5.1 Khóa phân tán Redis
- [ ] Hàm `acquire_offering_lock(offering_id)` dùng `SET lock:offering:{id} <token> NX PX 5000`; **giải phóng bằng so sánh token** (script Lua "xóa nếu đúng token") để không xóa nhầm khóa của người khác.
- [ ] Chờ khóa có giới hạn (thử lại với độ trễ ngẫu nhiên, tổng tối đa ~1–2 giây); hết giờ → `CONCURRENT_UPDATE` (M1 sẽ tự thử lại một lần).
- [ ] Khóa chỉ là **lớp bảo vệ thêm**: Redis sập/không lấy được → bỏ qua khóa và dựa hoàn toàn vào DB (câu cập nhật có điều kiện + khóa sinh viên). Đúng đắn **không bao giờ** phụ thuộc Redis.
- [ ] **Dùng có điều kiện ("fallback cho cao điểm" như kế hoạch):** chỉ lấy khóa khi lớp sắp đầy hoặc đang có tranh chấp cao; số ngưỡng đặt trong `.env` (ví dụ `LOCK_SEAT_THRESHOLD`) và đo bằng benchmark. Nếu thêm biến, cập nhật `.env.example`.
- [ ] Thứ tự khóa luôn là: Redis lock lớp → dòng `students` → dòng `course_offerings` (Mục 1.1(d)).

### 5.2 Tối ưu theo số liệu
- [ ] Đọc báo cáo spike test lần đầu của M5 (Tuần 4): chỗ nào chậm, lỗi 5xx, `CONCURRENT_UPDATE` nhiều, hết connection.
- [ ] Rà **connection pool** của SQLAlchemy (`pool_size`, `max_overflow`, `pool_timeout`) và `max_connections` của Postgres; phối hợp M4 (DB) và M5 (số worker uvicorn).
- [ ] Phân tích "điểm nóng" `enrolled_count` (nhiều yêu cầu cùng cập nhật một dòng lớp): so sánh có/không có Redis lock.
- [ ] Rút ngắn transaction: tiên quyết (cache) và các kiểm tra chỉ đọc làm trước; chỉ giữ khóa cho phần ghi.
- [ ] (Tùy chọn, chỉ khi số liệu cho thấy cần) bộ đếm chỗ trống trong Redis để từ chối nhanh các yêu cầu chắc chắn không còn chỗ; **sự thật luôn nằm ở DB**, bộ đếm lệch chỉ làm từ chối nhầm sớm/muộn chứ không làm sai sĩ số — phải có cơ chế đồng bộ lại. Nếu làm, đặt tên khóa mới và cập nhật quy ước.

### 5.3 Kiểm thử
- [ ] Chạy lại toàn bộ test tranh chấp (Tuần 3, 4) **với Redis lock bật và tắt**.
- [ ] Redis bị tắt giữa chừng → vẫn đúng; khóa hết hạn khi transaction còn chạy (giả lập bằng TTL ngắn) → vẫn đúng nhờ DB.
- [ ] Hai request cùng lấy khóa → chỉ một người giữ; release bằng sai token không xóa khóa của người khác.

### 5.4 Đo lại
- [ ] Chạy lại spike test cùng M5; ghi **số liệu trước/sau** (P95, tỷ lệ lỗi, tỷ lệ ghi đúng sĩ số, số `CONCURRENT_UPDATE`) cho báo cáo.

### Sản phẩm bàn giao cuối tuần
- Phiên bản có Redis lock (dùng có điều kiện), tối ưu pool/transaction, số liệu trước/sau.

### Tiêu chí hoàn thành
- Spike test: **không có đăng ký vượt sĩ số**, tỷ lệ ghi đúng sĩ số = 100%, P95 trong ngưỡng nhóm đã chốt với M5.
- Redis lỗi không làm sai dữ liệu.

### Phối hợp
- **M5:** kịch bản và báo cáo tải; **M4:** pool, `lock_timeout`, rà bảo mật (rate-limit của `/enroll` — phối hợp để không chặn nhầm kịch bản tải); **M2:** kiểm tra tiên quyết không là điểm nghẽn.

---

## Tuần 6 (Tuần 8 kế hoạch) — Chốt test tranh chấp, đóng băng

**Mục tiêu:** Bộ test tranh chấp ổn định, chạy trong CI, **chặn merge khi bất biến thất bại** (rủi ro đầu tiên của kế hoạch).

### 6.1 Bộ test tranh chấp chính thức
Bảng ca nghiệm thu (làm chung với M5, mọi ca gọi `find_invariant_violations` ở cuối):

| # | Tình huống | Kết quả mong đợi |
|---|---|---|
| T1 | N sinh viên khác nhau tranh 1 chỗ | Đúng 1 `ACTIVE`; còn lại `WAITLISTED` hoặc `WAITLIST_FULL`; `enrolled_count = 1` |
| T2 | Một sinh viên gửi 2 yêu cầu giống nhau (cùng key) | Cùng một kết quả; 1 đăng ký |
| T3 | Một sinh viên gửi 2 yêu cầu (khác key) | Đúng 1 đăng ký, yêu cầu còn lại `ALREADY_ENROLLED` |
| T4 | Một sinh viên đăng ký 2 lớp khi tín chỉ chỉ đủ cho 1 | Đúng 1 thành công; tổng tín chỉ ≤ `max_credits` |
| T5 | Một sinh viên đăng ký 2 lớp trùng giờ | Đúng 1 thành công |
| T6 | Hủy hai lần đồng thời cùng một đăng ký | Giảm `enrolled_count` đúng 1 lần |
| T7 | Hai hủy đồng thời, lớp có 2 người chờ | Cả hai chỗ được đôn theo FIFO, không đôn trùng |
| T8 | Hủy và đăng ký trực tiếp cùng lúc vào lớp vừa trống | Sĩ số đúng; người chờ đầu hàng được xử lý đúng |
| T9 | Người đầu hàng đã bị chặn (trùng lịch) | Bỏ qua, đôn người kế tiếp |
| T10 | Redis tắt | Mọi ca trên vẫn đúng |
| T11 | Khóa Redis hết hạn giữa chừng | Vẫn đúng |
| T12 | Lớp 1 chỗ, 200 yêu cầu (spike nhỏ qua HTTP) | Đúng 1 thành công |

- [ ] Chạy lặp (≥ 20 lần, hạt giống ngẫu nhiên khác nhau) để loại test không ổn định; M5 thêm job "stress" chạy định kỳ.
- [ ] Đưa vào CI; **thất bại → chặn merge**.

### 6.2 Đóng băng và dọn dẹp
- [ ] Chỉ sửa lỗi, không thêm tính năng; `ruff` sạch; hàm công khai có type hint; **không còn `print`**.
- [ ] Rà comment ở chỗ khó: thứ tự khóa, câu cập nhật có điều kiện, đôn trong transaction, thử lại deadlock.
- [ ] Contract test: phản hồi `/courses`, `/enroll`, `/waitlist`, `/timetable` khớp OpenAPI đã đóng băng.
- [ ] Hoàn thiện `docs/enrollment-design.md` thành **tài liệu quyết định thiết kế**: so sánh optimistic và pessimistic, lý do chọn tổ hợp hiện tại, các lớp bảo vệ, thứ tự khóa, số liệu tải, các cách đã loại bỏ và lý do.
- [ ] Chạy từ máy sạch: `docker compose up` → migrate → seed → thử toàn bộ luồng.
- [ ] Hỗ trợ M1/M5 chạy E2E smoke (đăng ký → lớp đầy → waitlist → hủy → được đôn).

### Sản phẩm bàn giao cuối tuần
- Bộ test tranh chấp xanh trong CI; tài liệu quyết định thiết kế; bản đóng băng.

### Tiêu chí hoàn thành
- Không còn lỗi mức nghiêm trọng thuộc phần đăng ký; mọi ca T1–T12 xanh ổn định.

### Phối hợp
- **M5:** CI chặn merge, E2E; **M2:** chốt test nghiệm thu; **M1:** E2E; **M4:** seed demo.

---

## Tuần 7 (Tuần 9 kế hoạch) — Bảo vệ: slide concurrency, demo, trả lời câu hỏi

### 7.1 Slide phần đăng ký & tranh chấp (gợi ý)
- [ ] Bài toán tranh suất; vì sao `version` không đủ để giữ sĩ số.
- [ ] Các lớp bảo vệ: câu cập nhật có điều kiện, khóa dòng sinh viên, optimistic `version`, idempotency, Redis lock — mỗi lớp chống lỗi nào.
- [ ] So sánh optimistic và pessimistic, lý do chọn.
- [ ] Luồng hủy + đôn waitlist trong một transaction; thứ tự khóa chống deadlock.
- [ ] Bộ test tranh chấp (T1–T12) và kết quả spike test (số liệu trước/sau).

### 7.2 Kịch bản demo (3–4 phút)
- [ ] Lớp còn 1 chỗ: chạy kịch bản song song (script) cho thấy đúng 1 người vào, còn lại vào hàng chờ; hiển thị `enrolled_count` khớp.
- [ ] Một người hủy → người đầu hàng được đôn (xem trên giao diện của M1).
- [ ] Hiện kết quả công cụ kiểm tra bất biến (không vi phạm).
- [ ] Phương án dự phòng: video/ảnh chụp; dữ liệu demo cố định của M4; diễn tập ≥ 2 lần.

### 7.3 Chuẩn bị trả lời câu hỏi
- [ ] Vì sao không chỉ dùng Redis lock? (DB mới là nguồn đúng đắn; lock chỉ giảm tải)
- [ ] Redis sập thì sao? Hai yêu cầu cùng một sinh viên thì sao?
- [ ] Vì sao `READ COMMITTED` mà vẫn đúng? Làm sao tránh deadlock khi đôn?
- [ ] Người đầu hàng chờ không còn đủ điều kiện thì sao? Hàng chờ có công bằng không?
- [ ] Làm sao chứng minh "không race condition"? (bộ test T1–T12, kiểm tra bất biến, spike test)

### 7.4 Chốt
- [ ] Nộp tài liệu quyết định thiết kế vào báo cáo tổng hợp do M5 thu thập; chạy thử lần cuối trên máy demo.

### Sản phẩm bàn giao
- Slide phần concurrency, kịch bản demo + bản dự phòng, tài liệu quyết định thiết kế.

---

## 8. Ánh xạ yêu cầu → công việc của M3

| Yêu cầu | Nội dung | Làm ở |
|---|---|---|
| UR-F-01 / SR-F-01 | Tra cứu, lọc đồng thời 5 trường | Tuần 1 |
| UR-F-02 / SR-F-07 | Phát hiện trùng lịch (JSONB) so với đăng ký đang hoạt động | Tuần 2 |
| UR-F-04 / SR-F-04 | Đăng ký trong một transaction; optimistic locking + Redis lock | Tuần 2, 3, 5 |
| UR-F-05 | Không vượt tín chỉ tối đa | Tuần 2, 3 |
| SR-F-05 (một phần) | Ngưỡng tỷ lệ waitlist theo sĩ số | Tuần 4 |
| SR-F-06 / UR-NF-03 | Waitlist FIFO, tự động đôn trong transaction | Tuần 4 |
| SR-NF-04 | Không race condition, không vượt sĩ số | Tuần 3, 5, 6 |
| SR-NF-05 | Chịu tải spike, ghi đúng sĩ số 100% | Tuần 5 |
| SR-NF-02 | Logic đăng ký dễ kiểm thử độc lập (hàm thuần, service tách lớp) | Tuần 2 |

---

## 9. Những điểm cần chốt với nhóm (phát hiện khi đối chiếu tài liệu)

Nên đưa ra trao đổi **ngay trong Tuần 1** (nhiều điểm trùng với file của M1/M2 — ghi chung vào `docs/decisions.md` do M5 giữ):

1. **Tên endpoint và tham số tra cứu:** `/courses` hay `/courses/search`; tên tham số `q`, `section`, `credits`, `instructor`, `day`, `from`, `to`, `term`. (M1)
2. **Idempotency key:** gửi qua header `Idempotency-Key` (đề xuất) hay trong body. (M1)
3. **`GET /timetable`:** trả gì? Đề xuất: các đăng ký `ACTIVE` kèm lịch **và** `total_credits`, `max_credits`. Ngoài ra `max_credits` cũng có thể nằm trong phản hồi đăng nhập của M4 — chọn một nơi. (M1, M4)
4. **Mã lỗi mới:** `WAITLIST_FULL` (409), `ALREADY_WAITLISTED` (409); cập nhật bảng mã lỗi Mục 5 quy ước và báo M1.
5. **Thứ tự kiểm tra và quy tắc "cùng môn, khác lớp":** có chặn đăng ký hai lớp của cùng một môn trong một kỳ không? Mã lỗi dùng `ALREADY_ENROLLED`? Môn đã học xong có được đăng ký lại không (điểm 9 của M2)?
6. **Người đầu hàng chờ không còn đủ điều kiện:** giữ nguyên chỗ hay xóa khỏi hàng? Và quy tắc **nghỉ giữa hai ca** (bao nhiêu phút, `MIN_BREAK_MINUTES`). (M1, M5)
7. **Làm tròn giới hạn waitlist:** `ceil` hay `floor` của `sĩ số × WAITLIST_MAX_RATIO`; lớp nhỏ có được chờ không.
8. **Khóa Redis mới:** `idem:enroll:{student_id}:{key}` (và khóa đếm chỗ trống nếu làm); cập nhật Mục 7 quy ước.
9. **Cách vào hàng chờ:** `POST /enroll` tự đưa vào (đúng quy ước, `200 WAITLISTED`) hay thêm xác nhận qua `POST /waitlist`. (M1)
10. **`DELETE /waitlist/{id}`** cần thêm vào hợp đồng (M1 có nút rời hàng chờ).
11. **Router `timetable.py`** chưa có trong cấu trúc thư mục quy ước.
12. **Lịch sử đôn waitlist:** bảng `waitlist` xóa dòng khi đôn nên **không đo được hiệu suất đôn** từ dữ liệu. Đề xuất: ghi log có cấu trúc mỗi lần đôn; báo cáo thống kê của M4 chỉ gồm trạng thái hiện tại. (M4, M5)

---

## 10. Rủi ro riêng của M3 và cách giảm thiểu

| Rủi ro | Biện pháp |
|---|---|
| Race condition làm vượt sĩ số | Câu cập nhật có điều kiện làm nguồn đúng đắn; bộ test T1–T12 chạy trong CI; kiểm tra bất biến sau mỗi test và sau spike test |
| Vượt tín chỉ/trùng lịch khi một sinh viên gửi nhiều yêu cầu song song | Khóa dòng `students` ở đầu transaction (Mục 1.1(a)); test T4, T5 |
| Deadlock khi hủy + đôn | Khóa theo thứ tự `id`, đọc-rồi-xác-nhận-lại đầu hàng, thử lại tối đa 3 lần; test T7, T8 |
| Redis sập làm hỏng đăng ký | Redis chỉ là lớp bảo vệ thêm; fallback về DB; test T10, T11 |
| Lệch quy tắc trùng lịch giữa client và server | Bộ vector dùng chung với M1; server luôn là nơi quyết định |
| Cạn connection pool lúc spike | Redis lock cho chờ ngoài DB, transaction ngắn, chỉnh pool cùng M4/M5 |
| Chậm tiến độ | Cặp dự phòng chéo **M2↔M3** (M2 hiểu `check_eligibility` và luồng đăng ký); báo sớm ở buổi review 2 tuần/lần; nếu thiếu thời gian, cắt bộ đếm Redis và `my_status` trước, **không cắt** phần kiểm tra bất biến và khóa theo sinh viên |
