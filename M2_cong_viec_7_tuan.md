# M2 — Backend Engineer, Prerequisite Validation Engine: Công việc chi tiết 7 tuần coding

**Đề tài:** Hệ thống Đăng ký Học phần & Kiểm tra Điều kiện Tiên quyết
**Vai trò:** M2 — engine kiểm tra tiên quyết (DAG), API `check`/`explain`, cache Redis
**Căn cứ:** *Báo cáo kế hoạch dự án* (Mục 4.2, 5, 6) và *Quy ước chung của nhóm*.

> **Cách đánh số tuần.** Kế hoạch gốc có 9 tuần; Tuần 1–2 là thiết kế, nên **7 tuần coding còn lại tương ứng Tuần 3–9 của kế hoạch**. Phần "nghiên cứu DAG, phác thuật toán" của Tuần 1 gốc được rút gọn thành nửa ngày chốt thiết kế ở đầu Tuần 1 coding (Mục 1.1). Cách làm này giống file của M1.

---

## 0. Tổng quan 7 tuần

| Tuần coding | Tuần kế hoạch | Trọng tâm | Sản phẩm chính |
|---|---|---|---|
| 1 | 3 | Engine v1: bắc cầu (AND), phát hiện chu trình, `GET /prerequisites/check` | Lõi engine thuần Python + bộ test đầu tiên |
| 2 | 4 | **OR-group** + **explain API** + chặn chu trình khi nhập dữ liệu | `POST /prerequisites/explain`, hàm kiểm tra chu trình cho M4 |
| 3 | 5 | **Cache Redis + invalidation**, tích hợp với M3 (`/enroll`) và M1 | Engine có cache, chạy qua API thật |
| 4 | 6 | **Benchmark DAG lớn** (hàng nghìn cạnh) | Bộ sinh DAG, số liệu baseline, đối chứng với bản "oracle" |
| 5 | 7 | **Tối ưu N+1**, tăng tỷ lệ cache hit | Bảng so sánh trước/sau |
| 6 | 8 | **Chốt test nghiệm thu**, đóng băng | Bộ ca nghiệm thu 100% xanh trong CI |
| 7 | 9 | **Bảo vệ**: slide engine, demo, trả lời câu hỏi | Slide + kịch bản demo |

**Ranh giới với người khác:** M2 trả lời câu hỏi *"sinh viên này **đủ điều kiện** học môn X chưa, thiếu gì?"*. M3 quyết định *"đăng ký có thành công không"* (sĩ số, tín chỉ, trùng lịch, tranh chấp). M2 **không** làm sĩ số/tín chỉ/trùng lịch/waitlist.

**Việc lặp lại mỗi tuần:**
- Đầu buổi làm: `git pull`; làm trên nhánh riêng dạng `ha-prereq-engine` (`ten-tinhnang`); commit nhỏ, mô tả rõ.
- Mỗi PR: một bạn khác đọc và chạy thử rồi mới merge. **Vòng review: M1 xem M2 (PR của bạn), M2 xem M3 (bạn xem PR của M3).**
- Trước khi gộp: chạy checklist Mục 8 quy ước (`ruff`, test mới, không `print`, `.env.example` cập nhật, chạy được bằng `docker compose up`).
- Tham dự buổi review 2 tuần/lần do M5 tổ chức; báo tiến độ lên bảng của M5.

---

## 1. Quy ước M2 phải bám theo (tóm tắt để tra nhanh)

**Phân lớp backend (bắt buộc):**
- `api/v1/prerequisites.py` (router): nhận request, kiểm tra dữ liệu, gọi service, trả kết quả. **Không viết logic nghiệp vụ ở đây.**
- `services/prerequisite_engine.py`: toàn bộ logic kiểm tra/giải thích/phát hiện chu trình; (có thể tách thêm `prerequisite_cache.py` nếu file quá dài).
- `models/`: bảng `prerequisites`, `completed_courses`, `courses` (do M4 viết, M2 dùng).
- `schemas/prerequisite.py`: dữ liệu vào/ra (Pydantic).

**Code:** `snake_case` / `PascalCase` / `UPPER_CASE`; `ruff` (format on save); hàm công khai có type hint; hàm ≤ ~40 dòng; `async`/`await` cho DB và Redis; không ghép chuỗi SQL (dùng SQLAlchemy); giá trị cố định lấy từ `.env`; **chỗ khó (thuật toán kiểm tra tiên quyết) phải có comment giải thích**.

**Dữ liệu (bảng `prerequisites`):**
- `type = 'AND'`, `group_no = 0`: bắt buộc phải học xong môn này.
- `type = 'OR'`, `group_no ≥ 1`: các dòng cùng `(course_id, group_no)` là một nhóm, **chỉ cần học xong 1 môn trong nhóm**.
- Đạt khi: (1) mọi môn `AND` đã có trong `completed_courses` **và** (2) mỗi nhóm `OR` có ít nhất một môn đã có.
- `completed_courses` chỉ lưu môn **đã học xong và đạt** → engine không cần xét điểm.
- Khi nhập/sửa dữ liệu phải kiểm tra không tạo vòng lặp; dữ liệu có vòng lặp bị từ chối.

**Redis:**
- Khóa cache: `prereq:{student_id}:{course_id}`, TTL = `PREREQ_CACHE_TTL_SEC` (600 giây).
- Database 0 khi chạy thường, **database 1 khi chạy test**.
- Khi dữ liệu tiên quyết hoặc `completed_courses` của sinh viên thay đổi, **phải xóa các khóa `prereq:*` tương ứng**.

**API:** gốc `/api/v1`; JSON `snake_case`; lỗi trả về qua `HTTPException` với dạng `{ "detail": { "code", "message", ... } }`. Mã liên quan đến M2: `PREREQ_NOT_MET` (422), `NOT_FOUND` (404), `UNAUTHENTICATED` (401), `FORBIDDEN` (403).

**Kiểm thử:** `pytest` + `pytest-asyncio`, file `backend/tests/test_*.py`, chạy trên database riêng `course_reg_test`.

---

## 1.1 Chốt thiết kế (nửa ngày đầu Tuần 1) — kết quả cần ghi lại

