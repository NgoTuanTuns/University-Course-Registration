# Báo cáo Rà soát Bảo mật Hệ thống theo OWASP Top 10 (M4 — Tuần 5)

**Đề tài:** Hệ thống Đăng ký Học phần & Kiểm tra Điều kiện Tiên quyết  
**Vai trò phụ trách:** M4 (Database & Security Engineer)  
**Ngày thực hiện:** 09/11/2026  
**Phiên bản hệ thống:** 1.0.0 (Tuần 5)  
**Tiêu chuẩn rà soát:** OWASP Top 10 (2021) & Quy ước bảo mật của nhóm (SR-F-08, UR-NF-04, UR-NF-05, UR-NF-08)

---

## 1. Tóm tắt kết quả rà soát (Executive Summary)

Đợt rà soát bảo mật Tuần 5 tập trung đánh giá toàn diện mã nguồn backend (FastAPI), cơ sở dữ liệu (PostgreSQL), bộ nhớ đệm (Redis), máy chủ trung gian (Nginx reverse proxy) và giao tiếp frontend (Vite/React).

### Bảng kết quả tổng hợp 10 hạng mục OWASP:

| Mã | Hạng mục OWASP | Hiện trạng | Kết luận | Biện pháp kỹ thuật áp dụng |
|---|---|---|---|---|
| **A01** | **Broken Access Control** (Kiểm soát truy cập) | Đã kiểm tra & gia cố | **ĐẠT** | RBAC 2 vai trò (`student`, `admin`), chặn IDOR khi hủy đăng ký/rời hàng chờ, chặn sinh viên hỏi tiên quyết cho người khác. |
| **A02** | **Cryptographic Failures** (Lỗ hổng mật mã) | Đã kiểm tra | **ĐẠT** | Băm mật khẩu bcrypt (cost=12) chạy trong thread pool, JWT HS256, từ chối khởi động ở `APP_ENV=prod` nếu bí mật yếu (<32 ký tự). |
| **A03** | **Injection** (Tiêm lệnh / SQL Injection) | Đã sửa & gia cố | **ĐẠT** | 100% truy vấn qua SQLAlchemy ORM/Parameterized SQL, thoát ký tự đặc biệt (`\`, `%`, `_`) trong tìm kiếm `ILIKE`. |
| **A04** | **Insecure Design** (Thiết kế không an toàn) | Đã kiểm tra | **ĐẠT** | Chống dò email bằng so sánh mật khẩu giả thời gian hằng định, toàn bộ luật nghiệp vụ (sức chứa, tín chỉ, chu trình DAG) kiểm soát ở server. |
| **A05** | **Security Misconfiguration** (Cấu hình sai) | Đã sửa & bổ sung | **ĐẠT** | Whitelist `CORS_ORIGINS`, thêm 4 tiêu đề bảo mật Nginx (`X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`, `Referrer-Policy`). |
| **A06** | **Vulnerable & Outdated Components** | Đã kiểm tra | **ĐẠT** | Khóa cứng phiên bản thư viện (`requirements.txt`, `package-lock.json`), không có lỗ hổng mức Critical trong phụ thuộc trực tiếp. |
| **A07** | **Identification & Auth Failures** | Đã kiểm tra | **ĐẠT** | Rate-limit nghiêm ngặt đăng nhập (5 lần/phút), xoay vòng refresh token (Single-use), phát hiện dùng lại (Reuse Detection) thu hồi toàn bộ phiên. |
| **A08** | **Software & Data Integrity Failures** | Đã kiểm tra | **ĐẠT** | CI tự động kiểm tra cú pháp, format, migrations, snapshot hợp đồng OpenAPI, kiểm tra bất biến toàn vẹn dữ liệu. |
| **A09** | **Security Logging & Monitoring** | Đã kiểm tra | **ĐẠT** | Ghi log có cấu trúc các sự kiện bất thường (đăng nhập sai, 403, 429, reuse token) mà tuyệt đối không chứa mật khẩu hay token. |
| **A10** | **Server-Side Request Forgery (SSRF)** | Đã đánh giá | **N/A** | Hệ thống không thực hiện bất kỳ lệnh gọi HTTP nào ra ngoài dựa trên URL người dùng cung cấp. |

---

## 2. Chi tiết đánh giá và bằng chứng kỹ thuật

### A01: Broken Access Control (Kiểm soát truy cập)
- **Phân quyền dựa trên vai trò (RBAC):**
  - Hệ thống định nghĩa chính xác 2 vai trò: `student` và `admin`. Ràng buộc này được bảo vệ kép từ tầng Database (`CHECK (role IN ('student', 'admin'))`) đến tầng mã nguồn Pydantic/FastAPI.
  - Mọi route quản trị `/api/v1/admin/*` (học phần và tiên quyết) được đặt dưới dependency `require_role("admin")`. Sinh viên truy cập lập tức nhận HTTP `403 FORBIDDEN`.
- **Phòng chống tấn công tham chiếu trực tiếp đối tượng không an toàn (IDOR):**
  - `DELETE /api/v1/enroll/{id}`: Truy vấn lọc bắt buộc `Enrollment.id == enrollment_id, Enrollment.student_id == student_id`. Nếu sinh viên A cố hủy môn của sinh viên B, API trả về `404 NOT_FOUND` thay vì `403` để không làm lộ sự tồn tại của tài nguyên.
  - `DELETE /api/v1/waitlist/{id}`: Tương tự, lọc `Waitlist.id == waitlist_id, Waitlist.student_id == student_id`.
  - `GET /api/v1/prerequisites/check` & `POST /api/v1/prerequisites/explain`: Sinh viên chỉ được hỏi cho chính mình. Nếu truyền `student_id` của người khác mà không phải admin $\rightarrow$ trả `403 FORBIDDEN`.

### A02: Cryptographic Failures (Lỗ hổng mật mã)
- **Băm mật khẩu:**
  - Mật khẩu được băm bằng thuật toán `bcrypt` với hệ số làm việc `BCRYPT_ROUNDS = 12`.
  - Hàm so sánh `verify_password` được đưa vào `run_in_threadpool` của Starlette, đảm bảo tác vụ tiêu tốn CPU này không chiếm dụng hay làm nghẽn Event Loop đơn luồng của FastAPI.
- **Cấu hình khóa bí mật JWT:**
  - Khóa ký JWT được quản lý qua biến `JWT_SECRET`.
  - Kiểm tra nghiêm ngặt tại `tokens.get_secret()`: Khi `APP_ENV=prod`, hệ thống sẽ từ chối khởi động nếu `JWT_SECRET` là chuỗi mặc định mẫu hoặc có độ dài nhỏ hơn 32 ký tự.
- **Bảo mật mã nguồn:**
  - Không lưu mật khẩu hoặc token thật trong Git repository. CI workflow có bước quét bí mật độc lập `Secret scan` (`trufflehog`/`detect-secrets`).

### A03: Injection (Tiêm mã lệnh & SQL Injection)
- **Parameterized SQL:**
  - Toàn bộ các thao tác dữ liệu đều sử dụng SQLAlchemy Core / ORM async với câu lệnh tham số hóa (Parameterized queries), hoàn toàn không nối chuỗi SQL thủ công.
- **Thoát ký tự đại diện trong tìm kiếm `ILIKE`:**
  - Trong `course_service.py` và `enrollment_queries.py`, các ký tự đại diện nhạy cảm của SQL `ILIKE` gồm `%` (khớp chuỗi bất kỳ), `_` (khớp ký tự đơn) và `\` (ký tự escape) đều được tự động escape trước khi đưa vào câu lệnh:
    ```python
    clean_q = q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    Course.name.ilike(f"%{clean_q}%", escape="\\")
    ```
  - Điều này ngăn chặn việc người dùng nhập chuỗi `%` làm quét cạn bảng dữ liệu hoặc làm sai lệch kết quả phân trang.

### A04: Insecure Design (Thiết kế không an toàn)
- **Chống dò tài khoản (Enumeration Prevention):**
  - Khi đăng nhập sai mật khẩu hoặc sai email, API trả về cùng một mã lỗi: `401 UNAUTHENTICATED` với thông điệp chung: *"Sai email hoặc mật khẩu"*.
  - Trong trường hợp email không tồn tại trong DB, `auth_service.authenticate()` vẫn thực hiện một phép kiểm tra mật khẩu giả lập (`_get_dummy_hash()`) để thời gian xử lý phản hồi là tương đương nhau (Timing Attack Mitigation).
- **Quy tắc nghiệp vụ được thực thi tuyệt đối ở Backend:**
  - Sĩ số lớp học phần, hạn mức tín chỉ tối đa (mặc định 25), kiểm tra điều kiện tiên quyết, khóa đồng thời và chống tạo chu trình trong DAG đều do backend quyết định; không tin tưởng bất kỳ dữ liệu nào phía client.

### A05: Security Misconfiguration (Cấu hình sai)
- **CORS Whitelist:**
  - `CORSMiddleware` đọc danh sách domain cho phép từ biến `CORS_ORIGINS`. Không sử dụng wildcard `*` khi cho phép credentials.
- **Tiêu đề bảo mật Nginx (Security Headers):**
  - Nginx reverse proxy được bổ sung 4 tiêu đề bảo mật chuẩn OWASP:
    + `X-Content-Type-Options: nosniff`: Ngăn MIME-type sniffing.
    + `X-Frame-Options: DENY`: Chống tấn công Clickjacking.
    + `X-XSS-Protection: 1; mode=block`: Bật bộ lọc XSS của trình duyệt.
    + `Referrer-Policy: strict-origin-when-cross-origin`: Bảo vệ thông tin rò rỉ qua Referer header.

### A06: Vulnerable and Outdated Components (Thành phần lỗi thời)
- Tất cả thư viện Python (`requirements.txt`) và JavaScript (`package-lock.json`) đều được cố định phiên bản (pinned versions).
- Các gói phụ thuộc cốt lõi: FastAPI 0.115+, Pydantic 2.10+, SQLAlchemy 2.0.36+, Asyncpg 0.30+, Redis-py 5.2+, React 18.3+, Vite 6.0+.

### A07: Identification and Authentication Failures (Xác thực và phiên)
- **Giới hạn tần suất đăng nhập (Brute Force Protection):**
  - Endpoint `/api/v1/auth/login` áp dụng rate-limit nghiêm ngặt: 5 lần/phút cho mỗi cặp `(IP, email)`. Vượt ngưỡng trả về `429 RATE_LIMITED` kèm header `Retry-After`.
- **Cơ chế xoay vòng Refresh Token (Token Rotation):**
  - Refresh token chỉ có giá trị sử dụng **1 lần duy nhất**. Khi gọi `/api/v1/auth/refresh`, refresh token cũ bị tiêu thụ và cấp mới 1 cặp token.
- **Phát hiện tái sử dụng Token (Token Reuse Detection):**
  - Nếu một refresh token đã dùng bị gửi lại, hệ thống xác định có khả năng rò rỉ token và **lập tức thu hồi TOÀN BỘ phiên đăng nhập** của sinh viên đó trong Redis.
- **Không lộ mật khẩu:**
  - Cột `password_hash` không bao giờ xuất hiện trong bất kỳ Pydantic response schema nào.

### A08: Software and Data Integrity Failures (Toàn vẹn phần mềm & dữ liệu)
- Toàn bộ thay đổi cơ sở dữ liệu đều đi qua migration Alembic có phiên bản.
- OpenAPI contract snapshot được kiểm tra tự động (`openapi_snapshot --check`) nhằm ngăn ngừa việc sửa API tùy tiện gây vỡ hợp đồng với frontend.
- Bộ kiểm tra bất biến dữ liệu `app.tools.invariants` xác thực 7 bất biến cốt lõi về sĩ số và đăng ký.

### A09: Security Logging and Monitoring (Ghi log và giám sát)
- Ghi log các sự kiện bảo mật: đăng nhập thất bại, truy cập trái phép 403, vượt giới hạn tần suất 429, phát hiện dùng lại token.
- Bộ định dạng log loại trừ hoàn toàn các trường nhạy cảm như `password`, `password_hash`, `token`, `secret`.

### A10: Server-Side Request Forgery (SSRF)
- Hệ thống không có tính năng tải ảnh, webhook hay gọi URL từ tham số người dùng $\rightarrow$ Đánh giá: **Không áp dụng (N/A)**.

---

## 3. Danh sách các bài kiểm thử tự động bảo mật

Các kịch bản trên được kiểm chứng liên tục qua bộ kiểm thử `backend/tests/test_security_audit.py`:
1. `test_security_idor_cancel_enrollment`: Sinh viên A không thể hủy đăng ký của sinh viên B (nhận 404).
2. `test_security_idor_leave_waitlist`: Sinh viên A không thể rời hàng chờ của sinh viên B (nhận 404).
3. `test_security_rbac_admin_routes`: Sinh viên gọi route admin bị từ chối 403 FORBIDDEN.
4. `test_security_password_hash_never_exposed`: Response đăng nhập không chứa trường `password_hash`.
5. `test_security_sql_wildcard_escaping`: Tìm kiếm với ký tự `%`, `_` được escape an toàn.
6. `test_security_login_rate_limiting`: Gọi đăng nhập quá 5 lần/phút trả về HTTP 429 + Retry-After.
7. `test_security_refresh_token_reuse_detection`: Gửi lại refresh token cũ kích hoạt thu hồi toàn bộ phiên.
