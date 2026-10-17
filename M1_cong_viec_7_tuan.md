# M1 — Frontend Web Developer: Công việc chi tiết 7 tuần coding

**Đề tài:** Hệ thống Đăng ký Học phần & Kiểm tra Điều kiện Tiên quyết
**Vai trò:** M1 — SPA React 18 + TypeScript + TailwindCSS (Vite)
**Căn cứ:** *Báo cáo kế hoạch dự án* (Mục 4.1, 5, 6) và *Quy ước chung của nhóm*.

> **Cách đánh số tuần.** Kế hoạch gốc có 9 tuần; Tuần 1–2 là thiết kế (kiến trúc, đóng băng hợp đồng API), nên **7 tuần coding còn lại tương ứng Tuần 3–9 của kế hoạch**. Vì việc "dựng khung dự án + MSW" ở Tuần 1 gốc chưa làm, nó được **gộp vào Tuần 1 coding** bên dưới. Việc "Trang quản trị" có trong Mục 4.1 nhưng không nằm trong bảng 9 tuần, nên được xếp vào Tuần 4–5.

---

## 0. Tổng quan 7 tuần

| Tuần coding | Tuần kế hoạch | Trọng tâm | Sản phẩm chính |
|---|---|---|---|
| 1 | 3 | Khung dự án, MSW, đăng nhập, **tra cứu học phần** | Trang tra cứu chạy trên mock |
| 2 | 4 | **Lưới thời khóa biểu** + tô xung đột thời gian thực | Timetable grid + hàm phát hiện trùng lịch (có test) |
| 3 | 5 | **Chuyển sang API thật**, luồng đăng ký + giải thích tiên quyết | Đăng ký/hủy chạy end-to-end với backend |
| 4 | 6 | **Waitlist UI**, dashboard tín chỉ, bắt đầu trang quản trị | Waitlist + thanh tín chỉ + admin (học phần) |
| 5 | 7 | Hoàn thiện admin (DAG), **sửa UX theo test tải**, tối ưu hiệu năng | Admin đầy đủ, UI chịu được spike |
| 6 | 8 | **Đóng băng tính năng**, E2E smoke cùng M5, bản build production | Bộ E2E xanh, build chạy qua Nginx |
| 7 | 9 | **Bảo vệ**: demo UI, slide, diễn tập | Kịch bản demo + slide phần FE |

**Việc lặp lại mỗi tuần (không ghi lại ở từng tuần):**
- Đầu mỗi buổi làm: `git pull` từ `main`; làm trên nhánh riêng dạng `an-timetable` (`ten-tinhnang`).
- Commit nhỏ, mô tả rõ (`Thêm lưới thời khóa biểu`, `Sửa lỗi trùng lịch`).
- Mỗi PR: một bạn khác đọc và chạy thử rồi mới merge. **Vòng review: M1 xem M2, M5 xem M1.**
- Trước khi gộp, chạy checklist Mục 8 quy ước (Prettier/ESLint, không `console.log`, `.env.example` cập nhật, chạy được bằng `docker compose up`).
- Tham dự buổi review 2 tuần/lần do M5 tổ chức; báo tiến độ lên bảng của M5.

---

## 1. Quy ước M1 phải bám theo (tóm tắt để tra nhanh)

**Cấu trúc `frontend/src/`**
```
api/          # MỌI lời gọi backend nằm ở đây (không fetch rải rác trong component)
features/     # courses, timetable, enroll, waitlist, admin
components/   # thành phần dùng chung
pages/ hooks/ types/ mocks/
```

**Quy tắc code:** component/file `PascalCase`; biến/hàm `camelCase`; hook bắt đầu `use`; TypeScript `strict`, hạn chế `any`; kiểu dữ liệu API đặt trong `src/types/`; JSON từ backend là `snake_case` → **chuyển sang `camelCase` ở đúng một chỗ trong `src/api/`**; ESLint + Prettier (format on save); thời gian truyền/lưu UTC, ISO 8601.

**API:** gốc `/api/v1` (biến `VITE_API_BASE_URL`); header `Authorization: Bearer <access_token>`; danh sách phân trang `?page=1&page_size=20` (tối đa 100) trả `{ items, total, page, page_size }`.

**Lịch học (`schedule`):** danh sách buổi `{ "day": 2, "start": "07:00", "end": "09:30" }`, `day` từ 1 (Thứ Hai) đến 7 (Chủ nhật), giờ `HH:MM`. Học kỳ dạng `2026-1`.

**Mã lỗi frontend phải xử lý (đặt trong MỘT file map `code → thông báo tiếng Việt`):**

