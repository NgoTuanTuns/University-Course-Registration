# M1 — Frontend Web Developer

Bộ bàn giao gồm ba phiên bản lũy tiến của phần frontend hệ thống Đăng ký Học phần & Kiểm tra Điều kiện Tiên quyết.

## 1. Các phiên bản

| Thư mục | Phạm vi | Chế độ chạy |
|---|---|---|
| `M1_1` | Week 1: nền tảng SPA, MSW, đăng nhập demo, tra cứu và 5 nhóm bộ lọc | Mock, không cần backend |
| `M1_2` | Week 2: kế thừa Week 1, thêm TKB dạng lưới, xem trước và phát hiện xung đột | Mock, không cần backend |
| `M1_3` | Week 3: kế thừa Week 1–2, auth/refresh/logout và prerequisite check/explain thật; phần chưa có API chỉ hiển thị tĩnh | Backend thật cho endpoint có; danh mục/TKB tĩnh; đăng ký/hủy bị khóa |

Mỗi thư mục là một ứng dụng Vite độc lập, có `.env.development`, `.env.example` và README riêng.

## 2. Yêu cầu chung

- Windows 10/11.
- Node.js 20 LTS và npm.
- VS Code (khuyến nghị).
- Không cần backend để chạy `M1_1` và `M1_2`.
- `M1_3` cần backend nhóm chạy tại `http://localhost:8000` để đăng nhập và kiểm tra tiên quyết thật.

## 3. Chạy một phiên bản

Mở terminal tại thư mục phiên bản cần chạy, ví dụ:

```powershell
cd .\M1_1
npm install
npm run dev
```

Mở URL Vite hiển thị (mặc định `http://localhost:5173`). Không chạy đồng thời nhiều phiên bản trên cùng cổng; nếu cần chạy nhiều bản, dừng bản trước hoặc đổi cổng.

## 4. Lệnh chất lượng

Trong từng thư mục tuần:

```powershell
npm run test
npm run typecheck
npm run lint
npm run build
```

## 5. Nguyên tắc tích hợp

- Mọi request frontend đi qua `src/api/`.
- Backend JSON snake_case được chuyển thành camelCase tại một lớp HTTP duy nhất.
- Week 1–2 dùng MSW theo cùng đường dẫn API dự kiến.
- Week 3 chỉ gọi endpoint được xác nhận tồn tại trong backend hiện tại.
- Không tạo thành công giả cho đăng ký, hủy, waitlist hoặc TKB thật khi API tương ứng chưa được bàn giao.
- Danh mục tĩnh Week 3 chỉ để hiển thị/xem trước và kiểm tra tiên quyết theo bộ seed KIT; README Week 3 ghi rõ điều kiện ánh xạ ID.

## 6. Tài liệu

- `M1_1/README.md`: hướng dẫn Week 1.
- `M1_2/README.md`: hướng dẫn Week 2.
- `M1_3/README.md`: hướng dẫn Week 3 và ma trận API đã có/chưa có.

## 7. Kiểm tra đóng gói

- Đã kiểm tra cấu trúc ba ứng dụng, đường dẫn import nội bộ, JSON của `package.json`/`tsconfig.json` và luồng ánh xạ ID seed của Week 3.
- Đã chạy smoke test độc lập cho logic phát hiện trùng lịch và dữ liệu demo Week 2: **đạt**.
- Chưa chạy được `npm install`, `npm run test`, `npm run lint` và `npm run build` trong môi trường đóng gói này vì truy cập `registry.npmjs.org` bị lỗi DNS (`EAI_AGAIN`). Sau khi giải nén trên máy có Internet, chạy `npm install` trước; lệnh này sẽ đồng bộ `package-lock.json` với các dependency ESLint vừa bổ sung. Sau đó chạy bốn lệnh kiểm tra trong README từng tuần.
