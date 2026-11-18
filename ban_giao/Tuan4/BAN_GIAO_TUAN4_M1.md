# Bàn giao Tuần 4 — M1 (Frontend)

Ngày lập: 18/11/2026  
Phạm vi: frontend trong `src/`. Người nhận: M5 review; M2, M3, M4 phối hợp tích hợp.

## Nội dung đã triển khai

- Danh sách chờ `/waitlist`: danh sách lớp, vị trí, thời điểm tham gia, nút rời hàng và quy tắc vào trước ra trước.
- Làm mới mỗi 30 giây và khi cửa sổ lấy lại focus; hiển thị lý do bị chặn do trùng lịch hoặc vượt tín chỉ.
- Nút lớp đầy đổi thành “Vào danh sách chờ”; gửi qua `POST /enroll`, dùng trạng thái server để phân biệt ACTIVE và WAITLISTED.
- Thanh tín chỉ, cảnh báo từ 90% và khi đạt hạn mức; cảnh báo sớm khi đăng ký vượt hạn mức nhưng vẫn gửi server quyết định.
- Quản trị học phần: tìm kiếm, thêm/sửa/xóa, kiểm tra tín chỉ 1–10 và xác nhận xóa; route và menu kiểm tra vai trò admin.
- Hủy đăng ký có xác nhận tên và mã môn trước khi gửi yêu cầu.
- Bỏ khối trang trí sidebar che nút đăng xuất; đổi “Thứ học” thành “Ngày học”, bỏ hai ô lọc giờ theo yêu cầu.
- Sửa lệch danh mục mock khiến INT331 bị đăng ký thành INT138. Mock đăng ký dùng cùng danh mục với tra cứu; lớp đầy được lưu vào hàng chờ, không thêm vào đăng ký ACTIVE.

## File chính

- `src/App.tsx`: giao diện, route và luồng thao tác.
- `src/api/waitlist.ts`: ánh xạ phản hồi hàng chờ dạng phẳng của backend sang dữ liệu giao diện.
- `src/mocks/browser.ts`: mock đăng ký và hàng chờ có trạng thái trong bộ nhớ.

## Hợp đồng tích hợp

- `POST /enroll` với offering_id; ACTIVE hoặc WAITLISTED do server quyết định.
- `DELETE /enroll/{id}`; `GET /timetable?term=2026-1`.
- `GET /waitlist?page=1&page_size=100`; `DELETE /waitlist/{id}`.
- `/admin/courses`: GET, POST; `/admin/courses/{id}`: PUT, DELETE.
- Backend đã có các endpoint này; chưa xác nhận E2E bằng backend thật trong phiên bàn giao.

## Kiểm chứng và giới hạn

- `npx tsc --noEmit`: thành công sau các đợt sửa.
- Chưa có bằng chứng kiểm thử trình duyệt tự động hoặc nghiệm thu E2E với backend thật.
- Chưa hoàn thiện phát hiện được đôn từ hàng chờ để toast và cập nhật TKB/tín chỉ tự động.
- Trang hàng chờ hiện lấy tối đa 100 dòng; quản trị học phần chưa có điều khiển phân trang đầy đủ.
- Tín chỉ hiện cộng từ danh sách TKB; cần kiểm chứng ACTIVE/cùng kỳ và lấy hạn mức mặc định 25 khi dữ liệu thiếu.
- Cần bổ sung test trạng thái hàng chờ/ngưỡng tín chỉ, trạng thái loading/lỗi và bảo vệ gửi lặp cho các thao tác còn thiếu.
- Mock lưu trong bộ nhớ, mất khi tải lại trang, không phải dữ liệu backend hay dữ liệu theo tài khoản.

## Hướng dẫn kiểm tra

Tại thư mục chứa package.json, chạy:

```powershell
$env:VITE_WEEK="4"
$env:VITE_USE_MOCK="true"
npm run dev
```

Đăng nhập mock bằng `sv0001@uni.edu.vn` hoặc `admin@uni.edu.vn`, mật khẩu bất kỳ. Thử INT331 đầy: đăng ký phải báo WAITLISTED, xuất hiện ở hàng chờ và không thêm vào TKB; rời hàng phải xóa dòng. Kiểm tra hủy đăng ký với cả lựa chọn hủy hộp thoại và xác nhận. Kiểm tra tài khoản sinh viên không vào được trang admin.

Để tích hợp thật, đặt VITE_USE_MOCK=false và dùng tài khoản backend. Cần M3/M4 cấp dữ liệu phù hợp; M5 chạy bug bash và ghi kết quả trước nghiệm thu.