| code | HTTP | Cách UI xử lý |
|---|---|---|
| `UNAUTHENTICATED` | 401 | Chuyển về đăng nhập, nhớ lại trang đang xem |
| `TOKEN_EXPIRED` | 401 | Âm thầm dùng refresh token lấy token mới rồi gọi lại |
| `FORBIDDEN` | 403 | Thông báo không đủ quyền; ẩn chức năng admin với sinh viên |
| `NOT_FOUND` | 404 | Thông báo/trang không tìm thấy |
| `PREREQ_NOT_MET` | 422 | Mở khung giải thích môn còn thiếu (`missing_courses`) |
| `CREDIT_LIMIT_EXCEEDED` | 422 | Báo vượt tín chỉ, chỉ vào thanh tín chỉ |
| `SCHEDULE_CONFLICT` | 409 | Báo trùng lịch, tô lớp bị trùng trên lưới |
| `ALREADY_ENROLLED` | 409 | Báo đã đăng ký lớp này |
| `CONCURRENT_UPDATE` | 409 | Tự thử lại 1 lần (backoff ngắn), nếu vẫn lỗi mới báo người dùng |

Đăng ký thành công: `201`. Lớp đầy và được đưa vào hàng chờ: `200` với `"status": "WAITLISTED"`. Không bao giờ hiển thị lỗi kỹ thuật thô.

---

## Tuần 1 (Tuần 3 kế hoạch) — Khung dự án, mock API, tra cứu học phần

**Mục tiêu:** Có SPA chạy được hoàn toàn trên dữ liệu giả, đúng hợp đồng API; màn hình tra cứu dùng được.

### 1.1 Dựng khung dự án
- [ ] Khởi tạo Vite + React 18 + TypeScript (bật `strict`) + TailwindCSS trong `frontend/`.
- [ ] Cấu hình ESLint + Prettier, bật format on save (VS Code), thêm script `lint`, `format`.
- [ ] Tạo cấu trúc thư mục đúng quy ước (`api/ features/ components/ pages/ hooks/ types/ mocks/`).
- [ ] Cài router (React Router): `/login`, `/courses`, `/timetable`, `/waitlist`, `/admin/*`, `*` (404).
- [ ] Layout chung: thanh điều hướng, chỗ hiển thị tên người dùng, nút đăng xuất, vùng toast.
- [ ] Phối hợp **M5**: bảo đảm service `web` (Vite, cổng 5173) chạy được trong `docker compose up`, truy cập qua Nginx `http://localhost:8080`. Nếu compose chưa sẵn sàng, tạm dùng `npm run dev`.
- [ ] Thêm `VITE_API_BASE_URL=/api/v1` vào `.env.example` (nếu chưa có).

### 1.2 Lớp `src/api/` và `src/types/`
- [ ] `types/`: `Course`, `CourseOffering`, `ScheduleSlot`, `Enrollment`, `WaitlistEntry`, `User`/`Role`, `Paginated<T>`, `ApiError` (`code`, `message`, `missing_courses?`).
- [ ] `api/http.ts`: hàm gọi chung — gắn `Authorization`, đọc `VITE_API_BASE_URL`, parse lỗi về `ApiError`, **chuyển `snake_case` → `camelCase` tại đây (và ngược lại khi gửi đi)**.
- [ ] Các hàm theo từng nhóm: `auth.ts`, `courses.ts`, `prerequisites.ts`, `enroll.ts`, `waitlist.ts`, `timetable.ts`, `admin.ts` (khai báo trước, nối mock).
- [ ] File `errorMessages.ts`: bảng `code → thông báo tiếng Việt` theo Mục 1.

### 1.3 Mock API bằng MSW (`src/mocks/`)
- [ ] Bật MSW ở chế độ dev qua biến `VITE_USE_MOCK=true`; **tuyệt đối không đưa MSW vào bản build production**.
- [ ] Handler cho `POST /auth/login`, `POST /auth/refresh`, `GET /courses` (lọc + phân trang), `GET /prerequisites/check`, `POST /prerequisites/explain`, `GET /timetable`, `POST /enroll`, `DELETE /enroll/{id}`, `GET/POST /waitlist`.
- [ ] Bộ dữ liệu giả ~30–50 học phần **có đủ các ca khó**: tiên quyết bắc cầu, nhóm "hoặc", lớp sắp đầy, lớp đã đầy, hai lớp trùng lịch, lớp có nhiều buổi/tuần.
- [ ] Mock có thể trả đủ **9 mã lỗi** (ví dụ qua header/giá trị đặc biệt) để thử UI mà không cần backend.
- [ ] Định dạng phản hồi mock **phải khớp đúng** Mục 5 quy ước; chỗ nào hợp đồng chưa rõ thì ghi vào danh sách "cần chốt" (Mục 9).

### 1.4 Đăng nhập tối thiểu & phân quyền giao diện
- [ ] Trang đăng nhập (email + mật khẩu), lưu `access_token` và `refresh_token` (nêu rõ lựa chọn nơi lưu với nhóm — xem Mục 9).
- [ ] Context/hook `useAuth` (người dùng hiện tại, vai trò, đăng nhập/đăng xuất).
- [ ] Route guard: chưa đăng nhập → `/login`; **tài khoản sinh viên không thấy và không vào được `/admin/*`** (UR-NF-04).