Làm xong trước khi viết code engine, ghi thành `docs/prerequisite-engine.md` (ngắn, 1 trang) và gửi cả nhóm.

**(a) Mô hình:** đồ thị có hướng không chu trình (DAG): cạnh `X → Y` nghĩa là "X **cần** Y". Mỗi môn có một biểu thức yêu cầu: `AND(các môn AND) ∧ OR₁ ∧ OR₂ ∧ …`.

**(b) Ngữ nghĩa "bắc cầu" — cần chốt (Mục 9, điểm 1).** Hai cách hiểu:
- **(a) Đề xuất — "đã học nghĩa là đã đủ":** một môn Y được coi là thỏa khi có trong `completed_courses`. Bắc cầu dùng để **giải thích và liệt kê đủ chuỗi môn còn phải học** (A cần B, B cần C, sinh viên chưa có B và C → thiếu cả B lẫn C).
- **(b) Nghiêm ngặt:** mọi tổ tiên của A đều phải có trong `completed_courses`, kể cả khi sinh viên đã có B nhưng thiếu C (dữ liệu miễn học/chuyển điểm).

Đề xuất chọn (a): đúng với thực tế (đã qua B tức đã đạt điều kiện của B), và ví dụ của kế hoạch *"thiếu INT131 — tiên quyết bắc cầu của CS441"* khớp cách này. Nếu nhóm chọn (b), chỉ đổi một hàm đánh giá và một vài ca trong bảng test (các ca đánh dấu *phụ thuộc điểm 1* ở Mục 6.1).

**(c) Giao diện hàm cho M3 gọi trong `/enroll` (chốt với M3 trong 2 ngày đầu):**
```python
# services/prerequisite_engine.py
async def check_eligibility(session, student_id: int, course_id: int) -> EligibilityResult: ...
# EligibilityResult: eligible: bool, missing_courses: list[str]  (mã môn, ví dụ "INT131")
#                    unmet_or_groups: list[OrGroupResult]
```
Hàm **chỉ đọc**, dùng chung `session` của M3 (không tự commit/rollback). M3 dùng `missing_courses` để dựng lỗi `PREREQ_NOT_MET` (422).

**(d) Bản nháp schema JSON — gửi M1 và M5 trong 2 ngày đầu** (M1 cần để làm mock; M1 làm giao diện giải thích ở Tuần 3 của họ). Đây là đề xuất, chốt cùng M1:

`GET /prerequisites/check?course_id=12` → `200`:
```json
{ "course_id": 12, "course_code": "CS441", "eligible": false,
  "missing_courses": ["CS331", "INT131"],
  "unmet_or_groups": [ { "group_no": 1, "options": ["MAT201", "MAT202"] } ] }
```

`POST /prerequisites/explain` (body `{ "course_id": 12 }`) → `200`:
```json
{ "course_id": 12, "course_code": "CS441", "eligible": false,
  "missing": [
    { "course_code": "CS331", "course_name": "…", "kind": "DIRECT",
      "required_by": "CS441", "path": ["CS441", "CS331"] },
    { "course_code": "INT131", "course_name": "…", "kind": "TRANSITIVE",
      "required_by": "CS331", "path": ["CS441", "CS331", "INT131"] } ],
  "unmet_or_groups": [
    { "group_no": 1, "required_by": "CS441",
      "options": [ { "course_code": "MAT201", "can_take_now": true },
                   { "course_code": "MAT202", "can_take_now": false,
                     "missing_courses": ["MAT101"] } ] } ],
  "suggested_order": ["INT131", "CS331"] }
```
`path` đi từ môn đang xét tới môn thiếu để M1 hiển thị "A → B → C" bằng ngôn ngữ thường. Backend trả **dữ liệu có cấu trúc**; lời giải thích bằng tiếng Việt do M1 dựng (thống nhất lại nếu M1 muốn backend trả sẵn câu chữ).

---

## Tuần 1 (Tuần 3 kế hoạch) — Engine v1: bắc cầu, chu trình, `check`

**Mục tiêu:** Lõi engine đúng với tiên quyết AND và bắc cầu; phát hiện chu trình; `GET /prerequisites/check` chạy được.

### 1.2 Thiết kế để không bị chặn chờ M4
M4 làm migrations + seed 200 môn trong chính tuần này. Để M2 không phải chờ, **lõi engine viết thuần Python trên cấu trúc dữ liệu trong bộ nhớ, tách khỏi database**, đồng thời đáp ứng SR-NF-02 (dễ kiểm thử độc lập):

- [ ] `PrerequisiteGraph` (dataclass): dựng từ danh sách cạnh `(course_id, prereq_course_id, type, group_no)`; lưu `and_prereqs[course]` và `or_groups[course][group_no]`.
- [ ] `evaluate(graph, course_id, completed: set[int]) -> EligibilityResult` — hàm thuần, không đụng DB/Redis.
- [ ] Lớp truy cập dữ liệu mỏng: `load_edges(session)` (1 truy vấn lấy toàn bộ bảng `prerequisites`) và `load_completed(session, student_id)` (1 truy vấn). Khi M4 đẩy models lên `main`, nối vào. **Không tự tạo bản sao model** — thống nhất với M4 để họ đẩy `models/course.py`, `prerequisite.py`, `completed_course.py` sớm trong 2 ngày đầu.

### 1.3 Thuật toán kiểm tra (bắc cầu)
- [ ] Duyệt từ môn đích theo các cạnh "cần", **có tập `visited`/ghi nhớ kết quả (memoization)** để môn xuất hiện ở nhiều nhánh (hình kim cương) chỉ được xử lý **một lần** — tránh bùng nổ theo cấp số nhân.
- [ ] Môn thiếu = môn `AND` chưa có trong `completed`; với mỗi môn thiếu, **tiếp tục mở rộng** các tiên quyết của nó để liệt kê đủ chuỗi cần học (theo quyết định 1.1(b)).
- [ ] Dùng **topological sort** (Kahn) trên tập môn thiếu để có thứ tự học hợp lý (`suggested_order`); kết quả này dùng cho explain ở Tuần 2.
- [ ] Viết **vòng lặp/hàng đợi, không đệ quy sâu** (giới hạn đệ quy của Python mặc định ~1000). Có comment giải thích từng bước (theo quy ước "chỗ khó phải có comment").
- [ ] Môn không có dòng tiên quyết nào → `eligible = True`.

