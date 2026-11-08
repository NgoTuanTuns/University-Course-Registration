# M1 — Week 3: Tích hợp API hiện có và trạng thái chờ backend

## 1. Mục tiêu

Kế thừa Week 1–2. Tích hợp những endpoint đã được xác nhận trong backend nhóm.

## 2. Trạng thái tích hợp theo backend nhóm

Đối chiếu `docs/openapi.json`, `backend/app/main.py`, router và schema trong `University-Course-Registration-main`:

| Chức năng                   | Endpoint                             | Trạng thái trong Week 3                                                            |
| --------------------------- | ------------------------------------ | ---------------------------------------------------------------------------------- |
| Đăng nhập                   | `POST /api/v1/auth/login`            | Tích hợp backend thật                                                              |
| Refresh token               | `POST /api/v1/auth/refresh`          | Tích hợp, dùng single-flight để nhiều request chỉ refresh một lần                  |
| Đăng xuất                   | `POST /api/v1/auth/logout`           | Tích hợp backend thật                                                              |
| Kiểm tra tiên quyết         | `GET /api/v1/prerequisites/check`    | Tích hợp backend thật                                                              |
| Giải thích tiên quyết       | `POST /api/v1/prerequisites/explain` | Tích hợp backend thật theo schema M2                                               |
| Danh mục học phần sinh viên | `GET /api/v1/courses`                | Chưa có; dùng danh mục tĩnh chỉ đọc, bám bộ seed KIT                               |
| Thời khóa biểu              | `GET /api/v1/timetable`              | Chưa có; TKB chỉ hiển thị trạng thái tĩnh/rỗng, lớp xem trước vẫn hoạt động cục bộ |
| Đăng ký                     | `POST /api/v1/enroll`                | Chưa có; không gửi request, không tạo đăng ký giả                                  |
| Hủy đăng ký                 | `DELETE /api/v1/enroll/{id}`         | Chưa có; hiển thị ghi chú chờ M3, không gửi request                                |

Lưu ý: backend có `GET /api/v1/admin/courses` nhưng đây là API quản trị, không thay thế API danh mục dành cho sinh viên. CRUD admin thuộc các tuần 4–5 của kế hoạch M1, không phải mục tiêu Week 3.

## 3. Cách xử lý chức năng chưa có API

- Danh mục 12 lớp KIT được đóng gói trong `src/mocks/data.ts` dưới dạng dữ liệu tĩnh, chỉ dùng để xem và xem trước.
- ID môn học và ID lớp học phần của danh mục này được ánh xạ theo thứ tự KIT trong `backend/app/seed_data.py`. Việc gọi kiểm tra tiên quyết chỉ chính xác khi backend được nạp bộ seed tương ứng (`default` hoặc `minimal`) và giữ nguyên thứ tự seed.
- Nếu backend dùng dữ liệu tự nhập hoặc ID khác, API có thể trả `NOT_FOUND`; giao diện hiển thị rõ rằng dữ liệu tĩnh không khớp DB, không che lỗi.
- Ánh xạ ID môn học của bộ KIT: `INT101=1`, `MAT201=2`, `MAT202=3`, `INT131=4`, `INT221=5`, `INT222=6`, `INT231=7`, `INT321=8`, `INT331=9`, `INT341=10`, `INT451=11`, `INT431=12`. ID lớp học phần KIT theo thứ tự `INT101=1`, `INT131=2`, `INT221=3`, `INT222=4`, `MAT201=5`, `MAT202=6`, `INT231=7`, `INT331=8`, `INT341=9`, `INT321=10`, `INT431=11`, `INT451=12`.
- Khi điều kiện tiên quyết đạt, giao diện thông báo đã đủ điều kiện nhưng không đăng ký vì chưa có `POST /enroll`.
- Khi thiếu điều kiện, frontend gọi explain và hiển thị môn thiếu, trực tiếp/gián tiếp, đường dẫn và nhóm lựa chọn OR.
- Không có nút hủy thực thi, không cập nhật số lượng đăng ký giả và không tuyên bố đã vào waitlist.

