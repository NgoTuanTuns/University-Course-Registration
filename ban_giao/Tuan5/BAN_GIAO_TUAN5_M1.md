# Bàn giao Tuần 5 — M1 (Frontend)

Ngày lập: 18/11/2026  
Người nhận: M5 review; M2/M4 xác nhận nghiệp vụ tiên quyết, M3 xác nhận luồng tải.
Trạng thái: đã triển khai một phần; chưa nghiệm thu toàn bộ tiêu chí Tuần 5.

## Nội dung đã triển khai

- Menu admin và trang `/admin/prereqs`: chọn học phần, đọc điều kiện AND và các nhóm OR, thêm điều kiện với loại và số nhóm, xóa điều kiện.
- Chặn chọn chính môn đang quản trị làm tiên quyết; thông báo dễ hiểu khi nhận PREREQ_CYCLE.
- Trạng thái đang lưu và khóa nút thêm khi gửi request.
- Chuẩn hóa tên trường camelCase trong giao diện và lớp API quản trị để khớp chuyển đổi tập trung của HTTP.
- CONCURRENT_UPDATE: thử lại tối đa một lần sau khoảng chờ ngẫu nhiên ngắn.
- HTTP 429 có Retry-After dạng số: thử lại một lần; hiện thời gian chờ bị giới hạn tối đa 10 giây.
- Không gọi API TKB dành cho sinh viên ngay sau đăng nhập admin.
- Sửa nguyên nhân vòng lặp đăng nhập khi mở quản trị ở chế độ mock: bổ sung mock admin, tránh gửi token giả tới backend thật qua request bypass. Mock có CRUD học phần, xem/thêm/xóa tiên quyết và kiểm tra chu trình khi thêm.
- Không thêm thư viện cache mới. Không có endpoint seed giao diện; seed thực hiện bằng `python -m app.seed`.

## File chính

- `src/App.tsx`: quản trị tiên quyết và điều hướng theo vai trò.
- `src/api/admin.ts`: kiểu dữ liệu quản trị camelCase.
- `src/api/http.ts`: retry và xử lý phiên.
- `src/mocks/browser.ts`: mock quản trị trong bộ nhớ.

## Hợp đồng backend

- `GET /admin/courses`; chọn học phần từ danh mục.
- `GET /admin/prereqs/{course_id}`: and_prerequisites, or_groups và items.
- `POST /admin/prereqs`: course_id, prereq_course_id, type, group_no.
- `DELETE /admin/prereqs/{course_id}/{prereq_course_id}`.
- Backend có PUT cập nhật tiên quyết, nhưng giao diện hiện dùng thêm/xóa.
- Snake_case trên đường truyền được chuyển đổi tập trung tại HTTP.

## Kiểm chứng

`npx tsc --noEmit` thành công sau sửa lỗi quản trị và mock. Đây là kiểm tra kiểu dữ liệu, không thay thế kiểm thử trình duyệt hoặc E2E.

Lần build trước đã qua bước TypeScript nhưng Vite không đọc được đường dẫn cấu hình do giới hạn quyền môi trường. Chưa có kết quả build production được xác nhận sau các sửa đổi cuối.

## Các mục chưa hoàn tất / cần phối hợp

- Chưa có báo cáo Locust của M5 để phân tích hoặc nghiệm thu UX dưới spike test; không có số liệu phản hồi giao diện/bundle được đo và xác nhận.
- Chưa triển khai route lazy loading, memo hóa TKB/danh sách, đo bundle và thời gian tìm kiếm.
- Chưa kiểm tra đầy đủ bàn phím, aria, dialog focus và responsive trên thiết bị nhỏ.
- Thông báo chu trình hiện tổng quát, chưa đọc cycle_path để chỉ rõ các môn liên quan; chưa có cây xem trước tùy chọn.
- Danh mục chọn môn admin hiện chỉ lấy trang mặc định; cần tải đủ hoặc tìm kiếm phân trang khi số môn lớn.
- Retry-After cần hỗ trợ HTTP-date, chờ đủ thời gian server yêu cầu thay vì giới hạn 10 giây, thông báo đang chờ và hủy chờ khi request bị abort. Cần test bảo đảm không lặp thao tác ghi khi retry.
- Cần khóa chống gửi lặp chặt hơn cho các thao tác thêm/xóa và kiểm thử idempotency đăng ký.
- Mock chỉ phục vụ phát triển: mất dữ liệu khi tải lại, không phải kiểm chứng RBAC hoặc độ đúng của backend.
- M5 cần chạy bug bash, lint/build/test và E2E trên backend thật; M2/M4 xác nhận nhóm OR, chu trình, invalidation và schema cuối.

## Hướng dẫn chạy thử

Tại thư mục có package.json:

```powershell
$env:VITE_WEEK="5"
$env:VITE_USE_MOCK="true"
npm run dev
npx tsc --noEmit
```

Đăng nhập admin mock (admin@uni.edu.vn, mật khẩu bất kỳ), mở quản trị học phần và tiên quyết. Thêm A cần B, sau đó B cần A: phải bị từ chối; thử nhiều môn OR cùng group_no và xóa một điều kiện. Kiểm tra không bị mất phiên khi đổi trang.

Đổi VITE_USE_MOCK=false, khởi động lại Vite và dùng tài khoản backend để kiểm chứng tích hợp thật. M5 cần ghi kết quả và lỗi theo mức ưu tiên; không đánh dấu hoàn tất Definition of Done trước khi có bằng chứng spike/E2E.