### 1.4 Phát hiện chu trình
- [ ] `find_cycle(graph) -> list[int] | None`: DFS ba màu (hoặc Kahn); trả về **đường đi của chu trình** (để báo lỗi dễ hiểu), không chỉ true/false.
- [ ] `would_create_cycle(graph, course_id, prereq_course_id) -> list[int] | None`: thêm cạnh "course_id cần prereq_course_id" tạo vòng khi `course_id` đã **tới được** từ `prereq_course_id` (theo chiều "cần"). Ca đặc biệt: tự trỏ vào chính nó.
- [ ] Ngoại lệ miền dữ liệu `PrerequisiteCycleError(path)`. (Cần mã lỗi API — xem Mục 9, điểm 4.)

### 1.5 API khung `GET /prerequisites/check`
- [ ] Router mỏng trong `api/v1/prerequisites.py`; tham số `course_id`; lấy `student_id` từ JWT (dùng dependency từ `core/security.py` của M4; **khi M4 chưa xong, dùng dependency giả bằng cơ chế override của FastAPI, ghi chú rõ chỗ cần thay**).
- [ ] Sinh viên chỉ kiểm tra cho **chính mình**; tham số `student_id` (nếu có) chỉ dành cho admin, ngược lại `403 FORBIDDEN`.
- [ ] Môn không tồn tại → `404 NOT_FOUND`.
- [ ] Trả `200` với `eligible=false` khi thiếu điều kiện (đây là **kết quả hợp lệ của phép kiểm tra**, không phải lỗi); `PREREQ_NOT_MET` 422 chỉ phát sinh ở `/enroll` (M3) — cần chốt, Mục 9, điểm 8.
- [ ] Schema Pydantic cho request/response; hiển thị đúng trên Swagger `/docs`.

### 1.6 Kiểm thử (pytest)
- [ ] Bộ test tham số hóa cho lõi thuần: không tiên quyết, AND một cấp, chuỗi bắc cầu, **kim cương**, nhiều môn thiếu, sinh viên chưa học gì, chu trình (tự trỏ, vòng 2, vòng 3), thêm cạnh hợp lệ không tạo vòng.
- [ ] Bắt đầu dựng **bảng ca nghiệm thu** chung với M5 (Mục 6.1) — đưa danh sách ca cho M5 vào cuối tuần.

### Sản phẩm bàn giao cuối tuần
- `docs/prerequisite-engine.md` (thiết kế + quyết định bắc cầu) và bản nháp schema đã gửi M1/M5.
- Lõi engine + `find_cycle`/`would_create_cycle` + `GET /prerequisites/check` đã merge (có thể còn dùng xác thực giả).

### Tiêu chí hoàn thành
- Bộ test lõi xanh; engine đúng trên các ca bắc cầu và kim cương; không đệ quy sâu.
- Chu trình trả về **đường đi cụ thể**, không chỉ báo "có vòng".
- Một thành viên khác (M1) đã đọc và chạy thử.

### Phối hợp
- **M4:** models + seed có đủ các ca (bắc cầu, nhóm "hoặc"); `core/security.py`.
- **M3:** chốt chữ ký `check_eligibility` và cách dùng `session`.
- **M1:** schema JSON nháp; phản hồi trước khi M1 làm mock.
- **M5:** bảng ca nghiệm thu.

---

## Tuần 2 (Tuần 4 kế hoạch) — OR-group + explain API + chặn chu trình khi nhập dữ liệu

**Mục tiêu:** Hỗ trợ điều kiện "hoặc"; trả lời được câu hỏi *"vì sao chưa đủ điều kiện và cần học gì"* (UR-F-03, SR-F-02, SR-F-03).

### 2.1 Điều kiện "hoặc" (OR-group)
- [ ] Mở rộng `evaluate`: mỗi nhóm `OR` đạt khi **có ít nhất một** môn trong nhóm nằm trong `completed`; môn đạt khi **tất cả** nhóm `OR` và **tất cả** môn `AND` đều đạt.
- [ ] Ca biên: nhóm `OR` chỉ có 1 môn (tương đương AND), nhiều nhóm `OR` độc lập cùng một môn, `AND` kết hợp `OR`, sinh viên thỏa **cả hai** môn của cùng nhóm.
- [ ] Môn nằm trong nhóm `OR` có tiên quyết riêng: tính `can_take_now` (đủ điều kiện học ngay) cho từng lựa chọn để người dùng biết nên chọn nhánh nào.
- [ ] Nhóm `OR` chưa thỏa: đưa vào `unmet_or_groups`, **không** gộp vào `missing_courses` (vì không bắt buộc học cả nhóm).

### 2.2 Explain API
- [ ] `POST /prerequisites/explain` (body `course_id`), theo schema đã gửi M1 (Mục 1.1(d)). Nếu nhóm chọn `GET` thì đổi theo (Mục 9, điểm 2).
- [ ] Mỗi môn thiếu có `kind` (`DIRECT` / `TRANSITIVE`), `required_by` (môn trực tiếp đòi hỏi) và `path` (đường từ môn đích tới môn thiếu).
- [ ] **Mỗi môn thiếu chỉ trả một đường đi tiêu biểu (đường ngắn nhất)**, không liệt kê mọi đường — số đường đi trong DAG có thể tăng theo cấp số nhân.
- [ ] `suggested_order`: thứ tự học gợi ý theo topological sort.
- [ ] Phản hồi ổn định về thứ tự (sắp xếp xác định) để test và giao diện không "nhảy".
- [ ] Thông tin cho giao diện nói **bằng ngôn ngữ môn học**, không có khái niệm kỹ thuật (UR-NF-02): trả mã môn + tên môn, không lộ `id` nội bộ hay thuật ngữ đồ thị.

