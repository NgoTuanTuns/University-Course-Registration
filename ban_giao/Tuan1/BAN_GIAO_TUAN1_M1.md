# M1 — Week 1: Nền tảng frontend và tra cứu học phần

## 1. Mục tiêu

Hoàn thiện SPA React 18 + TypeScript + TailwindCSS, đăng nhập demo, phân quyền giao diện và tra cứu học phần trên dữ liệu giả. Week 1 chưa yêu cầu backend thật.

## 2. Chức năng đã triển khai

- React 18, TypeScript `strict`, Vite 6, React Router và TailwindCSS.
- MSW được khởi động tự động khi `VITE_USE_MOCK=true`; request mock đi qua cùng lớp `src/api/` như API thật.
- Đăng nhập demo bằng email/mật khẩu; email bắt đầu bằng `admin` mở khu vực quản trị mẫu, tài khoản còn lại là sinh viên.
- Route guard giao diện: sinh viên không thấy liên kết quản trị và bị chuyển hướng nếu truy cập `/admin/*`.
- Tra cứu 40 lớp học phần mẫu, phân trang 20 dòng/trang.
- Bộ lọc: từ khóa (mã/tên), mã lớp, tín chỉ, giảng viên, thứ + khoảng giờ.
- Debounce 300 ms; hủy request cũ bằng `AbortController` khi thay đổi bộ lọc.
- Đồng bộ toàn bộ bộ lọc và trang lên query string của URL; tải lại trang vẫn giữ bộ lọc.
- Có trạng thái loading dạng skeleton, rỗng, lỗi và nút thử lại.
- Giao diện sáng/tối; responsive cho màn hình nhỏ.

## 3. Công nghệ và cấu trúc

```text
src/
├── api/                 # HTTP client, auth/courses/timetable/prerequisite API
├── features/timetable/  # logic thời gian và unit test dùng từ Week 2
├── mocks/               # MSW worker và dữ liệu mẫu
├── pages/               # wrapper tương thích, App chính ở src/App.tsx
├── types/               # kiểu dữ liệu dùng chung
├── App.tsx              # layout, routes, màn hình tra cứu
├── main.tsx             # bootstrap MSW và React
└── style.css
```

## 4. Yêu cầu cài đặt

- Node.js và npm.

## 5. Cách chạy trên Windows / VS Code

1. Kiểm tra Node/npm:

   ```powershell
   node -v
   npm -v
   ```

2. Cài thư viện:

   ```powershell
   npm install
   ```

3. Chạy:

   ```powershell
   npm run dev
   ```

6. Mở địa chỉ Vite hiển thị trong terminal, mặc định `http://localhost:5173`.

`.env.development` đã cấu hình `VITE_USE_MOCK=true`, MSW tự bật; không cần chạy backend.

## 6. Tài khoản demo

| Vai trò | Email | Mật khẩu |
|---|---|---|
| Sinh viên | `sv0001@uni.edu.vn` | Nhập chuỗi bất kỳ không rỗng |
| Quản trị | `admin@uni.edu.vn` | Nhập chuỗi bất kỳ không rỗng |

Tài khoản mô phỏng, không phải tài khoản backend.

## 7. Kiểm thử và build

```powershell
npm run test
npm run typecheck
npm run lint
npm run build
```

- `test`: chạy Vitest.
- `typecheck`: kiểm tra TypeScript strict.
- `lint`: chạy ESLint.
- `build`: typecheck và build Vite production.

## 8. Kịch bản kiểm tra nhanh

1. Đăng nhập bằng `sv0001@uni.edu.vn`.
2. Tìm `INT131`, thử lọc tín chỉ, mã lớp, giảng viên và ngày/giờ.
3. Kết hợp nhiều bộ lọc, kiểm tra URL thay đổi.
4. Chuyển trang rồi nhấn F5; bộ lọc và trang phải được khôi phục.
5. Nhập từ khóa không có kết quả để xem trạng thái rỗng.
6. Đăng xuất, đăng nhập bằng `admin@uni.edu.vn`; kiểm tra liên kết quản trị xuất hiện.

## 9. Mô phỏng mã lỗi API

Khi MSW đang bật, mở DevTools → Console và chạy ví dụ:

```js
fetch("/api/v1/__mock-error/SCHEDULE_CONFLICT").then(async (r) => ({ status: r.status, body: await r.json() }))
```

Thay `SCHEDULE_CONFLICT` bằng một trong các mã: `UNAUTHENTICATED`, `TOKEN_EXPIRED`, `FORBIDDEN`, `NOT_FOUND`, `PREREQ_NOT_MET`, `CREDIT_LIMIT_EXCEEDED`, `SCHEDULE_CONFLICT`, `ALREADY_ENROLLED`, `CONCURRENT_UPDATE` hoặc `RATE_LIMITED`.
