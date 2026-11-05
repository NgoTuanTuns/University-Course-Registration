## Mô tả

<!-- Nêu ngắn gọn thay đổi và lý do. -->

## Checklist trước khi gộp

- [ ] Chạy được bằng docker compose up --build.
- [ ] Đã format code bằng Ruff / Prettier.
- [ ] Có test cho logic mới hoặc giải thích vì sao không áp dụng.
- [ ] Không còn print / console.log thử nghiệm, mật khẩu thật hoặc file .env.
- [ ] Nếu đổi bảng, đã có Alembic migration và báo cả nhóm.
- [ ] Nếu thêm biến môi trường, đã cập nhật .env.example.
- [ ] Một bạn khác đã đọc qua và chạy thử.

## Hợp đồng và phối hợp

- [ ] PR có thay đổi hợp đồng API: Có / Không.
- [ ] Nếu có, đã cập nhật snapshot OpenAPI và báo M1.
- [ ] Người review theo vòng: M4 review M5 / M5 review M1 / Khác: ghi tên.