### 2.3 Chặn chu trình khi nhập/sửa dữ liệu
- [ ] Cung cấp cho **M4** hàm dùng trong `/admin/prereqs` và `seed.py`: `would_create_cycle(...)` (từng cạnh) và `assert_acyclic(edges)` (kiểm tra cả bộ dữ liệu khi seed/import).
- [ ] Phối hợp M4 để endpoint admin trả lỗi `422` kèm đường đi chu trình (mã lỗi cần thêm vào bảng — Mục 9, điểm 4).
- [ ] Kiểm tra bằng `assert_acyclic` trên dữ liệu seed của M4: **seed có vòng lặp phải bị từ chối**.

### 2.4 Kiểm thử
- [ ] Mở rộng bộ test: OR-group (đủ các ca biên), explain (đường đi, `suggested_order`, `can_take_now`), thêm cạnh gây vòng.
- [ ] Test API (`httpx` + `pytest-asyncio`): `check`/`explain` với sinh viên thật trong database test, kiểm tra `403` khi sinh viên hỏi hộ người khác và `404` khi môn không tồn tại.
- [ ] **Đảm bảo `check`/`explain` đã nằm trên `main` trước đầu Tuần 3**, để M1 chuyển sang API thật (cache sẽ làm sau và trong suốt với API).

### Sản phẩm bàn giao cuối tuần
- Engine hỗ trợ AND + OR + bắc cầu; `POST /prerequisites/explain` theo schema đã chốt.
- Hàm chặn chu trình đã trao cho M4.
- OpenAPI/Swagger của hai endpoint khớp schema (SR-NF-03).

### Tiêu chí hoàn thành
- Toàn bộ ca OR-group trong bảng nghiệm thu đạt 100%.
- M1 dựng được màn hình giải thích chỉ từ schema, không phải hỏi thêm.
- Dữ liệu có vòng lặp không thể vào hệ thống.

### Phối hợp
- **M1:** chốt schema explain; M1 xem lại PR.
- **M4:** gọi `would_create_cycle` ở admin; seed có ca OR và ca khó.
- **M5:** bảng ca nghiệm thu đầy đủ OR.

---

## Tuần 3 (Tuần 5 kế hoạch) — Cache Redis + invalidation, tích hợp

**Mục tiêu:** Kết quả kiểm tra được cache đúng và **luôn bị xóa đúng lúc dữ liệu đổi** (SR-NF-06); engine được `/enroll` của M3 và giao diện của M1 dùng thật.

### 3.1 Kết nối Redis
- [ ] Dùng `core/redis.py`. Cần chốt **ai viết file này** (M2/M3/M5) để không trùng (Mục 9, điểm 6); nếu chưa có, M2 viết bản dùng chung và báo M3 (M3 cũng cần Redis cho lock).
- [ ] Đọc `REDIS_URL` và `PREREQ_CACHE_TTL_SEC` từ `.env`; **test dùng database 1**.

### 3.2 Cache kết quả theo (sinh viên, môn)
- [ ] Khóa `prereq:{student_id}:{course_id}`, TTL = `PREREQ_CACHE_TTL_SEC`; giá trị là JSON của `EligibilityResult`.
- [ ] Luồng: tra Redis → trúng thì trả luôn; trượt thì tính (đọc DB) → ghi cache → trả.
- [ ] `explain` ít gọi hơn và phụ thuộc cùng dữ liệu: chỉ cache nếu số liệu benchmark (Tuần 4–5) cho thấy cần.
- [ ] **Cache là tối ưu, không phải điều kiện đúng đắn:** Redis lỗi/không kết nối được → ghi cảnh báo vào log và **tính trực tiếp**, không làm hỏng API.

### 3.3 Cache đồ thị
- [ ] Lưu toàn bộ danh sách cạnh đã dựng của DAG vào Redis (tránh truy vấn lại bảng `prerequisites` mỗi lần).
- [ ] **Lưu ý đặt tên khóa:** khóa đồ thị **không được bắt đầu bằng `prereq:`**, nếu không sẽ bị xóa nhầm cùng nhóm `prereq:*` (hoặc làm lộn lệnh xóa theo tiền tố). Đề xuất `prereqgraph:v1`. Phải **cập nhật bảng khóa ở Mục 7 quy ước** và báo cả nhóm (Mục 9, điểm 5).

### 3.4 Invalidation (trọng tâm của tuần)
| Sự kiện | Việc cần làm | Ai gọi |
|---|---|---|
| Admin thêm/sửa/xóa tiên quyết (hoặc xóa/sửa môn ảnh hưởng DAG) | Xóa khóa đồ thị **và toàn bộ `prereq:*`** | M4 (admin API), M2 cung cấp hàm |
| `completed_courses` của một sinh viên đổi (seed, import) | Xóa `prereq:{student_id}:*` | M4 (seed/import), M2 cung cấp hàm |
| Seed lại toàn bộ dữ liệu | Xóa toàn bộ `prereq:*` và khóa đồ thị | M4 |

- [ ] Hàm `invalidate_graph()` và `invalidate_student(student_id)` trong `services/`; dùng **`SCAN` theo tiền tố + `UNLINK`/`DEL`, không dùng `KEYS`** (không chặn Redis).
- [ ] Chốt với M4: nơi nào trong code ghi `completed_courses`/`prerequisites` thì phải gọi hàm tương ứng (hiện chưa có API sửa `completed_courses`, chỉ có seed — Mục 9, điểm 7). Tốt nhất M2 gửi sẵn một PR nhỏ gắn lời gọi vào endpoint admin.
- [ ] Lập **bảng "dữ liệu nào đổi → khóa nào xóa"** trong `docs/prerequisite-engine.md`; đây là nội dung hay bị hỏi khi bảo vệ.

### 3.5 Tích hợp
- [ ] **M3:** `check_eligibility` được `/enroll` gọi bên trong transaction; test chung: thiếu tiên quyết → `PREREQ_NOT_MET` (422) kèm `missing_courses` là mã môn.
- [ ] **M1:** hỗ trợ chuyển từ mock sang API thật; sửa lệch hợp đồng nếu có (kiểm tra cùng M1 từng ca bắc cầu/OR trên giao diện).

