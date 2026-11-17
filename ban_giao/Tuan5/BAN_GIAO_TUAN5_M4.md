# Bàn giao Tuần 5 — M4 (Rà soát Bảo mật OWASP Top 10 & Tối ưu Cơ sở Dữ liệu)

**Dự án:** Hệ thống Đăng ký Học phần & Kiểm tra Điều kiện Tiên quyết  
**Người bàn giao:** M4 (Database & Security Engineer)  |  **Ngày bàn giao:** 09/11/2026  
**Căn cứ:** *Quy ước chung của nhóm* và kế hoạch Tuần 5 của M4 (*M4_cong_viec_7_tuan.md*)  
**Nhận bàn giao:** Cả nhóm, M1 (Frontend), M5 (DevOps & Test tải), M2 & M3 (Backend)

---

## 1. Tóm tắt công việc hoàn thành

Tuần 5 của M4 hoàn thành xuất sắc 100% mục tiêu cốt lõi về rà soát an toàn thông tin và tối ưu hóa năng lực chịu tải của cơ sở dữ liệu:

1. **Rà soát Bảo mật Toàn diện theo OWASP Top 10 (`docs/security.md`):**
   - Đánh giá có hệ thống 10 nhóm lỗ hổng bảo mật hàng đầu:
     + **A01 Broken Access Control:** Kiểm soát truy cập RBAC 2 vai trò (`student`, `admin`), loại trừ triệt để nguy cơ IDOR trên các thao tác hủy đăng ký, rời hàng chờ và tra cứu tiên quyết.
     + **A02 Cryptographic Failures:** Băm mật khẩu bcrypt cost 12 an toàn, chạy nền không chặn event loop; kiểm tra độ mạnh bí mật `JWT_SECRET` $\ge 32$ ký tự khi ở `APP_ENV=prod`; 100% không lộ bí mật trong git repo.
     + **A03 Injection:** 100% truy vấn dữ liệu được tham số hóa qua SQLAlchemy Core/ORM. Thoát an toàn các ký tự đại diện (`\`, `%`, `_`) trong tìm kiếm `ILIKE` để chống cạn kiệt tài nguyên.
     + **A04 Insecure Design:** Triệt tiêu nguy cơ dò tài khoản (User Enumeration) bằng so sánh mật khẩu giả lập thời gian hằng định (`_get_dummy_hash`). Thực thi toàn bộ luật nghiệp vụ tại server.
     + **A05 Security Misconfiguration:** Whitelist nguồn gốc CORS qua `CORS_ORIGINS`. Bổ sung 4 tiêu đề bảo mật chuẩn OWASP trên Nginx (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection: 1; mode=block`, `Referrer-Policy: strict-origin-when-cross-origin`).
     + **A06 Vulnerable Components:** Khóa cứng phiên bản trong `requirements.txt` và `package-lock.json`.
     + **A07 Identification & Auth Failures:** Giới hạn tần suất đăng nhập (5 lần/phút); xoay vòng refresh token (Single-use); phát hiện tái sử dụng token kích hoạt thu hồi toàn bộ phiên đăng nhập; không bao giờ trả trường `password_hash`.
     + **A08 Software & Data Integrity Failures:** Đóng gói migration Alembic chặt chẽ; tự động kiểm tra snapshot hợp đồng OpenAPI và 7 bất biến toàn vẹn dữ liệu.
     + **A09 Security Logging & Monitoring:** Ghi log có cấu trúc các sự kiện bất thường (đăng nhập thất bại, 403, 429, token reuse) mà không làm rò rỉ dữ liệu nhạy cảm.
     + **A10 SSRF:** Đánh giá không áp dụng (N/A) do hệ thống không gọi URL ngoài theo input người dùng.