### 1.5 Màn hình tra cứu học phần
- [ ] Bộ lọc đúng **5 trường**: từ khóa, mã lớp, tín chỉ, giảng viên, khung giờ (thứ + khoảng giờ) — SR-F-01.
- [ ] Debounce ô gõ (~300 ms); hủy request cũ khi có request mới (`AbortController`).
- [ ] Đồng bộ bộ lọc và trang hiện tại lên URL (`?q=&credits=&page=`), để F5 hoặc chia sẻ link vẫn giữ kết quả.
- [ ] Danh sách kết quả: mã môn, tên, tín chỉ, lớp, giảng viên, lịch học, sĩ số (`enrolled_count/capacity`), tag "Sắp đầy"/"Đã đầy".
- [ ] Phân trang theo `page`/`page_size` (mặc định 20, tối đa 100).
- [ ] Đủ ba trạng thái: đang tải (skeleton), rỗng ("Không tìm thấy học phần phù hợp"), lỗi (thông báo thân thiện + nút thử lại).

### Sản phẩm bàn giao cuối tuần
- Repo chạy `docker compose up` (hoặc `npm run dev`) mở được ứng dụng trên mock.
- PR đã merge: khung dự án, lớp `api/`, MSW, đăng nhập mock, trang tra cứu.

### Tiêu chí hoàn thành
- Lọc đồng thời cả 5 trường cho kết quả đúng trên dữ liệu giả; đổi bộ lọc không cần tải lại trang (UR-NF-07).
- Không có `any` trong `types/` và `api/`; `npm run lint` sạch.
- Một thành viên khác đã chạy thử (M5 review).

### Phối hợp
- **M3** (owner `/courses/search`): chốt tên endpoint và tên tham số lọc (xem Mục 9).
- **M5**: Docker Compose cho service `web`, CI chạy lint/build cho frontend.

---

## Tuần 2 (Tuần 4 kế hoạch) — Thời khóa biểu dạng lưới + tô xung đột thời gian thực

**Mục tiêu:** Sinh viên nhìn ngay môn nào trùng lịch, **không cần tải lại trang** (UR-F-02, UR-NF-06, SR-F-07).

### 2.1 Hàm tiện ích lịch (`features/timetable/` hoặc `utils/`)
- [ ] `parseTime("07:00") → số phút` và ngược lại.
- [ ] `slotsOverlap(a, b)`: cùng `day` và `a.start < b.end && b.start < a.end`. **Hai buổi liền nhau (kết thúc 09:30, bắt đầu 09:30) KHÔNG tính là trùng.**
- [ ] `findConflicts(candidateOffering, currentOfferings)`: trả về danh sách lớp bị trùng và buổi bị trùng (một lớp có thể có nhiều buổi/tuần).
- [ ] Thêm Vitest (báo nhóm/M5 để đưa vào CI) và viết unit test: trùng hẳn, trùng một phần, liền kề, khác ngày, nhiều buổi, lớp trùng chính nó. **Mục tiêu: 0 dương tính giả, 0 âm tính giả** trên bộ test (tiêu chí nghiệm thu Mục 8).

### 2.2 Component lưới tuần `TimetableGrid`
- [ ] Cột: Thứ Hai → Chủ nhật (`day` 1–7); hàng: giờ (ví dụ 07:00–21:00, khoảng giờ lấy từ cấu hình, không viết cứng rải rác).
- [ ] Mỗi buổi học là một block định vị theo giờ–thứ (tính vị trí/chiều cao từ phút bắt đầu/kết thúc), hiển thị mã môn, lớp, phòng, giờ.
- [ ] Màu theo môn (palette cố định, ánh xạ ổn định theo `course_id`) — UR-NF-01.
- [ ] **Xung đột:** viền đỏ + biểu tượng cảnh báo + tooltip "Trùng với <môn>". Không chỉ dựa vào màu (để người khó phân biệt màu vẫn nhận ra).
- [ ] Khi hai block chồng nhau trên cùng ô, hiển thị cạnh nhau (chia đôi chiều ngang) thay vì che mất nhau.
- [ ] Cuộn ngang trong khung riêng trên màn hình nhỏ.

### 2.3 Trang thời khóa biểu và "xem trước"
- [ ] Chọn học kỳ (`2026-1`) → gọi `GET /timetable` (mock) lấy các lớp đang đăng ký.
- [ ] Từ trang tra cứu thêm nút **"Xem trước trên TKB"**: lớp được thêm tạm vào lưới dạng block mờ; nếu trùng thì tô xung đột ngay (tính ở client bằng `findConflicts`).
- [ ] Danh sách bên cạnh lưới: các lớp đang đăng ký + lớp xem trước, có nút bỏ xem trước.
- [ ] Mã màu/chú giải (legend) cho "đã đăng ký", "xem trước", "xung đột".

