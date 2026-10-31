# Prerequisite Engine (M2) — thiết kế Tuần 1

## Mô hình
DAG, cạnh `X -> Y` = "X cần Y". Bảng `prerequisites`: `AND` (group_no=0) bắt buộc; `OR` (group_no>=1) cùng (course, group_no) là 1 nhóm, chỉ cần 1 môn.
Đạt khi: mọi môn AND đã có trong `completed_courses` **và** mỗi nhóm OR có >= 1 môn đã có.

## Quyết định bắc cầu (cần cả nhóm xác nhận)
Chọn (a): *đã học nghĩa là đã đủ* — môn có trong `completed_courses` thì không xét lại tổ tiên của nó.
Môn chưa học thì mở rộng tiếp tiên quyết để liệt kê đủ chuỗi cần học. Nếu nhóm chọn (b, nghiêm ngặt) chỉ đổi hàm `evaluate` và ca #6 trong bảng nghiệm thu.

## Thuật toán
- `evaluate`: BFS bằng hàng đợi + tập `seen` (memoization) -> O(V + E), môn kim cương chỉ xử lý 1 lần, không đệ quy.
- `find_cycle`: DFS 3 màu bằng vòng lặp, trả đường đi chu trình. Cạnh OR cũng được tính khi tìm chu trình (chặt hơn, an toàn).
- `would_create_cycle(course, prereq)`: có vòng khi `course` tới được từ `prereq`.
- `assert_acyclic(edges)`: cho seed/import của M4.

## Giao diện
`check_eligibility(session, student_id, course_id) -> EligibilityResult` (chỉ đọc, dùng chung session của M3; `missing_courses` là mã môn).
`GET /api/v1/prerequisites/check?course_id=` -> 200 kể cả khi `eligible=false`; 404 `NOT_FOUND`; 403 `FORBIDDEN`.

## Chưa làm (Tuần 2+)
`can_take_now`, `explain`, `suggested_order`, cache Redis, benchmark.
