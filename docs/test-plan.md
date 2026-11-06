# Kế hoạch kiểm thử — Tuần coding 2 (M5)

**Trạng thái:** Bản kế hoạch v1; chưa có bộ bất biến, snapshot OpenAPI hoặc Locust trong repo.

**Ngày:** 2026-11-06
**Căn cứ:** `chitietcongviec/M5_cong_viec_7_tuan.md`, `chitietcongviec/QUY_UOC_DU_AN.md`, bảng ca M2 và nhật ký `docs/decisions.md`.

## 1. Mục tiêu và nguyên tắc

Tuần này thiết lập cách chứng minh chất lượng trước khi mở rộng kiểm thử tải. Thứ tự ưu tiên là: làm rõ quy tắc → lập ca kiểm thử → chạy trên dữ liệu cô lập → nối vào CI → mới đo tải thử.

- Không đổi quy tắc nghiệp vụ chỉ để làm test xanh. Mọi quy tắc chưa chốt được ghi là phụ thuộc quyết định, không ngầm chọn một phương án.
- Test tích hợp dùng `course_reg_test` và Redis DB 1; không dùng DB demo, không chạy `pytest-xdist` trên cùng DB/Redis.
- Test nghiệm thu tiên quyết dùng đồ thị nhỏ trong bộ nhớ, không phụ thuộc seed hoặc thứ tự ID của DB.
- CLI bất biến chỉ đọc dữ liệu, trả danh sách vi phạm và thoát khác 0 khi có vi phạm; không tự sửa dữ liệu.
- Tuần 2 chỉ chạy Locust với vài chục user trên seed nhỏ. Spike 2.000 user/30 giây là tuần coding 4, không phải mục tiêu tuần này.
- Không ghi mật khẩu hoặc tệp tài khoản tải vào Git. Locust lấy tài khoản từ tệp cục bộ bị ignore hoặc biến môi trường.

## 2. Tháp kiểm thử và chủ sở hữu

| Mức | Phạm vi | Chủ sở hữu chính | Điều kiện đạt |
|---|---|---|---|
| Unit | Hàm thuần: đồ thị tiên quyết, lịch, quy tắc tính toán | Mỗi thành viên cho logic của mình; M5 cho bộ dùng chung | Ca biên có kết quả xác định; không cần DB/Redis |
| Integration | API cùng PostgreSQL/Redis, fixture và migration | Chủ sở hữu API; M5 giữ hạ tầng | Dùng test DB/Redis riêng; test dọn dữ liệu; không sửa DB demo |
| Bất biến | Tình trạng toàn vẹn sau test tranh chấp, seed hoặc tải | M5 viết công cụ; M3/M4 gọi và phản biện | `find_invariant_violations` phát hiện được lỗi ứng dụng; CLI thoát mã 0 nếu sạch, khác 0 nếu có vi phạm |
| Nghiệm thu | 21 ca tiên quyết + 5 ca thêm cạnh tạo chu trình từ M2 | M2 + M5 rà từng ca | Đồ thị trong bộ nhớ; kỳ vọng được M2 xác nhận; chạy trong CI và chặn merge khi sai |
| Hợp đồng | Schema response và OpenAPI snapshot | M5 cùng M1/M2/M3/M4 theo endpoint | Snapshot sinh ổn định; thay đổi hợp đồng không cập nhật snapshot thì CI thất bại |
| E2E | Luồng trình duyệt qua giao diện và API | M1 + M5 | Chưa thuộc phạm vi chạy bắt buộc tuần này khi frontend chưa tích hợp |
| Tải | Đăng nhập → tra cứu → tiên quyết → đăng ký → thời khóa biểu | M5; cần M3 API và M4 tài khoản/seed | Bản nháp chạy với vài chục tài khoản riêng; phân loại đúng lỗi nghiệp vụ và lỗi hệ thống |

## 3. Ánh xạ yêu cầu sang cách kiểm chứng

