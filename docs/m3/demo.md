# Demo và bảo vệ M3

## Chạy từ checkout

Tại thư mục gốc: sao chép `.env.example` thành `.env` nếu chưa có, rồi `docker compose -p cnpm-m3 up -d db redis`. Trên máy này các dịch vụ đã chạy ở cổng PostgreSQL 5433, Redis 6380. Không dùng cổng nginx 8080 vì đang có ứng dụng khác sử dụng.

Tại `backend`, cài `python -m pip install -r ../requirements.txt`. Khi chạy Python trực tiếp trên Windows, đặt DATABASE_URL/TEST_DATABASE_URL trỏ localhost:5433 và TEST_REDIS_URL trỏ localhost:6380/1, dùng thông tin đăng nhập DB từ `.env` của bạn. Không dùng hostname `db`/`redis` của Docker khi chạy trên host.

```powershell
$env:APP_ENV = 'test'
# Đặt URL phù hợp thông tin PostgreSQL của bạn; DB bắt buộc course_reg_test.
$env:DATABASE_URL = $env:TEST_DATABASE_URL
$env:TEST_REDIS_URL = 'redis://localhost:6380/1'
python -m alembic upgrade head
python -m app.tools.m3_benchmark --students 4 --rounds 1 --output ../docs/m3/demo-result.json
```

Công cụ tạo 4 tài khoản demo tạm không dùng đăng nhập mật khẩu, lớp 1 chỗ, gửi request qua FastAPI với token thật của M4. Kỳ vọng một ACTIVE, một WAITLISTED và hai WAITLIST_FULL. Người ACTIVE hủy qua API, người chờ được đôn, công cụ kiểm tra bất biến rồi dọn đúng những dòng nó tạo. Kết quả JSON không chứa token/mật khẩu và có thể dùng làm bản dự phòng.

## Kịch bản 3–4 phút

1. 30 giây: mở slide bài toán một chỗ và giải thích vì sao SELECT rồi INSERT có thể race.
2. 60 giây: chạy demo 4 tài khoản hoặc test T12 200 request; chỉ ra đúng một ACTIVE và sĩ số tương ứng.
3. 60 giây: dùng kết quả `promoted_correctly` và test T7/T9 để giải thích hủy + đôn cùng transaction, người đầu hàng bị chặn vẫn giữ hàng.
4. 45 giây: chỉ ra `invariant_violations=0`, giải thích Redis là tối ưu bổ sung và các ca gate hết hạn/mất kết nối.
5. 30 giây: trình bày giới hạn số đo ASGI cục bộ, phần nghiệm thu tải mạng cần M5.

Frontend hiện vẫn có ghi chú chờ API M3; buổi demo giao diện cần M1 nối adapter theo hợp đồng. M3 cung cấp API và demo backend, không sửa phần M1.

## Lệnh kiểm chứng

```powershell
python -m ruff check app tests
python -m ruff format --check app tests
python -m app.tools.openapi_snapshot --check
python -m pytest --no-cov -q
python -m pytest tests/test_enrollment_concurrency.py --no-cov -q
python -m app.tools.m3_benchmark --students 200 --rounds 3 --output ../docs/m3/benchmark-db.json
python -m app.tools.m3_benchmark --students 200 --rounds 3 --redis-lock --output ../docs/m3/benchmark-redis.json
```

Không chạy test và benchmark đồng thời vì fixture test dọn course_reg_test. Bộ concurrency phải lặp tối thiểu 20 lượt trước nghiệm thu; log kết quả nằm trong bàn giao. Workflow backend hiện có đã chạy marker concurrency, M5 cần cấu hình branch protection/job stress định kỳ trên GitHub.

## Câu hỏi bảo vệ

- **Vì sao version không đủ?** Version ở enrollment, còn enrolled_count ở offering. Câu UPDATE có điều kiện bảo vệ sĩ số, version bảo vệ cập nhật đăng ký.
- **Một sinh viên đăng ký hai lớp cùng lúc?** Khóa dòng students tuần tự hóa cả hai kiểm tra tín chỉ/lịch trước khi ghi.
- **Redis chết hoặc TTL hết giữa transaction?** DB vẫn giữ khóa/ràng buộc và UPDATE nguyên tử. Idempotency response có thể không replay khi cache mất, nhưng không có đăng ký ACTIVE trùng.
- **READ COMMITTED có đủ?** Có với những invariant đang bảo vệ bằng khóa theo sinh viên và offering; đây là bằng chứng theo từng thao tác, không phải khẳng định mọi luồng tương lai đều an toàn.
- **Người chờ đầu tiên bị trùng lịch?** Giữ họ trong hàng, trả blocked_reason, xét người đủ điều kiện tiếp theo. Position liên tục sau đôn/rời hàng.
- **Tránh deadlock?** Khóa student ID tăng dần trước offering, đọc lại tập ứng viên và retry có giới hạn.
- **Đã đạt tải 2.000 sinh viên chưa?** Chưa nghiệm thu tải mạng; số đo kèm theo là ASGI cục bộ, không thay báo cáo Locust của M5.
