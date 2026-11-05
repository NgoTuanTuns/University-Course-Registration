# Hệ thống Đăng ký Học phần

Dự án môn Công nghệ phần mềm: hệ thống đăng ký học phần và kiểm tra điều kiện tiên quyết. Repo được thiết kế để chạy bằng Docker Compose trên Windows/Docker Desktop; không cần cài riêng Python, PostgreSQL hay Redis trên máy.

## Yêu cầu

- Git
- Docker Desktop đang chạy
- VS Code (khuyến nghị)

## Chạy toàn bộ hệ thống

Mở PowerShell tại thư mục gốc repo:

```powershell
copy .env.example .env
docker compose up --build
```

Giữ terminal này mở khi dùng ứng dụng. Nếu file `.env` đã tồn tại, không cần ghi đè; giữ cấu hình local của bạn.

Mở một terminal PowerShell khác để tạo/cập nhật bảng và nạp dữ liệu mẫu lần đầu:

```powershell
docker compose exec api alembic upgrade head
docker compose exec api python -m app.seed
```

Mở các địa chỉ:

- Ứng dụng qua Nginx: <http://localhost:8080>
- Swagger/API: <http://localhost:8000/docs>
- Vite dev server trực tiếp: <http://localhost:5173>

Dịch vụ và cổng máy host: Nginx `8080`, web `5173`, API `8000`, PostgreSQL `5433`, Redis `6380`. Container kết nối với nhau bằng tên dịch vụ `db`, `redis`, `api`, không dùng `localhost`.

## Chạy backend trong lúc frontend chưa có

Nếu nhánh hiện tại chưa có `package.json` ở thư mục gốc (đang chờ tích hợp frontend M1), có thể chỉ chạy các dịch vụ backend:

```powershell
docker compose up --build db redis api
```

Sau đó dùng Swagger tại <http://localhost:8000/docs>. Lệnh này không kiểm tra Nginx hoặc giao diện web.

## Kiểm thử và lint backend

```powershell
docker compose exec api pytest
docker compose exec api ruff check app tests
docker compose exec api ruff format --check app tests
```

Test tích hợp dùng database riêng `course_reg_test` và Redis DB 1; không đổi `TEST_DATABASE_URL` sang database demo. Script tạo DB test chạy khi PostgreSQL khởi tạo data volume mới. Nếu volume đã tồn tại từ trước khi có script, tạo database test một lần:

```powershell
docker compose exec db psql -U course_user -d postgres -c "CREATE DATABASE course_reg_test OWNER course_user"
```

Nếu báo database đã tồn tại thì không tạo lại.

## Lệnh thường dùng

```powershell
docker compose logs -f api
docker compose down
```

`docker compose down` dừng và xóa container nhưng giữ dữ liệu PostgreSQL. `docker compose down -v` xóa cả volume và dữ liệu; chỉ dùng khi muốn dựng lại database từ đầu.

## Quy tắc làm việc

- Làm trên nhánh riêng, không commit trực tiếp vào `main`.
- Mỗi PR cần có người khác review và chạy thử trước khi merge.
- Không commit `.env`, mật khẩu thật, token hoặc dữ liệu nhạy cảm.
- Quy ước API, database, kiểm thử và Git nằm trong `chitietcongviec/QUY_UOC_DU_AN.md`; kế hoạch vai trò M5 nằm trong `chitietcongviec/M5_cong_viec_7_tuan.md`.