| Yêu cầu / quy tắc | Cách kiểm chứng | Trạng thái / phụ thuộc |
|---|---|---|
| Tiên quyết AND, bắc cầu, OR-group, phát hiện chu trình (`SR-F-02`) | Bộ 21 ca + 5 ca thêm cạnh; unit test trên `PrerequisiteGraph` trong bộ nhớ | Bảng ca đã có trong M2; cần pairing review M2×M5. Ca #6 phụ thuộc D04; ca #16 cần chốt cách diễn giải lựa chọn OR có tiên quyết riêng |
| Không đăng ký trùng, giữ sĩ số nguyên tử (`UR-F-04`, `SR-F-04`) | Test API/tích hợp và bất biến I1–I3, I7; test tranh chấp thuộc bước tích hợp với M3 | Endpoint enrollment của M3 chưa có trong snapshot repo hiện được đọc; không giả lập API chưa tồn tại |
| Không vượt tín chỉ (`UR-F-05`) | Test tích hợp và bất biến I4 theo từng sinh viên/kỳ | Cần dữ liệu test có nhiều lớp trong cùng kỳ |
| Không trùng lịch (`UR-F-02`, `SR-F-07`) | Bộ vector lịch của M3; unit test: trùng hoàn toàn/một phần, liền giờ, khác ngày, nhiều buổi | D08 về thời gian nghỉ giữa ca còn Open; tạm chỉ so khoảng giao nhau, chưa áp dụng thời gian nghỉ khác 0 |
| FIFO và giới hạn waitlist (`SR-F-05`, `SR-F-06`) | Test thứ tự `(enqueued_at, id)`, position liên tục, và bất biến I6–I8 | D12 về ceil/floor còn Open; không chốt ngưỡng I8 trước quyết định |
| Tiên quyết của mọi đăng ký ACTIVE | Bất biến I9 dùng engine của M2 làm oracle | D04 còn Open; ghi rõ ngữ nghĩa hiện tại của engine và xác nhận với M2 trước khi xem là cổng cuối |
| OpenAPI đóng băng (`SR-NF-03`) | Sinh `docs/openapi.json`, so sánh snapshot trong CI, test định dạng lỗi | D01–D15 còn Open và các router `/courses`, `/enroll`, `/timetable`, `/waitlist` chưa có trong ứng dụng hiện tại; chỉ chốt baseline sau khi nhóm xác nhận phạm vi hợp đồng |
| Tải (`SR-NF-05`) | Locust bản nháp, ghi số liệu và chạy bất biến sau lượt tải | Tuần 2 chỉ vài chục user; 2.000 user/30 giây là tuần 4. Cần M4 xuất tệp tài khoản riêng và M3 cung cấp luồng API |
| Phân quyền và lỗi API | Test API theo schema lỗi `{detail: {code, message}}` | Cần hợp đồng và API hoàn chỉnh; không đóng băng schema trong khi D01–D15 chưa chốt |

## 4. Bộ bất biến dự kiến

Nguồn định nghĩa là M5 mục 2.2. `I10` chỉ bật nếu nhóm chốt D10. `I8` cần D12 trước khi trở thành cổng CI.

| ID | Kiểm tra | Cách test / điều kiện |
|---|---|---|
| I1 | `enrolled_count <= capacity` | Kiểm tra mọi lớp; DB có CHECK constraint nên không vô hiệu hóa constraint để tạo dữ liệu hỏng |
| I2 | `enrolled_count` bằng số enrollment ACTIVE | Tạo mismatch trong test DB bằng cập nhật hợp lệ trong miền CHECK |
| I3 | Không trùng `(student_id, offering_id)` ACTIVE | Kiểm tra dữ liệu; unique index cũng phải được kiểm chứng riêng |
| I4 | Tổng tín chỉ ACTIVE mỗi sinh viên/kỳ không vượt `max_credits` | Dùng credit của course và term của offering |
| I5 | Lịch ACTIVE của một sinh viên không giao nhau | So các khoảng trong cùng ngày; D08=0 là đề xuất hiện tại, cần ghi rõ nếu nhóm chốt khác |
| I6 | Waitlist position liên tục 1..n theo `(enqueued_at, id)` | Test gap, thứ tự sai và hàng chờ rỗng |
| I7 | Không vừa ACTIVE vừa waitlist cùng sinh viên/lớp | Kiểm tra liên bảng; DB hiện không có constraint liên bảng |
| I8 | Độ dài waitlist không vượt `WAITLIST_MAX_RATIO` | Chờ quyết định D12 về làm tròn; không tự chọn ceil/floor |
| I9 | Mọi enrollment ACTIVE thỏa engine tiên quyết | Dùng engine M2; pairing review D04 và cách xử lý OR branch |
| I10 | Không đăng ký ACTIVE hai lớp khác nhau của cùng môn trong cùng kỳ | Chỉ triển khai/bật nếu nhóm chốt D10 |

