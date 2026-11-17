# BÀN GIAO CÔNG VIỆC M4 — TUẦN 6

**Vai trò:** M4 (Database & Security Engineer)  
**Nội dung:** Chốt seed demo, đóng băng cấu trúc CSDL/API và hoàn thiện tài liệu kỹ thuật.

---

## 1. Chốt Seed Demo & Tái lập 100%
- **Tài khoản demo cố định:**
  - Admin: `admin@uni.edu.vn` / `Admin@123`
  - Sinh viên kịch bản: `sv0001@uni.edu.vn` – `sv0004@uni.edu.vn` (và `sv0005` – `sv1000`) / `Student@123`.
- **An toàn khi chạy lặp (Idempotent):** `python -m app.seed` tự động kiểm tra nếu DB đã có dữ liệu thì bỏ qua, không gây lỗi trùng lặp.
- **Đặt lại demo nhanh:** `python -m app.seed --reset` xóa sạch 7 bảng theo thứ tự phụ thuộc khóa ngoại, reset identity sequence và nạp lại bộ dữ liệu chuẩn 100% không cần internet.

## 2. Đóng băng & Dọn dẹp Chất lượng Mã nguồn
- **Alembic Migration:** Chỉ tồn tại **1 head duy nhất** (`4cf23a63c3a3`), không xung đột nhánh migration.
- **Linter & Formatter:** `ruff check backend/` và `ruff format --check backend/` sạch 100% (83/83 file).
- **OpenAPI Contract:** `python -m app.tools.openapi_snapshot --check` khớp 100% với `docs/openapi.json` cho toàn bộ endpoint `/auth/*`, `/admin/*`.

## 3. Tài liệu Kỹ thuật Hoàn chỉnh
- [`docs/database.md`](../../docs/database.md): Sơ đồ 7 bảng, 19 chỉ mục chiến lược, 2-phase locking (`ORDER BY id ASC`), advisory lock DAG (`0x50524551`), pool tuning, ràng buộc `CHECK`, quy trình migration và tài khoản demo.
- [`docs/security.md`](../../docs/security.md): Ma trận kiểm định OWASP Top 10 (A01–A10), vòng đời JWT + Refresh Token Rotation, RBAC 2 vai trò, Rate Limiting và các header bảo mật Nginx.
