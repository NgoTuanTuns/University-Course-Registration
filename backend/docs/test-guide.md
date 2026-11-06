# Hướng dẫn kiểm thử backend

- Đặt file kiểm thử là test_*.py trong backend/tests/.
- Dùng marker unit, integration, concurrency, stress, slow hoặc e2e trong pyproject.toml.
- Dùng các factory make_student, make_course, make_offering, add_prereq và complete để tạo dữ liệu.
- Kiểm thử API dùng fixture async_client; kiểm thử tranh chấp dùng run_concurrently, mỗi tác vụ nhận session riêng.
- Test chạy trên course_reg_test và Redis database 1. Không trỏ test vào database demo.
- Không chạy pytest-xdist trên cùng database vì các test dùng chung dữ liệu và Redis test DB.
- Unit test không cần gọi database; chỉ test tích hợp/tranh chấp mới dùng fixture dịch vụ.
- Khi test thất bại không được tắt test; ghi nhận nguyên nhân, đánh dấu flaky nếu cần và sửa trong 48 giờ.