### 2.4 Chất lượng
- [ ] Trạng thái rỗng ("Chưa đăng ký lớp nào trong kỳ này"), đang tải, lỗi.
- [ ] Kiểm tra bằng bộ dữ liệu mock có sẵn hai lớp trùng lịch, lớp nhiều buổi.

### Sản phẩm bàn giao cuối tuần
- Trang TKB dạng lưới + chức năng xem trước + highlight xung đột.
- Bộ unit test lịch (xanh), PR đã được review.

### Tiêu chí hoàn thành
- Thêm một lớp trùng giờ → cảnh báo hiện **tức thì**, không gọi server.
- Bộ test lịch: 0 dương tính/âm tính giả.

### Phối hợp
- **M3**: chốt có **"quy tắc nghỉ giữa hai ca"** hay không (Mục 4.3 kế hoạch nhắc tới). Nếu có, `findConflicts` ở frontend phải **khớp đúng** quy tắc của server. Server là nơi quyết định cuối cùng (`SCHEDULE_CONFLICT` 409).
- **M3**: chốt `GET /timetable` (chủ sở hữu ghi là M1+M3) trả dữ liệu gì (xem Mục 9).
- **M5**: đưa Vitest vào CI.

---

## Tuần 3 (Tuần 5 kế hoạch) — Chuyển sang API thật, luồng đăng ký, giải thích tiên quyết

**Mục tiêu:** Đăng ký/hủy lớp chạy end-to-end với backend thật; lỗi tiên quyết được giải thích bằng ngôn ngữ dễ hiểu (UR-F-03, UR-NF-02, UR-F-04).

### 3.1 Chuyển từ mock sang API thật
- [ ] Đặt `VITE_USE_MOCK=false` làm mặc định cho môi trường tích hợp; vẫn giữ MSW cho khi phát triển độc lập.
- [ ] Rà từng endpoint: so khớp kiểu dữ liệu thực tế với `types/`; ghi mọi chỗ lệch hợp đồng vào danh sách và báo owner (M2/M3/M4) ngay trong ngày.
- [ ] Nối đăng nhập thật (`/auth/login`, `/auth/refresh`) với M4.
- [ ] Kiểm tra CORS (`CORS_ORIGINS` gồm `http://localhost:5173` và `http://localhost:8080`) hoạt động cả khi vào qua Nginx.

### 3.2 Xử lý phiên & token (UR-NF-05)
- [ ] Khi gặp `TOKEN_EXPIRED`: tự gọi `/auth/refresh` **một lần duy nhất** (nhiều request cùng hết hạn thì chỉ refresh một lần, các request còn lại chờ rồi chạy lại).
- [ ] Refresh thất bại → đăng xuất nhẹ nhàng, quay về `/login` kèm thông báo "Phiên đã hết hạn", giữ lại trang đang làm dở để quay lại.
- [ ] Không bị "văng" giữa chừng khi đang điền/duyệt (không reload toàn trang).

### 3.3 Luồng đăng ký lớp
- [ ] Trong tra cứu/chi tiết lớp, nút **"Đăng ký"** mở khung xác nhận.
- [ ] Bước 1: gọi `GET /prerequisites/check`. Nếu chưa đủ → gọi explain và **hiển thị nguyên nhân bằng ngôn ngữ thường**, ví dụ: *"Bạn còn thiếu INT131 — môn tiên quyết (gián tiếp) của CS441"*; với nhóm "hoặc": *"Cần hoàn thành ít nhất 1 trong các môn: A, B"*. **Không dùng thuật ngữ đồ thị** (DAG, node, cạnh…).
- [ ] Hiển thị đường dẫn suy diễn dạng chuỗi bước dễ đọc (ví dụ A → B → C), không phải cấu trúc kỹ thuật.
- [ ] Bước 2 (đủ điều kiện): gọi `POST /enroll` kèm **idempotency key** (sinh một UUID cho mỗi lần thao tác; nếu thử lại cùng thao tác thì dùng lại key đó) để chống double-submit.
- [ ] Khóa nút trong lúc đang gửi; không cho bấm lần hai.
- [ ] Xử lý kết quả: `201` → toast thành công + cập nhật TKB/tín chỉ; `200 WAITLISTED` → thông báo "Lớp đã đầy, bạn đã được đưa vào danh sách chờ" (chi tiết hàng chờ làm tuần sau); lỗi → dùng map mã lỗi ở Mục 1 (`CREDIT_LIMIT_EXCEEDED`, `SCHEDULE_CONFLICT`, `ALREADY_ENROLLED`, `CONCURRENT_UPDATE` tự thử lại 1 lần).
- [ ] Hủy đăng ký: `DELETE /enroll/{id}` có hộp xác nhận; sau khi hủy cập nhật lại TKB và số tín chỉ.

### 3.4 Kiểm thử thủ công cùng backend
- [ ] Chạy thử đủ các ca: thiếu tiên quyết (bắc cầu, nhóm "hoặc"), đủ điều kiện, trùng lịch, vượt tín chỉ, đăng ký trùng, hủy đăng ký.
- [ ] Ghi lỗi tìm được thành issue, gán đúng owner.