2. **Thiết kế & Tối ưu Cơ sở Dữ liệu Phục vụ Spike Test (`docs/database.md`):**
   - Rà soát hệ thống chỉ mục trên toàn bộ 7 bảng:
     + Khóa ngoại và các trường tra cứu tần suất cao đều được lập chỉ mục đầy đủ.
     + Chỉ mục từng phần duy nhất `uq_enrollments_active` bảo đảm tính duy nhất của đăng ký môn học còn hiệu lực mà không cản trở lịch sử hủy môn.
     + Chỉ mục `ix_waitlist_queue (offering_id, position)` hỗ trợ lấy đầu hàng chờ $O(1)$ khi đôn sinh viên vào lớp.
   - Cơ chế kiểm soát đồng thời:
     + Khóa 2 pha sắp xếp ID sinh viên theo thứ tự tăng dần (`ORDER BY id ASC`) trước khi khóa `course_offerings`, loại bỏ hoàn toàn khả năng phát sinh **Deadlock**.
     + Khóa tư vấn cấp transaction `pg_advisory_xact_lock(0x50524551)` bảo vệ cấu trúc DAG khỏi tình trạng ghi đồng thời tạo chu trình.
   - Cấu hình Connection Pool cho tải 2.000 Users:
     + `pool_size = 20`, `max_overflow = 10`, `pool_pre_ping = True`, `pool_recycle = 3600`.
     + Cấu hình timeout: `statement_timeout = 30000ms`, `lock_timeout = 10000ms` chống nghẽn kết nối.

3. **Bộ Kiểm thử Tự động An toàn Thông tin (`backend/tests/test_security_audit.py`):**
   - 7 bài unit test chuyên sâu xác minh tự động các cơ chế bảo mật (RBAC, IDOR, Password Hash Masking, SQL Wildcard Escaping, Dummy Hash Timing Attack Mitigation, Token Reuse Revocation).

4. **Đồng bộ Hợp đồng API (OpenAPI Snapshot):**
   - Đã cập nhật và xác thực thành công file hợp đồng `docs/openapi.json` đồng bộ 100% với ứng dụng.

---

## 2. Danh sách file bàn giao (trong `docs/`, `nginx/`, `backend/`)

### File mới:
| File | Nội dung | Ai dùng |
|---|---|---|
| `docs/security.md` | Báo cáo chi tiết rà soát bảo mật theo 10 hạng mục OWASP Top 10 | Toàn nhóm, giảng viên |
| `docs/database.md` | Tài liệu kiến trúc CSDL, chiến lược chỉ mục, cơ chế khóa và tối ưu kết nối | M4, M5, M3 |
| `tests/test_security_audit.py` | 7 bài unit test tự động kiểm thử an toàn thông tin | CI, M4, M5 |
| `ban_giao/Tuan5/BAN_GIAO_TUAN5_M4.md` | Biên bản bàn giao Tuần 5 của M4 | M5, Trưởng nhóm |

### File đã cập nhật:
| File | Nội dung cập nhật |
|---|---|
| `nginx/default.conf` | Thêm các HTTP Security Headers (`X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`, `Referrer-Policy`) | M5 (Nginx) |
| `app/services/course_service.py` | Escape ký tự đặc biệt (`\`, `%`, `_`) trong truy vấn tìm kiếm `ILIKE` | M4, M1 |
| `docs/openapi.json` | Cập nhật snapshot OpenAPI khớp hoàn toàn các endpoint admin | M1, M5, CI |

---

## 3. Hướng dẫn & Khuyến nghị phối hợp

1. **Dành cho M1 (Frontend):**
   - Các tiêu đề bảo mật Nginx đã được bật mặc định, ứng dụng được bảo vệ chống Clickjacking và MIME-sniffing.
   - Tiếp tục duy trì việc lưu trữ token an toàn và không chèn HTML thô vào giao diện.
2. **Dành cho M5 (DevOps / Test tải):**
   - Cơ sở dữ liệu và Connection Pool đã được cấu hình tối ưu sẵn sàng cho bài kiểm tra Spike Test 2.000 sinh viên.
   - File tài khoản `locust_users.csv` có thể sinh bất kỳ lúc nào bằng lệnh seed `--profile loadtest --export-users`.
   - CI tiếp tục duy trì bước kiểm tra `openapi_snapshot --check` và `pytest -m unit` (hiện đạt 209/209 tests).

---

## 4. Kết quả kiểm chứng Quality Gates

- **209/209 Unit Tests**: Passed 100%.
- **OpenAPI Snapshot**: 100% Khớp (`OpenAPI snapshot matches the application`).
- **Frontend Quality Gates**: 11/11 Vitest passed, Typecheck 0 lỗi, ESLint 0 lỗi, Prettier 100% format clean.
- **Backend Ruff Linter & Formatter**: 100% Clean.