## 4. Cách chạy độc lập trên Windows / VS Code

1. Mở VS Code tại thư mục `M1_3`.
2. Mở Terminal:

   ```powershell
   npm install
   npm run dev
   ```

3. Mở `http://localhost:5173`.
4. `.env.development` đặt `VITE_USE_MOCK=false`, vì vậy MSW không chạy. Frontend dùng Vite proxy `/api` đến `http://localhost:8000`.

Nếu backend chưa chạy, trang đăng nhập thật sẽ không thể đăng nhập; đây là hành vi đúng của chế độ tích hợp.

## 5. Chạy cùng backend dự án nhóm

Cần đặt thư mục `M1_3` cạnh hoặc trong môi trường làm việc có thể truy cập repo backend. Tại thư mục gốc dự án nhóm:

```powershell
copy .env.example .env
docker compose up --build -d
docker compose exec api alembic upgrade head
docker compose exec api python -m app.seed
```

Sau đó mở terminal khác tại thư mục `M1_3`:

```powershell
npm install
npm run dev
```

Vite proxy đã cấu hình `/api` → `http://localhost:8000`, vì vậy mở frontend tại `http://localhost:5173`.

### Tài khoản seed backend

| Vai trò   | Email               | Mật khẩu      |
| --------- | ------------------- | ------------- |
| Sinh viên | `sv0001@uni.edu.vn` | `Student@123` |
| Quản trị  | `admin@uni.edu.vn`  | `Admin@123`   |

Chỉ dùng các tài khoản này với backend seed của dự án nhóm.

## 6. Kiểm thử luồng Week 3

1. Đăng nhập bằng `sv0002@uni.edu.vn` để kiểm tra trường hợp thiếu tiên quyết bắc cầu.
2. Tìm `INT431`, mở **Kiểm tra tiên quyết** và xem các môn thiếu cùng đường dẫn suy diễn bắc cầu.
3. Vẫn dùng `sv0002`, tìm `INT341` để xem nhóm OR chưa đạt và các lựa chọn còn thiếu.
4. Đăng xuất, đăng nhập bằng `sv0001@uni.edu.vn`; tìm `INT341` để kiểm tra trường hợp đủ điều kiện nhờ đã hoàn thành INT231 và một lựa chọn OR (MAT201).
5. Nếu thiếu điều kiện, kiểm tra nội dung explain: môn thiếu, loại trực tiếp/gián tiếp, `path`, nhóm OR, thứ tự học gợi ý.
6. Nếu đủ điều kiện, xác nhận giao diện thông báo đủ điều kiện nhưng đăng ký đang chờ API M3.
7. Mở TKB: không có dữ liệu đăng ký thật vì backend chưa có `GET /timetable`; thử xem trước lớp từ danh mục tĩnh.
8. Kiểm tra console/network: không được có request tới `/courses`, `/timetable`, `/enroll` hoặc `/enroll/{id}` trong chế độ API thật.

## 7. Kiểm thử và build

```powershell
npm run test
npm run typecheck
npm run lint
npm run build
```

## 8. Việc cần M2/M3/M4 bàn giao

- **M2:** schema explain đã có trong backend; phối hợp kiểm thử dữ liệu seed và xác nhận nội dung hiển thị.
- **M3:** cung cấp `GET /courses` cho sinh viên, `GET /timetable`, `POST /enroll`, `DELETE /enroll/{id}`; chốt ID, request/response, idempotency key, lỗi nghiệp vụ và WAITLISTED.
- **M4:** xác nhận chính sách lưu token và vòng đời phiên; hiện client lưu session trong `sessionStorage` theo phiên tab.
- **M5:** đưa lint/build frontend vào CI và thống nhất Docker build context.