### 3.6 Kiểm thử
- [ ] Trúng/trượt cache (đếm số lần gọi DB), hết TTL, sau khi sửa DAG kết quả đổi ngay, sau khi sinh viên có thêm môn đã học kết quả đổi ngay.
- [ ] Redis bị tắt → API vẫn đúng (tính trực tiếp).
- [ ] Hai sinh viên khác nhau không dùng chung khóa; khóa đồ thị không bị xóa nhầm khi xóa `prereq:{student_id}:*`.

### Sản phẩm bàn giao cuối tuần
- Engine có cache + invalidation; M3 và M1 dùng được trên API thật.
- Bảng invalidation trong tài liệu; quy ước Redis được cập nhật.

### Tiêu chí hoàn thành
- Sau khi admin sửa DAG hoặc dữ liệu đã học đổi, **không bao giờ trả kết quả cũ** (kiểm bằng test).
- Redis sập không làm API sập.

### Phối hợp
- **M3:** tích hợp `/enroll`; **M4:** gọi invalidation; **M1:** E2E; **M5:** thêm test tích hợp vào pipeline.

---

## Tuần 4 (Tuần 6 kế hoạch) — Benchmark DAG lớn

**Mục tiêu:** Chứng minh engine chạy đúng và đủ nhanh với DAG lớn (hàng nghìn cạnh) và có số liệu baseline để so sánh sau tối ưu.

### 4.1 Bộ sinh DAG tổng hợp
- [ ] Script (`backend/benchmarks/` hoặc `tests/benchmarks/`) sinh DAG có **hạt giống cố định** (tái lập được) theo tham số: số môn, số cạnh, độ sâu tối đa, tỷ lệ nhóm OR, kích thước nhóm OR, mức fan-in. Sinh theo **tầng** để đảm bảo không có chu trình.
- [ ] Các kích cỡ: thực tế (~200 môn / vài trăm cạnh), lớn (~1.000 môn / ~3.000 cạnh), cực đoan (hàng nghìn cạnh, chuỗi sâu 50–100 tầng, lưới kim cương dày).
- [ ] Sinh ngẫu nhiên tập "đã học" của sinh viên (theo tỷ lệ).

### 4.2 Đo hiệu năng
- [ ] Đo riêng **lõi thuần** (thời gian xử lý p50/p95/max, bộ nhớ) và **API đầu-cuối** (qua HTTP, có/không cache).
- [ ] Đếm **số truy vấn SQL cho mỗi lần gọi** (đăng ký lắng nghe sự kiện của SQLAlchemy) — căn cứ chính cho phần "tối ưu N+1" Tuần 5.
- [ ] Giữ một **bản baseline "tải từng tầng" (kiểu N+1)** chỉ trong script benchmark, để có số liệu **trước/sau** thật (không đưa vào code chạy chính).
- [ ] Kiểm tra trường hợp bùng nổ: so sánh có/không có memoization trên lưới kim cương để chứng minh tác dụng.

### 4.3 Đối chứng độ đúng ở quy mô lớn
- [ ] Viết một **"oracle"** ngây thơ nhưng hiển nhiên đúng (đánh giá biểu thức đệ quy trực tiếp, chậm cũng được) rồi so với engine trên hàng nghìn bộ (DAG, sinh viên) ngẫu nhiên có hạt giống. Mọi sai khác phải bằng 0.
- [ ] Nếu nhóm đồng ý thêm thư viện `hypothesis` thì dùng; nếu không, dùng vòng lặp ngẫu nhiên với hạt giống cố định (Mục 9, điểm 12).

### 4.4 Phân tích độ phức tạp
- [ ] Ghi vào tài liệu: kiểm tra một môn là **O(V + E)** trên đồ thị con tới được từ môn đó (nhờ memoization); explain trả **một đường đi/môn thiếu** nên không bùng nổ; so sánh với cách duyệt không nhớ.
- [ ] Phát hiện và sửa điểm nghẽn: đệ quy sâu, cấu trúc dữ liệu chậm (tìm kiếm trong list thay vì set), tính toán lặp.

### 4.5 Báo cáo số liệu baseline
- [ ] Bảng: kích cỡ DAG × thời gian lõi × thời gian API × số truy vấn SQL. Gửi M5 để đưa vào báo cáo chung, đồng thời để M4 có căn cứ làm seed "ca khó" (độ sâu DAG thực tế).

### Sản phẩm bàn giao cuối tuần
- Bộ sinh DAG + script benchmark chạy được bằng một lệnh.
- Bảng số liệu baseline và bản đối chứng với oracle.

### Tiêu chí hoàn thành
- Engine khớp oracle 100% trên toàn bộ bộ ngẫu nhiên.
- Có số liệu cụ thể cho DAG hàng nghìn cạnh; không có ca nào bùng nổ thời gian.

### Phối hợp
- **M4:** độ sâu DAG thực tế của seed; **M5:** đưa số liệu vào báo cáo tải, spike test lần đầu.

---

## Tuần 5 (Tuần 7 kế hoạch) — Tối ưu N+1 và tỷ lệ cache hit

**Mục tiêu:** Giảm số truy vấn và độ trễ, tăng tỷ lệ cache trúng; có bảng so sánh **trước/sau** (SR-NF-05, SR-NF-06).

### 5.1 Tối ưu truy vấn (N+1)
- [ ] Đặt **test đếm truy vấn**: cache trượt → tối đa **một số ít truy vấn cố định** (ví dụ: 1 lấy cạnh + 1 lấy `completed_courses`, hoặc 0 cạnh nếu đã có trong cache đồ thị); cache trúng → **0 truy vấn DB**. Con số cụ thể chốt khi có số liệu Tuần 4.
- [ ] So sánh hai chiến lược bằng benchmark rồi chọn theo số liệu: (1) **nạp toàn bộ DAG và cache đồ thị**; (2) **truy vấn đệ quy `WITH RECURSIVE` chỉ lấy đồ thị con** của môn đang xét. Với ~200 môn, (1) thường đủ; (2) lợi khi DAG rất lớn.
- [ ] Rà index: `ix_prereq_prereq`, khóa chính `(student_id, course_id)` của `completed_courses`; dùng `EXPLAIN ANALYZE` cho truy vấn chính.