**Cách test dữ liệu sai:** ưu tiên unit test trên snapshot dữ liệu thuần để bao phủ lỗi mà CHECK/unique constraint của DB ngăn tạo ra. Test tích hợp xác nhận constraint DB chặn ghi sai. Không tắt constraint, không sửa schema để phục vụ test.

## 5. Rủi ro và biện pháp

| Rủi ro | Mức | Biện pháp trước khi code/merge |
|---|---|---|
| Kỳ vọng test sai vì D04 còn mở; ca #6 trong bảng M2 có hai kết luận | Cao | Không đưa ca #6 vào cổng CI cho tới khi M2 xác nhận bằng văn bản; giữ case và trạng thái pending trong ma trận |
| Sai hợp đồng vì D01–D15 còn Open; snapshot thiếu router | Cao | Chuẩn bị cơ chế snapshot, nhưng chưa đóng băng schema cuối trước khi M1/M2/M3/M4 xác nhận endpoint và response |
| I8/I10 mã hóa sai quy tắc waitlist hoặc cùng môn trong kỳ | Cao | I8 chờ D12; I10 chờ D10; CLI báo các kiểm tra bị hoãn, không gọi chúng là đạt |
| Test invariant không dựng được trạng thái sai do constraint | Trung bình | Pure checker nhận snapshot; test giả lập lỗi ở lớp thuần; kiểm tra constraint DB riêng, không tắt constraint |
| Locust cho kết quả giả vì dùng chung tài khoản hoặc coi lỗi nghiệp vụ là lỗi hệ thống | Cao | Một tài khoản/user; nhận `200/201` và các `409/422` hợp lệ theo kịch bản; chỉ 5xx, timeout và bất biến mới là lỗi hệ thống |
| Thiếu tài khoản/endpoint để chạy Locust | Cao | Chờ M4 xuất account file và M3 cung cấp search/enroll/timetable; chỉ làm cấu trúc/kịch bản kiểm soát trước, không nhúng credential |
| Test flaky hoặc làm CI kéo dài | Trung bình | Không tắt test; gắn marker đúng, không chạy xdist trên DB chung; tìm nguyên nhân gốc trong 48 giờ; không chạy load test trong job CI mặc định |
| GitGuardian lại báo chuỗi giả trong ví dụ | Trung bình | Không thêm mật khẩu mẫu vào code/Locust; dùng tệp local ignored hoặc env; secret scan sau mỗi thay đổi liên quan cấu hình |

## 6. Quy tắc flaky, dữ liệu và CI

- Test fail không được xóa hoặc skip để làm xanh; ghi issue/marker, tìm nguyên nhân gốc trong 48 giờ.
- Unit test không phụ thuộc DB/Redis. Integration dùng fixture `test_session`/`async_client`; concurrency dùng session riêng qua `run_concurrently`.
- Không chạy `pytest-xdist` với cùng `course_reg_test` hoặc Redis DB 1.
- Nghiệm thu tiên quyết dùng dữ liệu đồ thị nhỏ, cố định, không dùng seed 1.001 sinh viên.
- Locust không chạy trên demo DB; tài khoản tải không commit. Mỗi lần chạy lưu số liệu ở vị trí bị ignore.
- Thêm test bất biến và nghiệm thu vào pytest hiện có trước; chỉ sửa workflow sau khi chạy local đạt và kiểm tra diff workflow. Không dùng `hashFiles()` trong job-level `if`.
- OpenAPI check phải báo diff dễ đọc và hướng dẫn cập nhật snapshot trong cùng PR; không tự cập nhật snapshot khi CI chạy.