### Sản phẩm bàn giao cuối tuần
- Đăng nhập → tra cứu → đăng ký → xem TKB → hủy, chạy trên backend thật.
- Danh sách các điểm lệch hợp đồng đã được xử lý hoặc có owner nhận.

### Tiêu chí hoàn thành
- Mọi mã lỗi ở Mục 1 hiện thông báo tiếng Việt thân thiện, không lộ lỗi kỹ thuật.
- Bấm đăng ký liên tiếp/nhấp đúp không tạo đăng ký trùng.
- Hết phiên không làm gián đoạn luồng (UR-NF-05).

### Phối hợp
- **M2**: chốt **schema JSON của explain** (danh sách môn thiếu + đường dẫn suy diễn + nhóm "hoặc"), tránh mỗi bên hiểu một kiểu.
- **M3**: ý nghĩa của idempotency key phía server; hành vi khi `200 WAITLISTED`.
- **M4**: cách lưu token, vòng đời refresh token.
- **Cuối tuần:** là mốc tích hợp — dành thời gian gỡ lỗi chung cả nhóm.

---

## Tuần 4 (Tuần 6 kế hoạch) — Waitlist UI, dashboard tín chỉ, bắt đầu trang quản trị

**Mục tiêu:** Hoàn thiện nghiệp vụ phía sinh viên (UR-F-04, UR-F-05, UR-NF-03) và khởi động trang quản trị (UR-F-07).

### 4.1 Giao diện danh sách chờ (waitlist)
- [ ] Với lớp đã đầy: nút đổi thành **"Vào danh sách chờ"** (hoặc xử lý theo hành vi `200 WAITLISTED` của `/enroll` — chốt ở Mục 9).
- [ ] Trang `/waitlist`: danh sách các lớp đang chờ, **vị trí trong hàng** (`position`), thời điểm vào hàng, nút "Rời hàng chờ".
- [ ] Giải thích quy tắc ngay trên giao diện: *"Vào trước, ra trước — khi có người hủy, bạn ở đầu hàng sẽ được tự động đăng ký"* (UR-NF-03).
- [ ] Hiển thị lỗi liên quan hạn mức hàng chờ (tối đa ~20% sĩ số) bằng câu dễ hiểu.
- [ ] Cập nhật khi được đôn: làm mới danh sách theo chu kỳ (ví dụ 30 giây) và khi quay lại tab; khi phát hiện đã được đôn → toast "Bạn đã được đăng ký vào lớp X" và cập nhật TKB + tín chỉ.
- [ ] Ca đặc biệt từ M3: sinh viên được đôn nhưng không đăng ký được (trùng lịch/vượt tín chỉ) → hiển thị lý do rõ ràng, không im lặng.

### 4.2 Dashboard tín chỉ
- [ ] Thanh tiến trình **tín chỉ đã đăng ký / hạn mức kỳ** (`max_credits` của sinh viên, mặc định 25).
- [ ] Đổi màu theo ngưỡng (ví dụ ≥ 90% cảnh báo, đầy = đỏ); kèm chữ số cụ thể (không chỉ dựa vào màu).
- [ ] Khi chọn đăng ký lớp làm vượt hạn mức: **cảnh báo sớm** ở client, nhưng vẫn gửi lên server và xử lý `CREDIT_LIMIT_EXCEEDED` (server quyết định cuối cùng).
- [ ] Hiển thị trên trang TKB và/hoặc đầu trang tra cứu.

### 4.3 Trang quản trị — phần 1: học phần (role admin)
- [ ] Layout riêng `/admin/*`, chỉ admin vào được; sinh viên bị chặn cả ở route lẫn menu (UR-NF-04).
- [ ] Bảng học phần (`/admin/courses`): danh sách phân trang, tìm kiếm, nút thêm/sửa/xóa.
- [ ] Form thêm/sửa học phần (mã, tên, tín chỉ, mô tả) với kiểm tra dữ liệu phía client (tín chỉ 1–10, mã không trùng…) và hiển thị lỗi `422` từ server.
- [ ] Xác nhận trước khi xóa; xử lý lỗi khi học phần đang được tham chiếu.

### 4.4 Chất lượng
- [ ] Bug bash do M5 tổ chức trong tuần này: nhận danh sách lỗi UI, sửa theo mức ưu tiên.
- [ ] Viết thêm test component cho các phần có logic (hiển thị trạng thái waitlist, ngưỡng tín chỉ).

### Sản phẩm bàn giao cuối tuần
- Waitlist UI + dashboard tín chỉ chạy trên backend thật.
- Trang quản trị học phần (thêm/sửa/xóa).

### Tiêu chí hoàn thành
- Vào hàng chờ, xem vị trí, rời hàng chờ, và thấy thông báo khi được đôn đều hoạt động.
- Thanh tín chỉ luôn khớp với tổng tín chỉ các đăng ký `ACTIVE` của kỳ.