### 5.2 Nâng tỷ lệ cache hit
- [ ] Đếm **hit/miss** bằng bộ đếm (log có cấu trúc hoặc khóa đếm trong Redis); nếu dùng khóa Redis mới thì đặt tên khác tiền tố `prereq:` (ví dụ `metrics:prereq:hit`) và cập nhật quy ước (Mục 9, điểm 5).
- [ ] Phân tích mẫu gọi thực tế từ kịch bản Locust của M5 (nhiều sinh viên hỏi cùng một nhóm môn) để chỉnh TTL/chiến lược.
- [ ] **Làm nóng đồ thị khi khởi động** (FastAPI lifespan), tránh "cache stampede" khi khóa đồ thị bị xóa: nhiều request cùng dựng lại — dùng khóa ngắn (`SET NX`, vài giây) để chỉ một request dựng.
- [ ] Gộp thao tác Redis (pipeline/`MGET`) khi có nhiều lần tra liên tiếp.
- [ ] **Đề xuất ngưỡng mục tiêu cùng M5** sau khi có baseline (gợi ý: tỷ lệ trúng cao trong kịch bản tải lặp; con số do hai bạn chốt, đừng tự đặt trước khi có số liệu).

### 5.3 Vòng lặp sự kiện
- [ ] Lõi engine chạy **CPU thuần** (đồng bộ). Nếu với DAG lớn mỗi lần tính chiếm vài mili-giây trở lên, đo ảnh hưởng lên spike test; nếu cần, đẩy sang `run_in_executor` hoặc giảm công việc bằng cache.

### 5.4 An toàn & ổn định
- [ ] Phối hợp **M4** (rà OWASP): kiểm tra `course_id` hợp lệ (số nguyên dương), phân quyền (sinh viên chỉ hỏi cho mình), và **rate-limit** cho `check`/`explain` (tránh bị dùng để dò dữ liệu/quá tải).
- [ ] Giới hạn kích thước kết quả explain (số môn thiếu tối đa hợp lý) để không trả phản hồi khổng lồ.

### 5.5 Đo lại và so sánh
- [ ] Chạy lại benchmark Tuần 4: bảng **trước/sau** (thời gian, số truy vấn, tỷ lệ cache hit); gửi M5 để đưa vào báo cáo tải.
- [ ] Chạy lại spike test cùng M5 để xem phần tiên quyết còn là điểm nghẽn không.

### Sản phẩm bàn giao cuối tuần
- Phiên bản đã tối ưu + test đếm truy vấn + số liệu trước/sau + tỷ lệ cache hit.

### Tiêu chí hoàn thành
- Cache trúng → không truy vấn DB; cache trượt → số truy vấn cố định, không tăng theo kích cỡ DAG.
- Có bảng trước/sau thuyết phục, dùng được trong báo cáo.
- Engine vẫn khớp oracle 100% sau khi tối ưu (chạy lại bộ đối chứng).

### Phối hợp
- **M5:** kịch bản Locust, báo cáo trước/sau; **M4:** rà bảo mật, rate-limit; **M3:** kiểm tra `/enroll` không chậm hơn do tiên quyết.

---

## Tuần 6 (Tuần 8 kế hoạch) — Chốt test nghiệm thu, đóng băng

**Mục tiêu:** Bộ ca nghiệm thu đạt **100%**; không thêm tính năng mới (tiêu chí nghiệm thu Mục 8 kế hoạch).

### 6.1 Bộ ca nghiệm thu (làm chung với M5)
Dựng trên một DAG mẫu **trong bộ nhớ** (không phụ thuộc seed). Quy ước ký hiệu: "X cần Y" nghĩa là X có Y là tiên quyết; `OR g1 {…}` là nhóm "hoặc" số 1.

**Đồ thị mẫu:**
- `A1, A2, A3`: không có tiên quyết.
- `B1` cần `A1`; `B2` cần `A1`.
- `C1` cần `B1` (chuỗi A1 → B1 → C1).
- `D1` cần `B1` và `B2` (kim cương: cùng dựa vào A1).
- `E1` cần `OR g1 {A2, A3}`.
- `F1` cần `C1` và `OR g1 {A2, A3}`.
- `G1` cần `OR g1 {A2, A3}` và `OR g2 {B1, B2}` (hai nhóm "hoặc").
- `H1` cần `OR g1 {C1, E1}`.

| # | Đã học | Môn xét | Kết quả mong đợi |
|---|---|---|---|
| 1 | — | `A1` | Đủ điều kiện (không có tiên quyết) |
| 2 | — | `B1` | Không đủ; thiếu `A1` |
| 3 | `A1` | `B1` | Đủ |
| 4 | — | `C1` | Không đủ; thiếu `B1` và `A1` (bắc cầu) |
| 5 | `A1` | `C1` | Không đủ; thiếu `B1` |
| 6 | `B1` | `C1` | Đủ *(phụ thuộc điểm 1; nếu chọn nghiêm ngặt: không đủ, thiếu `A1`)* |
| 7 | `A1` | `D1` | Không đủ; thiếu `B1`, `B2` |
| 8 | — | `D1` | Không đủ; thiếu `B1`, `B2`, `A1` — **`A1` chỉ xuất hiện một lần** |
| 9 | `A1, B1, B2` | `D1` | Đủ |
| 10 | — | `E1` | Không đủ; nhóm "hoặc" 1 chưa thỏa, lựa chọn `A2`, `A3` |
| 11 | `A3` | `E1` | Đủ |
| 12 | `A2, A3` | `E1` | Đủ (thỏa cả hai vẫn đủ) |
| 13 | `A2` | `F1` | Không đủ; thiếu `C1`, `B1`, `A1` (nhóm OR đã thỏa) |
| 14 | `A1, B1, C1` | `F1` | Không đủ; nhóm OR 1 chưa thỏa |
| 15 | `A1, B1, C1, A2` | `F1` | Đủ |
| 16 | `A2` | `G1` | Không đủ; nhóm OR 2 chưa thỏa (`B1`, `B2` đều chưa học được ngay vì cần `A1`) |
| 17 | `A2, B2` | `G1` | Đủ (hai nhóm OR đều thỏa) |
| 18 | `B1` | `G1` | Không đủ; nhóm OR 1 chưa thỏa |
| 19 | `C1` | `H1` | Đủ |
| 20 | `E1` | `H1` | Đủ |
| 21 | — | môn không tồn tại | `404 NOT_FOUND` |

