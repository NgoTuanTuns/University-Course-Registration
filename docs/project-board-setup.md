# Thiết lập quản trị dự án trên GitHub

Tài liệu này ghi cấu hình thủ công cần áp dụng trong repository. Chưa có thay đổi nào được thực hiện trên GitHub Settings hoặc Projects từ nhánh code.

## GitHub Projects

Tạo bảng dự án với cột:

- Todo
- Doing
- Review
- Done
- Blocked

Tạo một issue cho mỗi sản phẩm bàn giao hàng tuần của M1–M5 theo các file trong chitietcongviec/. Gắn owner, tuần, loại và mức độ ưu tiên.

## Labels

Tạo các nhãn theo quy ước M5:

- owner:M1, owner:M2, owner:M3, owner:M4, owner:M5
- type:bug, type:task, type:decision
- severity:blocker, severity:major, severity:minor
- week:1, week:2, week:3, week:4, week:5, week:6, week:7

Thêm contract-change cho PR thay đổi hợp đồng API.

## Bảo vệ main

Trong Settings > Rules (hoặc Branch protection rules), cấu hình cho main:

- Yêu cầu Pull Request; không push trực tiếp.
- Yêu cầu CI thành công.
- Yêu cầu ít nhất một lượt review.
- Không cho gộp khi có review thay đổi còn mở.

## Vòng review

- M4 review PR của M5.
- M5 review PR của M1.
- Mỗi PR cần reviewer đọc và chạy thử trước khi gộp.