### Phối hợp
- **M3**: hành vi đôn tự động, các ca đôn thất bại.
- **M4**: API `/admin/courses`, quyền admin.
- **M5**: kết quả bug bash, spike test lần đầu.

---

## Tuần 5 (Tuần 7 kế hoạch) — Hoàn thiện admin, sửa UX theo test tải, hiệu năng

**Mục tiêu:** Giao diện vẫn mượt và đúng khi hệ thống chịu tải; trang quản trị đầy đủ.

### 5.1 Trang quản trị — phần 2: điều kiện tiên quyết
- [ ] Trang `/admin/prereqs`: chọn một học phần → xem danh sách tiên quyết hiện tại (nhóm `AND` và các nhóm `OR`).
- [ ] Thêm/xóa tiên quyết; chọn loại `AND` hoặc nhóm `OR` (`group_no`); giao diện gom các môn cùng nhóm "hoặc" thành một khối dễ thấy.
- [ ] **Khi server từ chối vì tạo vòng lặp** (A cần B, B cần A): hiển thị thông báo dễ hiểu, chỉ ra các môn liên quan.
- [ ] (Tùy thời gian) xem trước dạng cây tiên quyết của một môn để người quản trị kiểm tra.
- [ ] Chức năng import dữ liệu mẫu (seed) nếu M4 cung cấp endpoint — **cần chốt endpoint** (Mục 9). Nếu không có, ghi rõ là seed chạy bằng lệnh `python -m app.seed`, không làm trên UI.

### 5.2 Sửa UX theo kết quả test tải (từ M5)
- [ ] Đọc báo cáo Locust: những màn hình/hành động nào chậm hoặc lỗi nhiều khi mở đăng ký.
- [ ] Xử lý `429`/rate-limit (M4 làm rate-limiting): hiển thị "Hệ thống đang đông, thử lại sau X giây", tự thử lại theo `Retry-After` nếu có.
- [ ] `CONCURRENT_UPDATE`: thử lại tự động 1 lần với độ trễ ngẫu nhiên nhỏ, sau đó mới báo người dùng.
- [ ] Trạng thái "đang xử lý" rõ ràng khi đăng ký lúc cao điểm; tuyệt đối không cho gửi trùng.
- [ ] Hủy request cũ khi người dùng đổi bộ lọc liên tục; cân nhắc cache phía client (nếu nhóm đồng ý dùng TanStack Query — **cần thống nhất trước khi thêm thư viện**).

### 5.3 Hiệu năng giao diện
- [ ] Tách code theo route (lazy load), đặc biệt khu vực `/admin`.
- [ ] Tránh render lại không cần thiết ở `TimetableGrid` và danh sách kết quả (memo hợp lý, key ổn định).
- [ ] Kiểm tra kích thước bundle; loại thư viện thừa.
- [ ] Đo thời gian phản hồi của tra cứu/lọc (UR-NF-07) và ghi số liệu để đưa vào báo cáo.

### 5.4 Hoàn thiện trải nghiệm
- [ ] Rà toàn bộ chuỗi thông báo: nhất quán giọng văn, không còn lỗi kỹ thuật thô.
- [ ] Hỗ trợ bàn phím và nhãn truy cập (aria) cho form, hộp thoại, lưới TKB.
- [ ] Rà responsive trên màn hình nhỏ.

### Sản phẩm bàn giao cuối tuần
- Trang quản trị đầy đủ (học phần + tiên quyết).
- Bản sửa UX sau test tải; số liệu hiệu năng giao diện.

### Tiêu chí hoàn thành
- Admin thêm được tiên quyết (kể cả nhóm "hoặc") và thấy lỗi vòng lặp dễ hiểu khi nhập sai.
- Dưới spike test, giao diện không treo, không gửi trùng yêu cầu, hiển thị trạng thái rõ ràng.

### Phối hợp
- **M5**: báo cáo spike test, chạy lại test tải sau khi sửa.
- **M4**: `/admin/prereqs`, rate-limit, rà soát bảo mật (OWASP) — kiểm tra phía FE: không lưu dữ liệu nhạy cảm, không nhúng HTML thô từ API (chống XSS).
- **M2**: khi admin sửa DAG, cache tiên quyết (`prereq:*`) bị xóa — kiểm tra UI hiển thị đúng kết quả mới.

---

## Tuần 6 (Tuần 8 kế hoạch) — Đóng băng tính năng, E2E smoke, bản production

**Mục tiêu:** Không thêm tính năng mới; chỉ sửa lỗi và làm cho mọi thứ ổn định để demo.