**Ca chu trình (đối với thao tác thêm cạnh):**
| # | Thao tác thêm | Kết quả |
|---|---|---|
| C1 | `A1` cần `B1` | Từ chối (vòng `A1 → B1 → A1`) |
| C2 | `A1` cần `C1` | Từ chối (vòng 3: `A1 → C1 → B1 → A1`) |
| C3 | `B1` cần `B1` | Từ chối (tự trỏ) |
| C4 | `D1` cần `A2` | Chấp nhận |
| C5 | `C1` cần `A1` (dư thừa nhưng không tạo vòng) | Chấp nhận |

- [ ] Hai bạn (M2, M5) **rà chéo từng ca** (đây chính là "pairing review M2×M5" nêu ở phần rủi ro của kế hoạch); bổ sung ca khó từ seed của M4 (độ sâu lớn, nhiều nhóm OR).
- [ ] Tất cả chạy trong CI; **thất bại thì chặn merge**.

### 6.2 Kiểm thử hợp đồng
- [ ] Test khẳng định phản hồi `check`/`explain` **khớp schema OpenAPI** đã đóng băng (không lệch tên trường, kiểu dữ liệu).
- [ ] Test có xác thực thật (token từ M4): sinh viên hỏi hộ người khác → `403`; chưa đăng nhập → `401`.

### 6.3 Đóng băng và dọn dẹp
- [ ] Chỉ sửa lỗi, không thêm tính năng. `ruff` sạch; hàm công khai có type hint; **không còn `print`**; không mật khẩu/`.env` trong commit.
- [ ] Rà comment: thuật toán duyệt, chu trình, memoization, invalidation đều có giải thích rõ.
- [ ] Chạy từ máy sạch: `docker compose up` → `alembic upgrade head` → `python -m app.seed` → `check`/`explain` đúng trên dữ liệu seed (và `assert_acyclic` của seed đạt).
- [ ] Hoàn thiện `docs/prerequisite-engine.md`: thuật toán, độ phức tạp, quyết định bắc cầu, bảng invalidation, số liệu benchmark, cách chạy test.
- [ ] Hỗ trợ M1 chạy E2E smoke: dữ liệu demo phải có kịch bản bắc cầu và nhóm "hoặc" cho giao diện giải thích; sửa nhanh lỗi nếu có.

### Sản phẩm bàn giao cuối tuần
- Bộ nghiệm thu 100% xanh trong CI; tài liệu engine hoàn chỉnh; bản đã đóng băng.

### Tiêu chí hoàn thành
- Engine đúng 100% trên toàn bộ bộ ca (kể cả bắc cầu và nhóm "hoặc") — tiêu chí nghiệm thu thứ nhất của kế hoạch.
- Không còn lỗi mức nghiêm trọng đang mở thuộc phần tiên quyết.

### Phối hợp
- **M5:** pairing review, CI xanh; **M1:** E2E; **M4:** seed demo chốt; **M3:** test tích hợp `/enroll`.

---

## Tuần 7 (Tuần 9 kế hoạch) — Bảo vệ: slide engine, demo, trả lời câu hỏi

**Mục tiêu:** Thuyết minh rõ ràng, tự tin phần engine; demo chạy trơn tru.

### 7.1 Slide phần engine (gợi ý cấu trúc)
- [ ] Bài toán và yêu cầu (UR-F-03, SR-F-02).
- [ ] Mô hình hóa bằng DAG: cạnh, AND, nhóm OR (có hình minh họa).
- [ ] Thuật toán kiểm tra: duyệt + memoization + topological sort; độ phức tạp O(V + E).
- [ ] Bắc cầu và quyết định ngữ nghĩa; hình ví dụ A → B → C.
- [ ] Explain: đường đi, `suggested_order`, `can_take_now`.
- [ ] Chặn chu trình khi nhập dữ liệu.
- [ ] Cache Redis: khóa, TTL, bảng invalidation, hành vi khi Redis lỗi.
- [ ] Số liệu benchmark và bảng trước/sau (có biểu đồ).
- [ ] Chiến lược kiểm thử: bộ ca nghiệm thu, đối chứng với oracle, test đếm truy vấn.

### 7.2 Kịch bản demo (khoảng 3–4 phút)
- [ ] Trên Swagger `/docs` hoặc giao diện của M1: (1) sinh viên đủ điều kiện; (2) thiếu tiên quyết bắc cầu kèm đường đi; (3) môn có nhóm "hoặc"; (4) admin thử thêm cạnh gây vòng → bị từ chối kèm đường đi; (5) gọi lại lần hai cho thấy cache hit trong log.
- [ ] Phương án dự phòng: ảnh chụp/video sẵn nếu mạng hoặc máy lỗi; tài khoản và dữ liệu demo cố định từ M4.
- [ ] Diễn tập cùng cả nhóm ít nhất 2 lần.

### 7.3 Chuẩn bị trả lời câu hỏi
- [ ] Vì sao dùng DAG? Làm sao phát hiện chu trình và vì sao phải chặn từ lúc nhập?
- [ ] Nhóm "hoặc" được lưu và xử lý thế nào? Bắc cầu hiểu ra sao và vì sao chọn cách đó?
- [ ] Độ phức tạp là gì; điều gì xảy ra với lưới kim cương nếu không nhớ kết quả?
- [ ] Cache khóa theo gì, hết hạn thế nào; khi admin sửa DAG hay dữ liệu đã học đổi thì xử lý ra sao?
- [ ] Redis sập thì sao? Vì sao `check` không bị lệch với `/enroll`?
- [ ] Làm sao chứng minh "đúng 100%"? (bộ nghiệm thu + oracle)

