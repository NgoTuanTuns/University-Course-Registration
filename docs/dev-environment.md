# Dựng môi trường phát triển

## Chuẩn bị

Cài Docker Desktop và Git. Tạo file cấu hình cục bộ bằng PowerShell tại thư mục gốc repo:

```powershell
copy .env.example .env
```

Không commit file .env. Chỉ sửa giá trị trong .env.example khi cần thêm biến môi trường cho cả nhóm.

## Chạy hệ thống

```powershell
docker compose up --build
```

Ứng dụng: http://localhost:8080  
Vite trực tiếp: http://localhost:5173  
Swagger: http://localhost:8000/docs

Lần đầu dùng DB:

```powershell
docker compose exec api alembic upgrade head
docker compose exec api python -m app.seed
```

Các container dùng tên dịch vụ db, redis, api để kết nối nội bộ. Từ máy Windows dùng các cổng 5433 và 6380 để truy cập PostgreSQL và Redis.

Dừng hệ thống mà giữ dữ liệu:

```powershell
docker compose down
```

Xóa cả dữ liệu PostgreSQL:

```powershell
docker compose down -v
```

## Database kiểm thử

Volume mới tự tạo database course_reg_test. Script khởi tạo chỉ chạy khi volume PostgreSQL còn trống. Nếu volume đã tồn tại từ trước, tạo database test một lần:

```powershell
docker compose exec db createdb -U course_user course_reg_test
```

Backend test dùng course_reg_test và Redis database 1; dữ liệu demo dùng course_reg và Redis database 0. Không trỏ test vào database demo.

## Trạng thái cần phối hợp

Cấu hình web dùng package.json và src/ ở thư mục gốc như nhánh giao diện M1 hiện tại. Tích hợp Compose đầy đủ cần phần giao diện M1 được merge vào main. M1 hiện dùng React 19 trong package.json, trong khi quy ước chung ghi React 18; nhóm cần thống nhất phiên bản trước khi nghiệm thu.