### 6.1 Kiểm thử E2E cùng M5
- [ ] Chốt công cụ E2E với M5 (ví dụ Playwright) và dữ liệu demo cố định từ M4.
- [ ] Viết kịch bản smoke tối thiểu:
  1. Sinh viên đăng nhập → tra cứu → xem trước trên TKB → thấy cảnh báo trùng lịch.
  2. Đăng ký lớp đủ điều kiện → thành công → TKB và thanh tín chỉ cập nhật.
  3. Đăng ký lớp thiếu tiên quyết → hiện giải thích đúng (bắc cầu và nhóm "hoặc").
  4. Đăng ký lớp đã đầy → vào hàng chờ → hủy lớp ở tài khoản khác → được đôn.
  5. Vượt tín chỉ → báo đúng.
  6. Admin thêm học phần + tiên quyết; sinh viên **không** vào được `/admin`.
  7. Hết phiên/token hết hạn → tự làm mới, không gián đoạn.
- [ ] Đưa smoke test vào CI (M5 cấu hình), đảm bảo xanh.

### 6.2 Build production
- [ ] Build bằng Vite và phục vụ qua Nginx: kiểm tra định tuyến SPA (F5 ở `/timetable` không ra 404), gọi API qua `/api/v1`.
- [ ] Kiểm tra bản build **không chứa MSW**, không còn URL `localhost` viết cứng, không còn `console.log`/`print` thử nghiệm.
- [ ] Chạy được hoàn toàn **không cần internet** (SR-NF-07): font/icon/ảnh đều nằm trong bản build, không gọi CDN ngoài.
- [ ] Chạy thử bằng đúng lệnh `docker compose up` trên một máy sạch (nhờ một bạn khác thử).

### 6.3 Dọn dẹp
- [ ] Sửa các lỗi còn lại từ bug bash và E2E; không thêm tính năng mới.
- [ ] Rà lần cuối: lint/format sạch, không `any` thừa, mọi biến môi trường mới có trong `.env.example`.
- [ ] Cập nhật README phần frontend: cách chạy, cấu trúc thư mục, cách bật/tắt mock, cách chạy test.
- [ ] Chuẩn bị tài khoản demo (sinh viên, admin) và dữ liệu cho từng kịch bản.

### Sản phẩm bàn giao cuối tuần
- E2E smoke xanh trong CI; bản build production chạy qua Nginx.
- README frontend hoàn chỉnh.

### Tiêu chí hoàn thành
- Chạy `docker compose up` là demo được toàn bộ luồng, không lỗi console đáng kể.
- Không còn lỗi mức nghiêm trọng đang mở thuộc phần frontend.

### Phối hợp
- **M5**: E2E, Docker prod profile, CI xanh.
- **M4**: chốt seed demo.
- **M2, M3**: chốt test nghiệm thu — M1 xác nhận UI hiển thị khớp kết quả.

---

## Tuần 7 (Tuần 9 kế hoạch) — Bảo vệ: demo UI, slide, diễn tập

**Mục tiêu:** Mỗi thành viên thuyết minh được phần của mình; phần demo giao diện trơn tru (Mục 8 kế hoạch).

### 7.1 Kịch bản demo (khoảng 5–7 phút)
- [ ] Viết kịch bản từng bước kèm tài khoản và dữ liệu dùng cho mỗi bước, theo thứ tự: tra cứu → TKB và cảnh báo trùng lịch → thiếu tiên quyết (giải thích) → đăng ký thành công → lớp đầy → waitlist và đôn → thanh tín chỉ → trang quản trị.
- [ ] Chuẩn bị **phương án dự phòng**: video quay màn hình hoặc ảnh chụp từng bước, phòng khi mạng/máy lỗi.
- [ ] Diễn tập ít nhất 2 lần cùng cả nhóm; đo thời gian.

### 7.2 Slide phần frontend
- [ ] Nội dung gợi ý: kiến trúc SPA và phân tầng `api/ → features/ → components/`; làm việc song song nhờ mock (MSW) bám hợp đồng API; thuật toán phát hiện trùng lịch và vì sao không có dương/âm tính giả; xử lý lỗi theo mã; xử lý phiên/token; các cải tiến UX sau test tải (kèm số liệu).
- [ ] Mỗi slide có hình chụp thật từ ứng dụng.

### 7.3 Chuẩn bị trả lời câu hỏi
- [ ] Vì sao client vẫn kiểm tra trùng lịch khi server đã kiểm tra? (phản hồi tức thì; server vẫn là nơi quyết định)
- [ ] Làm sao chống double-submit? (khóa nút + idempotency key)
- [ ] Xử lý hết phiên thế nào? (refresh một lần duy nhất, không ngắt luồng)
- [ ] Phần frontend đã phối hợp với backend ra sao? (hợp đồng OpenAPI, mock đúng contract)

### 7.4 Chốt phiên bản
- [ ] Gắn tag phiên bản cuối trên `main`; kiểm tra lần cuối `docker compose up` trên máy dùng để demo.
- [ ] Nộp/ghép tài liệu frontend vào báo cáo tổng hợp do M5 thu thập.

### Sản phẩm bàn giao
- Kịch bản demo + bản dự phòng, slide phần FE, bản `main` đã gắn tag.

---

## 8. Ánh xạ yêu cầu → công việc của M1

