# Quyết định dự án

Cập nhật: 2026-11-05. Các đề xuất trong bảng được chép từ kế hoạch M5; chúng chưa được xem là quyết định của nhóm cho đến khi được ghi người chốt và ngày chốt.

Trạng thái: **Open**, **Decided**, hoặc **Deferred**. Khi chốt, điền cột “Quyết định đã chốt” và “Ngày/người chốt”. Với thay đổi hợp đồng API, cập nhật OpenAPI và gắn nhãn contract-change.

| ID | Nội dung cần chốt | Chủ trì | Hạn theo kế hoạch | Đề xuất trong kế hoạch | Trạng thái | Quyết định đã chốt | Ngày/người chốt |
|---|---|---|---|---|---|---|---|
| D01 | Endpoint tra cứu /courses hay /courses/search; tên tham số lọc | M3 | T1 | /courses theo quy ước | Open | | |
| D02 | explain dùng GET hay POST | M2 | T1 | POST body course_id | Open | | |
| D03 | Schema JSON của explain | M2 + M1 | T1 | Bản nháp Mục 1.1(d) file M2 | Open | | |
| D04 | Ngữ nghĩa tiên quyết bắc cầu | M2 + M5 | T1 | Đã học là đủ | Open | | |
| D05 | GET /timetable trả gì; nơi chứa max_credits | M3 + M1 | T1 | Trả total_credits và max_credits | Open | | |
| D06 | /enroll tự đưa vào hàng chờ hay cần POST /waitlist | M3 + M1 | T1 | /enroll trả 200 WAITLISTED | Open | | |
| D07 | Thêm DELETE /waitlist/{id} vào hợp đồng | M3 | T1 | Thêm | Open | | |
| D08 | Quy tắc nghỉ giữa hai ca; MIN_BREAK_MINUTES | M3 + M1 | T1 | Mặc định 0 | Open | | |
| D09 | Idempotency-Key gửi ở header hay body | M3 + M1 | T1 | Header | Open | | |
| D10 | Thứ tự kiểm tra lỗi; cùng môn trong kỳ; đăng ký lại môn đã đạt | M3 | T1 cuối | Đã đăng ký, tiên quyết, trùng lịch, tín chỉ, sĩ số; chặn cùng môn; không cho đăng ký lại môn đã đạt | Open | | |
| D11 | Người đầu hàng chờ không đủ điều kiện: giữ chỗ hay xóa | M3 + M1 | T2 | Giữ chỗ, trả blocked_reason | Open | | |
| D12 | Giới hạn waitlist dùng ceil hay floor | M3 | T2 | ceil | Open | | |
| D13 | prerequisites/check trả 200 eligible=false hay 422; tham số course_id | M2 + M3 | T1 | 200; course_id | Open | | |
| D14 | Engine có xét điểm tối thiểu không | M2 | T1 cuối | Không xét điểm; completed_courses chỉ chứa môn đạt | Open | | |
| D15 | Bổ sung mã lỗi PREREQ_CYCLE, WAITLIST_FULL, ALREADY_WAITLISTED, RATE_LIMITED, ALREADY_EXISTS, IN_USE, VALIDATION_ERROR, INTERNAL_ERROR | M5 | T1 cuối | Thêm và cập nhật quy ước/M1 | Open | | |
| D16 | Bổ sung khóa Redis và database 2 cho tải | M5 | T1 cuối | prereqgraph:v1, metrics:prereq:*, idem:enroll:*, refresh:*, ratelimit:*; Redis DB 2 cho tải | Open | | |
| D17 | Ai dựng core db, redis, errors, config, main | M5 | T1 | M5 dựng; core/security.py do M4 | Open | | |
| D18 | Nơi gọi invalidation khi completed_courses/DAG đổi | M4 + M2 | T2 | Seed/import và admin gọi hàm của M2 | Open | | |
| D19 | Frontend lưu token bằng HttpOnly cookie hay localStorage | M4 + M1 | T1 cuối | Cookie nếu kịp, nếu không localStorage và ghi rủi ro | Open | | |
| D20 | Có đăng ký tài khoản công khai /auth/register không | M4 | T1 cuối | Không | Open | | |
| D21 | Import seed qua giao diện admin | M4 + M1 | T2 | Không | Open | | |
| D22 | Công cụ frontend test và dữ liệu | M5 + nhóm | T1 cuối | Vitest và Playwright; các công cụ khác tùy nhóm | Open | | |
| D23 | Seed hồ sơ tải ít nhất 2.000 sinh viên và DB tải riêng | M4 + M5 | T2 | Đồng ý | Open | | |
| D24 | Tạo course_reg_test; migrate/seed thủ công hay một lệnh | M5 | T1 | Script init; profile prod tự migrate/seed khi trống | Open | | |
| D25 | Đo hiệu suất đôn waitlist | M3 + M5 | T2 | Log có cấu trúc và số liệu Locust | Open | | |
| D26 | Thêm router timetable.py | M3 | T1 | Thêm | Open | | |
| D27 | CHECK jsonb_typeof(schedule) = array | M4 | T2 | Chỉ làm nếu nhóm đồng ý | Open | | |
| D28 | Ngưỡng P95 và mức tối thiểu độ bao phủ | M5 + nhóm | Sau baseline | Quyết định từ số liệu thực | Open | | |
| D29 | Mốc đo của bài tải 2.000 người dùng/30 giây | M5 | T2 | Đăng nhập trước; đo từ lúc bắt đầu đăng ký | Open | | |

Ghi chú tài liệu nguồn: mục 1.4 của file M5 ghi 28 điểm, còn bảng Mục 9 liệt kê D01–D29 (29 điểm). Nhật ký này theo đủ 29 dòng của bảng Mục 9.
## Ghi chú hiện tại

- D17 đang được M5 triển khai trên nhánh riêng, chờ nhóm xác nhận.
- Nhánh M1 hiện dùng React 19; quy ước chung ghi React 18. Cần M1 và nhóm chốt trước khi tích hợp.
- Endpoint tra cứu ở bản M1 hiện có dự kiến /courses/search; D01 vẫn cần M3 chốt theo hợp đồng backend.