## 7. Phụ thuộc cần chốt trong tuần

- **M2:** xác nhận toàn bộ 21+5 ca, đặc biệt case #6/D04 và case #16 với OR option có tiên quyết; pairing review.
- **M3:** bộ vector lịch, trạng thái sẵn sàng của enroll/timetable/waitlist, cách đo sau tranh chấp.
- **M4:** account file và seed nhỏ cho Locust; review PR M5 vẫn đang chờ.
- **M1:** xác nhận contract `/courses`, `/timetable`, `/enroll`, `/waitlist` và response/error trước khi snapshot cuối.
- **Nhóm:** quyết định D08, D10, D12, D29; mục tiêu M5 là hơn một nửa 29 điểm D01–D29 có quyết định trước review cuối tuần.

## 8. Cổng hoàn thành tuần 2

- [x] Kế hoạch test có ma trận yêu cầu → phương pháp kiểm chứng và người sở hữu.
- [x] `find_invariant_violations` có CLI read-only, test sạch và test vi phạm; I8/I10 được thể hiện đúng trạng thái quyết định. Đã chạy 11 test mới và toàn bộ 86 backend tests; Ruff và format đều đạt.
- [ ] Bộ nghiệm thu tiên quyết được M2 rà chéo; các ca chưa chốt không được lén đưa thành expected result.
- [ ] Snapshot OpenAPI hiện tại đã khớp API trong container; CI gate đã thêm nhưng cần xác nhận trên GitHub Actions. Đây là baseline tạm của endpoint đang có, chưa phải contract cuối cho tới khi M1/M3 xác nhận phạm vi.
- [ ] Locust draft chạy với vài chục user riêng trên seed nhỏ; không dùng credential trong repo và không báo lỗi nghiệp vụ hợp lệ là lỗi hệ thống.
- [ ] Chuẩn bị review lần 1: tiến độ, rủi ro, D01–D29 còn mở, quyết định cần người chốt.

### Ghi nhận tiến độ hiện tại (2026-11-06)

- Test lõi `backend/tests/test_prerequisite_engine.py` đã có 20 ca đồ thị và 5 ca kiểm tra thêm cạnh; pytest tổng đã chạy chúng. Không nhân bản bộ test của M2.
- Thêm `backend/tests/test_prerequisite_acceptance.py` cho ca API #21 (môn không tồn tại → 404 `NOT_FOUND`); test riêng và toàn bộ backend suite đã chạy đạt sau khi thêm.
- Ca #6 đang theo ngữ nghĩa hiện tại của engine (môn đã hoàn tất là đủ), nhưng D04 vẫn Open nên M2 cần xác nhận trước khi coi kết quả là hợp đồng đã chốt.
- Ca #16 trong ma trận yêu cầu đánh giá `can_take_now` của từng lựa chọn OR; test lõi hiện chỉ kiểm tra nhóm OR chưa thỏa. Phần này thuộc thay đổi engine/explain của M2, cần M2 hoàn thành và rà cùng M5.
- API hiện có chưa chứa các endpoint courses/enroll/timetable/waitlist. Snapshot hiện tại là baseline của API đang có; kịch bản Locust đầy đủ vẫn chờ M3/M4 và phạm vi contract cuối chờ M1/M3.
- `backend/app/tools/openapi_snapshot.py` đã sinh snapshot ổn định; `--check` đã khớp cục bộ. Compose gắn `docs/` read-only vào API. CI gate vừa được thêm, chờ GitHub Actions xác nhận.