| Yêu cầu | Nội dung | Làm ở |
|---|---|---|
| UR-F-01 / SR-F-01 | Tra cứu, lọc theo 5 trường | Tuần 1 |
| UR-F-02 / SR-F-07 | TKB lưới tuần, nhận biết trùng lịch | Tuần 2 |
| UR-F-03 / SR-F-03 | Kiểm tra và giải thích tiên quyết | Tuần 3 |
| UR-F-04 | Đăng ký, vào hàng chờ, được đôn | Tuần 3–4 |
| UR-F-05 | Không vượt tín chỉ tối đa (dashboard + cảnh báo) | Tuần 4 |
| UR-F-06 | Đăng nhập, phân quyền sinh viên/admin trên UI | Tuần 1, 3 |
| UR-F-07 | Quản trị học phần và tiên quyết | Tuần 4–5 |
| UR-NF-01 | Mã màu TKB rõ ràng | Tuần 2 |
| UR-NF-02 | Giải thích tiên quyết dễ hiểu | Tuần 3 |
| UR-NF-03 | Waitlist dễ hiểu (vào trước, ra trước) | Tuần 4 |
| UR-NF-04 | Ẩn/khóa chức năng admin với sinh viên | Tuần 1, 4 |
| UR-NF-05 | Lỗi xác thực/hết phiên mượt | Tuần 3 |
| UR-NF-06 | Cảnh báo trùng lịch tức thì | Tuần 2 |
| UR-NF-07 | Tra cứu/lọc phản hồi nhanh | Tuần 1, 5 |
| SR-NF-07 | Chạy bằng `docker compose up`, không cần internet | Tuần 6 |

---

## 9. Những điểm cần chốt với nhóm (phát hiện khi đối chiếu hai tài liệu)

Nên đưa các mục này ra trao đổi **ngay trong tuần 1** để tránh lệch hợp đồng:

1. **Tên endpoint tra cứu:** kế hoạch ghi `/courses/search`, quy ước ghi `/courses`. Chọn một (chủ sở hữu: M3).
2. **Phương thức explain:** bảng Mục 5 kế hoạch ghi `GET /prerequisites/explain`, nhưng Mục 4.2 và quy ước ghi `POST /prerequisites/explain`. Cần chốt (M2).
3. **Schema JSON của explain:** chưa có định nghĩa — cần M2 chốt cấu trúc (môn thiếu, đường dẫn suy diễn, nhóm "hoặc") trước khi M1 làm giao diện Tuần 3.
4. **`GET /timetable`:** chủ sở hữu ghi M1+M3 nhưng không có trong danh sách endpoint của quy ước; cần chốt dữ liệu trả về (lớp đang đăng ký kèm `schedule`? hay chỉ danh sách đăng ký?).
5. **Đăng ký vào hàng chờ:** quy ước nói `POST /enroll` khi lớp đầy sẽ trả `200` + `WAITLISTED`, trong khi kế hoạch còn có `POST /waitlist` và "nút chuyển sang waitlist". Cần chốt UI sẽ gọi endpoint nào và có hỏi xác nhận trước khi vào hàng chờ không.
6. **Quy tắc nghỉ giữa hai ca:** có hay không, bao nhiêu phút? (ảnh hưởng hàm `findConflicts` ở client).
7. **Nơi lưu token** ở frontend (bộ nhớ, `localStorage`, hay cookie) — thống nhất với M4, lưu ý rủi ro XSS.
8. **Import seed trên giao diện admin:** có endpoint không, hay chỉ chạy bằng lệnh?
9. **Công cụ kiểm thử frontend:** quy ước mới nêu pytest/Locust; cần đồng ý thêm Vitest (unit) và Playwright (E2E), và có thêm TanStack Query hay không.
10. **Idempotency key:** gửi qua header hay trong body của `POST /enroll`?

---

## 10. Rủi ro riêng của M1 và cách giảm thiểu

| Rủi ro | Biện pháp |
|---|---|
| Hợp đồng API lệch giữa mock và backend thật | Mock bám đúng Mục 5; ghi lệch vào danh sách (Mục 9); chuyển API thật từ Tuần 3, không dồn về cuối |
| Logic trùng lịch ở client và server khác nhau | Chốt quy tắc với M3 sớm; server luôn quyết định; test các ca biên (liền kề, nhiều buổi) |
| Trang quản trị bị dồn việc vào cuối | Bắt đầu ở Tuần 4 (học phần), hoàn thiện Tuần 5; nếu thiếu thời gian thì cắt phần xem trước cây tiên quyết/import seed trước |
| Giao diện hỏng khi tải cao | Khóa nút gửi, tự thử lại có kiểm soát, xử lý 429; dùng kết quả Locust của M5 để sửa ở Tuần 5 |
| Chậm tiến độ | Cặp dự phòng chéo **M1↔M4** (M4 hỗ trợ giao diện admin khi cần); báo sớm trong buổi review 2 tuần/lần |
