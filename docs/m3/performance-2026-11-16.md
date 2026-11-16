# Kiểm chứng tải M3 ngày 16/11/2026

## Môi trường và cách đo

Python 3.11.9 Windows, một uvicorn worker trên loopback TCP, PostgreSQL 15 Docker dùng tmpfs riêng (fsync=on, max_connections=100), Redis 7.4 Docker. Pool ứng dụng giữ nguyên 5 + 10. Không dùng dữ liệu demo/production, không thay cấu hình DB toàn cục. Không coi tmpfs là phép đo độ bền ghi đĩa hoặc đại diện máy triển khai.

Mỗi lượt: 2.000 sinh viên giả, JWT riêng và Idempotency-Key riêng, đến đều trong cửa sổ 30 giây, tranh một lớp chỉ có 1 chỗ. Tất cả request hoàn tất rồi kiểm tra invariant, hủy người ACTIVE, kiểm tra đôn đúng người chờ và invariant lần nữa. Công cụ tự dọn đúng dữ liệu tạo ra. Chỉ retry một lần khi lỗi transport, giữ cùng key, không retry 409/500; báo cáo ghi tổng HTTP attempts và lỗi mạng cần retry. P50/P95 đo từ lúc bắt đầu request đầu tới kết quả cuối, gồm thời gian retry. `last_arrival_sec` cho biết thời điểm đến thực tế; không giấu sai lệch lịch gửi khi máy bận.

Đây là workload M3 qua HTTP thật, không gồm Nginx, đăng nhập mật khẩu, search/explain, đa lớp hoặc trải nghiệm trình duyệt. Ngưỡng P95 nghiệm thu chung cần M5 xác nhận; chưa tự đặt tiêu chuẩn production.

## Kết quả cuối

| Cấu hình | P95 từng lượt (ms) | Trung vị P95 (ms) | Tổng network retries | 5xx / lỗi mạng cuối |
|---|---|---|---|---|
| db | 2545.33, 1531.61, 4504.39 | 2545.33 | 0 | 0 |
| redis | 9070.39, 8848.04, 9144.31 | 9070.39 | 3 | 0 |

Cả 6 lượt: đúng một ACTIVE, một WAITLISTED, hủy/đôn đúng, 0 vi phạm invariant. Các 409 WAITLIST_FULL là kết quả nghiệp vụ hợp lệ; CONCURRENT_UPDATE là phản hồi yêu cầu thử lại khi gate hoặc DB admission quá tải. Không coi việc trả 409 nhanh là throughput ghi thành công cao hơn. Giữ gate mặc định tắt; đọc đầy đủ các bộ đếm trong JSON thay vì chỉ nhìn P95.

## Dữ liệu khảo sát và sửa lỗi

- `tcp-initial-db-2000.json`: bản chỉ có lock timeout, chưa có admission deadline. Ba lượt ghi nhận tổng 24 HTTP 500; không mất toàn vẹn dữ liệu. Đây là kết quả **không đạt**.
- `tcp-db-no-retry-2000.json`: sau bổ sung deadline lấy kết nối M3, trước khi thêm retry transport cho harness. Cả ba lượt không 5xx/lỗi mạng, nhưng độ trễ dao động.
- `tcp-initial-redis-2000.json`: gate bật, chưa retry transport trong harness, 5 lỗi kết nối cuối, 0 HTTP 500 và 0 vi phạm invariant. Đây là kết quả **không đạt** về transport.
- `tcp-redis-diagnostic.json`: một lượt kiểm tra lại gate bật không lỗi; không lấy riêng lượt thuận lợi này thay cho chuỗi ba lượt.
- `tcp-db-2000.json`, `tcp-redis-2000.json`: chuỗi cuối có cùng chính sách client, ba lượt mỗi cấu hình, giữ cả đếm retry.

Khi thiếu connection, lock_timeout của PostgreSQL chưa có hiệu lực vì request chưa lấy được connection. Bản sửa giới hạn riêng bước admission, rollback khi timeout và trả CONCURRENT_UPDATE. Test hồi quy giữ cứng connection duy nhất của pool và kiểm tra cả gate bật/tắt. Các lượt đo chạy tuần tự trên máy dùng chung, không phải thử nghiệm kiểm soát tải nền; không suy ra phần trăm cải thiện nhân quả chỉ từ các số P95 trước/sau.