### 7.4 Chốt
- [ ] Nộp tài liệu engine vào báo cáo tổng hợp do M5 thu thập; chạy thử lần cuối trên máy dùng để demo.

### Sản phẩm bàn giao
- Slide phần engine, kịch bản demo + bản dự phòng, tài liệu engine.

---

## 8. Ánh xạ yêu cầu → công việc của M2

| Yêu cầu | Nội dung | Làm ở |
|---|---|---|
| UR-F-03 | Kiểm tra đủ điều kiện, biết thiếu môn nào (bắc cầu, "hoặc") | Tuần 1–2 |
| SR-F-02 | DAG, đúng 100% với tập kiểm thử chuẩn, gồm bắc cầu và OR-group | Tuần 1–2, 6 |
| SR-F-03 | `GET /prerequisites/check`, `POST /prerequisites/explain` trả môn thiếu kèm đường suy diễn | Tuần 1–2 |
| UR-NF-02 | Lý do thiếu được diễn giải dễ hiểu (dữ liệu cho M1) | Tuần 2–3 |
| SR-NF-02 | Mã nguồn dễ kiểm thử độc lập (lõi thuần, tách DB) | Tuần 1 |
| SR-NF-03 | OpenAPI đóng băng; contract test | Tuần 2, 6 |
| SR-NF-06 | Cache Redis `(student_id, course_id)` + invalidation | Tuần 3, 5 |
| SR-NF-05 (một phần) | Phần tiên quyết không là điểm nghẽn khi tải | Tuần 4–5 |
| SR-F-04 (một phần) | Cung cấp `check_eligibility` cho `/enroll` của M3 | Tuần 1, 3 |

---

## 9. Những điểm cần chốt với nhóm (phát hiện khi đối chiếu hai tài liệu)

Nên đưa ra trao đổi **ngay trong Tuần 1**:

1. **Ngữ nghĩa "bắc cầu":** hiểu theo (a) *đã học nghĩa là đã đủ* hay (b) *mọi tổ tiên đều phải có*? Đề xuất (a). Ảnh hưởng ca #6 trong bảng nghiệm thu và test của M5. (M2, M5, cả nhóm)
2. **Phương thức explain:** bảng Mục 5 kế hoạch ghi `GET /prerequisites/explain`, nhưng Mục 4.2 và quy ước ghi `POST`. Đề xuất theo quy ước (`POST`, body `course_id`); cần thông báo M1.
3. **Schema JSON explain:** đã có bản đề xuất ở Mục 1.1(d); cần M1 duyệt và đưa vào OpenAPI. (Hợp đồng đã "đóng băng Tuần 2" nhưng phần này chưa có — cần xử lý như một thay đổi hợp đồng có thông báo.)
4. **Mã lỗi mới cho chu trình:** bảng mã lỗi chưa có. Đề xuất thêm `PREREQ_CYCLE` (422) kèm `cycle_path: ["INT101","CS201","INT101"]`; cập nhật bảng Mục 5 quy ước; báo M1 (hiển thị) và M4 (admin API).
5. **Khóa Redis mới:** Mục 7 quy ước chỉ có hai khóa. Đề xuất bổ sung `prereqgraph:v1` (đồ thị, **không** dùng tiền tố `prereq:` để không bị xóa nhầm) và `metrics:prereq:hit|miss` (đếm cache).
6. **Ai viết `core/redis.py`?** M2, M3 hay M5 — tránh viết trùng; M3 cũng cần cho lock.
7. **Ai gọi invalidation khi `completed_courses` thay đổi?** Hiện chưa có API sửa `completed_courses`; chỉ có seed/import — cần M4 xác nhận nơi gắn lời gọi.
8. **`check` trả `200` với `eligible=false` hay `422`?** Đề xuất `200` (đó là kết quả hợp lệ), còn `PREREQ_NOT_MET` 422 chỉ khi `/enroll` bị từ chối.
9. **Môn đã học xong có được đăng ký lại không?** (M3 quyết định.) Nếu cần, `check` có thể trả thêm `already_completed`.
10. **Tham số `check`:** đề xuất dùng `course_id` (không phải `offering_id`, vì tiên quyết gắn với môn); M1 lấy `course_id` từ lớp đang xem.
11. **Điểm đạt tối thiểu:** `completed_courses` chỉ lưu môn đã đạt nên engine không xét điểm; xác nhận lại để không ai kỳ vọng ngưỡng điểm.
12. **Thư viện test:** có thêm `hypothesis` vào `requirements.txt` không? Nếu không, dùng vòng lặp ngẫu nhiên có hạt giống cố định.

---

## 10. Rủi ro riêng của M2 và cách giảm thiểu

| Rủi ro | Biện pháp |
|---|---|
| Engine sai với DAG phức tạp (OR, kim cương, chu trình) | Bảng ca nghiệm thu từ Tuần 1; đối chiếu với oracle ngẫu nhiên (Tuần 4); pairing review M2×M5 |
| Hiểu khác nhau về "bắc cầu" giữa các thành viên | Chốt và ghi vào tài liệu ngay Tuần 1 (Mục 1.1, Mục 9 điểm 1) |
| Cache trả kết quả cũ sau khi dữ liệu đổi | Bảng invalidation, test "đổi dữ liệu → kết quả đổi ngay"; TTL làm lưới an toàn; xác nhận chỗ gọi với M4 |
| Bùng nổ thời gian trên DAG kim cương/sâu | Memoization, duyệt bằng vòng lặp, một đường đi cho mỗi môn thiếu; benchmark Tuần 4 |
| Lệch hợp đồng với M1/M3 | Gửi schema nháp trong 2 ngày đầu; contract test; xử lý lệch trong ngày |
| M4 chưa có models/seed khi M2 cần | Lõi engine thuần, không phụ thuộc DB; kiểm thử bằng DAG trong bộ nhớ |
| Chậm tiến độ | Cặp dự phòng chéo **M2↔M3** (M3 hiểu `check_eligibility` để hỗ trợ), báo sớm ở buổi review 2 tuần/lần; nếu thiếu thời gian, cắt `can_take_now` và `suggested_order` trước (không cắt phần đúng-sai) |
