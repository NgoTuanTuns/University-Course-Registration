# M1 — Week 2: Thời khóa biểu tuần và phát hiện xung đột

## 1. Mục tiêu

Kế thừa toàn bộ Week 1 và bổ sung lưới thời khóa biểu, xem trước lớp học phần và phát hiện trùng lịch ngay trên trình duyệt.

## 2. Chức năng đã triển khai

Bao gồm toàn bộ chức năng Week 1, đồng thời:

- Trang `/timetable` dạng lưới từ Thứ Hai đến Chủ nhật, khung giờ 07:00–21:00.
- Hiển thị mã môn, tên môn, lớp, phòng và thời gian của từng buổi.
- Màu sắc theo học phần; lớp xem trước dùng viền nét đứt; lớp xung đột dùng viền đỏ và ký hiệu cảnh báo.
- Xem trước học phần từ trang tra cứu; lớp được thêm tạm vào lưới và có thể bỏ xem trước.
- Dữ liệu mock có lớp nhiều buổi/tuần, lớp trùng giờ và lớp liền ca để kiểm thử.
- Logic thuần: `parseTime`, `formatTime`, `slotsOverlap`, `findSlotConflicts`, `findConflicts`.
- Hai ca liền nhau (ví dụ 07:00–09:30 và 09:30–12:00) không bị tính là trùng.
- Một lớp có nhiều buổi chỉ được liệt kê một lần trong danh sách lớp xung đột.

## 3. Công nghệ và cấu trúc

Giữ nguyên cấu trúc Week 1; logic lịch nằm trong `src/features/timetable/` và test trong `conflicts.test.ts`.

## 4. Cách chạy trên Windows / VS Code

1. Mở VS Code tại thư mục `M1_2`.
2. Mở Terminal và chạy:

   ```powershell
   npm install
   npm run dev
   ```

3. Mở `http://localhost:5173` (hoặc địa chỉ được Vite hiển thị).
4. Đăng nhập demo như Week 1. `VITE_USE_MOCK=true` và `VITE_WEEK=2` đã được đặt trong `.env.development`.

Không cần backend để xem lưới và thử phát hiện xung đột.

## 5. Kịch bản demo thời khóa biểu

1. Đăng nhập bằng `sv0001@uni.edu.vn`.
2. Mở **Tra cứu học phần**.
3. Tìm `INT132` và nhấn **Xem trước**. Lớp này được cấu hình trùng một phần với lớp INT131 đang có trong TKB mẫu; block phải có viền đỏ và ký hiệu cảnh báo.
4. Tìm `INT133` để kiểm tra hai ca liền kề không bị đánh dấu trùng.
5. Bỏ xem trước và kiểm tra cảnh báo được cập nhật ngay.
6. Kiểm tra một lớp có nhiều buổi trong tuần; các buổi phải hiển thị đúng ngày/giờ.

## 6. Kiểm thử và build

```powershell
npm run test
npm run typecheck
npm run lint
npm run build
```

Bộ test bao gồm:

- Chuyển đổi giờ.
- Trùng hoàn toàn và trùng một phần.
- Hai ca liền kề.
- Khác ngày.
- Khoảng thời gian không hợp lệ.
- Nhiều lớp xung đột qua nhiều buổi.
- Không tự xung đột với chính lớp đang xét.
- Không nhân đôi một lớp trong kết quả xung đột.
- Xác định buổi cụ thể bị trùng.

## 7. Phạm vi chưa thuộc Week 2

- Chưa có đăng ký/hủy học phần thật.
- TKB hiện lấy từ dữ liệu mock; API `GET /timetable` chưa có trong backend nhóm ở thời điểm đối chiếu.
- Máy chủ vẫn là nơi quyết định cuối cùng về trùng lịch khi API đăng ký được bàn giao; kiểm tra ở frontend chỉ nhằm cảnh báo tức thì.

## 10. Mô phỏng mã lỗi API

Khi MSW đang bật, mở DevTools → Console và chạy ví dụ:

```js
fetch("/api/v1/__mock-error/SCHEDULE_CONFLICT").then(async (r) => ({ status: r.status, body: await r.json() }))
```

Thay `SCHEDULE_CONFLICT` bằng một trong các mã: `UNAUTHENTICATED`, `TOKEN_EXPIRED`, `FORBIDDEN`, `NOT_FOUND`, `PREREQ_NOT_MET`, `CREDIT_LIMIT_EXCEEDED`, `SCHEDULE_CONFLICT`, `ALREADY_ENROLLED`, `CONCURRENT_UPDATE` hoặc `RATE_LIMITED`.
