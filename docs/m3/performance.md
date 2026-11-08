# Số đo cục bộ M3

Ngày đo: 08/11/2026. Python 3.11.9 trên Windows, FastAPI qua httpx ASGITransport trong cùng tiến trình; PostgreSQL 15 và Redis 7.4 chạy Docker Desktop. Pool 5, max_overflow 10, một lớp 1 chỗ và 200 sinh viên riêng cho mỗi lượt. Ba lượt cho mỗi cấu hình, dọn dữ liệu sau mỗi lượt.

P95 tính trên tất cả request, gồm cả lỗi nghiệp vụ 409. CONCURRENT_UPDATE do gate hết thời gian chờ được ghi riêng; trả lỗi sớm có thể giảm P95 mà không tăng throughput thành công. Không so P95 đơn lẻ để kết luận gate tốt hơn. Mỗi lượt phải có đúng một ACTIVE, một WAITLISTED, hủy đôn đúng người và không có vi phạm invariant.

Tối ưu M3: giữ khóa student trong toàn bộ kiểm tra nhưng chỉ lấy khóa offering sau khi kiểm tra điều kiện. Khi có khóa offering, đọc lại course_id/term/schedule; đổi dữ liệu thì retry. Cách này cho phép nhiều sinh viên khác nhau kiểm tra song song, giảm phần công việc nằm trong khóa lớp.

Các tệp `benchmark-initial-*.json` là số đo khảo sát trước tối ưu, lúc máy còn chạy build Docker. Giữ để truy vết, không dùng chúng làm bằng chứng nhân quả trước/sau vì tải nền khác nhau. Các tệp `benchmark-db.json` và `benchmark-redis.json` là số đo của bản cuối sau khi build đã xong.

Các số đo này chưa thay thế chạy qua TCP/Nginx, workload nhiều lớp, 2.000 sinh viên trong 30 giây, rate limit và tiêu chí P95 do M5 chốt. Giữ gate mặc định tắt; cần M4/M5 nghiệm thu môi trường triển khai trước khi chỉnh pool hay bật gate theo tải thực tế.

## Kết quả bản cuối

| Cấu hình | P95 từng lượt (ms) | Trung vị P95 (ms) | Lỗi nghiệp vụ qua 3 lượt |
|---|---|---|---|
| db | 3597.29, 3316.31, 4379.52 | 3597.29 | WAITLIST_FULL=594 |
| redis | 3830.6, 3811.44, 4058.62 | 3830.60 | CONCURRENT_UPDATE=488, WAITLIST_FULL=106 |

Cả 6 lượt đều đúng một ACTIVE và một WAITLISTED, đôn đúng người sau hủy, 0 vi phạm invariant, 0 HTTP 5xx. Các lỗi 409 được phân loại trong JSON gốc.

Trong mẫu đo này, gate có trung vị P95 3.830,60 ms so với DB-only 3.597,29 ms và 488 CONCURRENT_UPDATE trên 600 request. Không có căn cứ bật gate mặc định; giữ tắt để tránh yêu cầu thử lại không cần thiết trong cấu hình hiện tại.
