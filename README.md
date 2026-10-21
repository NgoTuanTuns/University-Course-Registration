# M1 — Frontend Web Developer
## Hệ thống Đăng ký Học phần & Kiểm tra Điều kiện Tiên quyết

> **Phạm vi tài liệu:** README này đối chiếu mã nguồn thực tế có trong `M1(1).zip` với tài liệu **“M1 — Frontend Web Developer: Công việc chi tiết 7 tuần coding”** được cung cấp. Trạng thái bên dưới chỉ phản ánh những gì có thể xác nhận từ mã nguồn trong ZIP, không khẳng định thay cho tiến độ của các thành viên khác.

## 1. Tổng quan dự án

M1 phụ trách xây dựng ứng dụng web frontend cho hệ thống đăng ký học phần. Phiên bản hiện tại là **bản demo frontend chạy bằng dữ liệu mock**, tập trung vào trải nghiệm sinh viên, thời khóa biểu, mô phỏng đăng ký và một phần giao diện quản trị.

Các màn hình và hành vi demo giúp nhóm có cơ sở thảo luận giao diện, luồng nghiệp vụ và hợp đồng API. Tuy nhiên, dữ liệu và quy tắc trong frontend **chưa được xem là quy định nghiệp vụ chính thức của cả nhóm** nếu chưa được thống nhất với các thành viên phụ trách nghiệp vụ/backend.

### Trạng thái tổng quát

- **Đã có:** SPA React chạy được; điều hướng; layout sinh viên/quản trị; dashboard; tra cứu học phần; thời khóa biểu dạng lưới; xem trước lớp và cảnh báo trùng lịch phía client; màn hình đăng ký, tiên quyết, danh sách chờ; CRUD học phần bằng dữ liệu mock; một số unit test.
- **Còn thiếu đáng kể:** tích hợp API backend thật; xác thực và phân quyền có hiệu lực ở server; quản trị điều kiện tiên quyết với nhóm `AND/OR` và chống tạo chu trình; kiểm thử E2E; triển khai production qua Docker/Nginx; bằng chứng kiểm thử tải và tài liệu/demo bảo vệ.
- **Không được hiểu nhầm:** việc một nút hoặc màn hình hoạt động trong bản demo không có nghĩa giao dịch đã được lưu vào cơ sở dữ liệu dùng chung hay được backend xác thực.

## 2. Công nghệ và yêu cầu môi trường

Các phiên bản dưới đây lấy từ `package.json` của ZIP:

| Thành phần | Công nghệ |
|---|---|
| UI | React `^19.3.1` |
| Ngôn ngữ | TypeScript `~6.0.3` |
| Công cụ phát triển/build | Vite `^8.3.4` |
| Điều hướng | React Router DOM `^7.18.4` |
| CSS | Tailwind CSS `^4.3.3`, `@tailwindcss/vite` |
| Icon | `lucide-react` |
| Kiểm tra code | ESLint |
| Unit test | Node.js built-in test runner, chạy test TypeScript bằng `--experimental-strip-types` |

**Cần cài:**
- Node.js **22.12 trở lên** (khuyến nghị dùng bản LTS tương thích với Vite 8).
- npm đi kèm Node.js.
- Trình duyệt hiện đại như Chrome hoặc Edge.

Kiểm tra môi trường sau khi cài Node.js:

```bash
node -v
npm -v
```

Nếu terminal báo không tìm thấy `node` hoặc `npm`, hãy cài Node.js, mở terminal mới rồi chạy lại hai lệnh trên.

## 3. Tiến độ đối chiếu với kế hoạch coding 7 tuần

Tài liệu kế hoạch chia 7 tuần coding, tương ứng tuần 3–9 của kế hoạch tổng. Bảng này đánh giá theo **sản phẩm có thể xác nhận trong ZIP**, không dựa trên dự định hoặc trao đổi miệng.

| Tuần coding | Trọng tâm theo kế hoạch | Đánh giá trong ZIP | Căn cứ / phần còn thiếu |
|---|---|---|---|
| **1** | Khung dự án, mock API/MSW, đăng nhập, tra cứu học phần | **Hoàn thành một phần** | Đã có Vite/React/TypeScript, router, layout, trang login và trang tra cứu học phần. Dữ liệu tra cứu là mock. Chưa thấy MSW được cấu hình và các handler theo hợp đồng API; chưa có lớp HTTP hoàn chỉnh xử lý token, chuyển đổi `snake_case`/`camelCase`, map đầy đủ 9 mã lỗi, debounce + hủy request, đồng bộ đầy đủ bộ lọc lên URL như kế hoạch. |
| **2** | Lưới thời khóa biểu và phát hiện xung đột tức thì | **Phần giao diện/logic chính đã có** | Có `TimetableGrid`, tiện ích xử lý lịch, dữ liệu mock, xem trước lớp và unit test lịch. Cần đối chiếu thêm các tiêu chí chi tiết trong kế hoạch: hiển thị nhiều block chồng nhau, cấu hình khung giờ, tooltip/khả năng truy cập, toàn bộ ca biên và tiêu chí 0 dương tính giả/âm tính giả. Chưa có bằng chứng kiểm thử cùng backend. |
| **3** | API thật, đăng ký/hủy end-to-end, giải thích tiên quyết | **Mới ở mức demo frontend** | Có màn hình đăng ký, dữ liệu/logic mock và trang giải thích tiên quyết. Chưa có bằng chứng luồng chạy end-to-end với backend thật; chưa xác nhận refresh token, xử lý nhiều request refresh đồng thời, idempotency key, đầy đủ mã lỗi API hoặc kiểm thử tích hợp. |
| **4** | Waitlist, dashboard tín chỉ, bắt đầu admin học phần | **Giao diện demo phần lớn đã có; backend chưa có** | Có trang danh sách chờ, tiện ích waitlist, dashboard/thanh tín chỉ và CRUD học phần phía frontend. Chưa xác nhận hàng chờ được backend quản lý, tự động đôn, cập nhật theo chu kỳ hoặc thông báo đôn thất bại; quyền admin và validation server chưa được tích hợp. |
| **5** | Admin tiên quyết (DAG), UX theo test tải, tối ưu hiệu năng | **Chưa hoàn thành** | `/admin/prerequisites` hiện là trang giữ chỗ (`PlaceholderPage`). Chưa có giao diện chỉnh nhóm `AND/OR`, `group_no`, thêm/xóa quan hệ và phát hiện/ngăn chu trình. ZIP không cung cấp báo cáo Locust, số liệu hiệu năng, xử lý `429`/`Retry-After` hoặc bằng chứng tối ưu theo test tải. |
| **6** | Đóng băng tính năng, E2E smoke, production qua Nginx/Docker | **Chưa hoàn thành theo bằng chứng hiện có** | Có script lint/test/build và các unit test. Chưa thấy bộ E2E smoke/Playwright, cấu hình Docker Compose/Nginx hoặc quy trình kiểm chứng build production qua Nginx trong mã nguồn được cung cấp. |
| **7** | Demo bảo vệ, slide frontend, diễn tập | **Chưa thể xác nhận từ ZIP** | ZIP không thể hiện kịch bản demo, slide, video dự phòng hay biên bản diễn tập. Đây có thể là tài liệu ngoài mã nguồn nên cần kiểm tra riêng. |

### Kết luận tiến độ

Có thể mô tả trung thực tiến độ hiện tại là: **đã xây dựng được bản demo frontend có nhiều luồng chính và một số unit test; chưa phải frontend đã tích hợp hoàn chỉnh theo hợp đồng API của nhóm**. Tuần 1–4 có các sản phẩm giao diện/logic mock đáng kể, Tuần 5 còn thiếu phần quản trị tiên quyết, Tuần 6 chưa có bằng chứng E2E và triển khai production, Tuần 7 chưa thể xác nhận từ ZIP.

Không nên ghi “hoàn thành 4/7 tuần” như một tỷ lệ chính thức, vì mỗi tuần có nhiều tiêu chí nghiệm thu và một số tiêu chí chỉ hoàn thành ở mức giao diện mock.

## 4. Chức năng hiện có và đường dẫn

| Khu vực | URL | Trạng thái trong bản ZIP |
|---|---|---|
| Trang mặc định | `/` | Chuyển hướng tới `/student/dashboard` |
| Đăng nhập | `/login` | Có giao diện demo; không phải xác thực backend |
| Dashboard sinh viên | `/student/dashboard` | Thống kê và tín chỉ từ dữ liệu mock |
| Tra cứu học phần | `/student/courses` | Danh sách, bộ lọc và thao tác demo |
| Thời khóa biểu | `/student/timetable` | Lưới tuần, dữ liệu lịch mock, xem trước/cảnh báo xung đột phía client |
| Điều kiện tiên quyết phía sinh viên | `/student/prerequisites` | Minh họa kiểm tra/giải thích bằng dữ liệu mock |
| Đăng ký học phần | `/student/enrollment` | Luồng đăng ký/hủy demo |
| Danh sách chờ | `/student/waitlist` | Giao diện/logic demo |
| Quản trị học phần | `/admin/courses` | Tìm kiếm và CRUD trên dữ liệu mock phía frontend |
| Quản trị tiên quyết | `/admin/prerequisites` | Trang giữ chỗ, chưa có nghiệp vụ quản trị hoàn chỉnh |
| Không tìm thấy trang | Các URL không khớp | Trang 404 |

### Các phần kỹ thuật nhìn thấy trong mã nguồn

- Layout riêng cho sinh viên và quản trị viên; sidebar, header và chuyển đổi sáng/tối.
- Tổ chức code theo `pages`, `layouts`, `components`, `features`, `api`, `types`, `mocks` và `tests`.
- Dữ liệu mock học phần và một số trạng thái được lưu trong `localStorage`; lớp xem trước TKB dùng `sessionStorage`.
- Unit test hiện có cho tiện ích thời khóa biểu, dashboard, điều kiện tiên quyết mock, lưu trữ học phần và tiện ích danh sách chờ.
- Script dự án có `dev`, `lint`, `test`, `test:timetable`, `build` và `preview`.

## 5. Cách cài đặt và chạy website

### Bước 1 — Giải nén dự án

Giải nén `M1(1).zip`. Mở terminal tại thư mục chứa dự án frontend:

```text
M1/
└── course-registration-frontend/
```

Tên thư mục phải là nơi có file `package.json`. Nếu terminal chưa ở đó, dùng lệnh:

```bash
cd M1/course-registration-frontend
```

> Nếu bạn đã mở terminal ngay trong `course-registration-frontend`, không cần chạy lại lệnh `cd` này.

### Bước 2 — Cài các thư viện cần thiết

Chạy:

```bash
npm ci
```

`npm ci` cài dependency dựa trên `package-lock.json`. Nếu vì lý do nào đó không có `package-lock.json`, có thể dùng `npm install`; trong ZIP này có sẵn lockfile nên ưu tiên `npm ci`.

### Bước 3 — Khởi chạy website ở chế độ phát triển

```bash
npm run dev
```

Terminal sẽ hiển thị địa chỉ local, thường là:

```text
http://localhost:5173/
```

Mở địa chỉ đó trong Chrome/Edge. Giữ terminal mở trong khi dùng website; nhấn `Ctrl + C` để dừng máy chủ phát triển.

### Bước 4 — Mở các màn hình để kiểm tra

Có thể truy cập trực tiếp các đường dẫn sau sau khi server đã chạy:

```text
http://localhost:5173/student/dashboard
http://localhost:5173/student/courses
http://localhost:5173/student/timetable
http://localhost:5173/student/prerequisites
http://localhost:5173/student/enrollment
http://localhost:5173/student/waitlist
http://localhost:5173/admin/courses
http://localhost:5173/admin/prerequisites
```

Lưu ý: đây là frontend demo. Đừng dùng dữ liệu hoặc thao tác trên website này như dữ liệu đăng ký học phần chính thức. Trang quản trị tiên quyết hiện chỉ là placeholder.

## 6. Các lệnh kiểm tra chất lượng

Chạy tại thư mục `course-registration-frontend`.

### Kiểm tra quy tắc code

```bash
npm run lint
```

### Chạy toàn bộ unit test hiện có

```bash
npm test
```

### Chỉ chạy test tiện ích thời khóa biểu

```bash
npm run test:timetable
```

### Build bản production

```bash
npm run build
```

Lệnh build thực hiện kiểm tra TypeScript (`tsc -b`) rồi build ứng dụng bằng Vite. Khi thành công, đầu ra nằm trong thư mục `dist/`.

### Xem thử bản build production ở máy local

Sau khi `npm run build` chạy thành công:

```bash
npm run preview
```

Vite sẽ in ra URL preview trong terminal. Mở URL đó bằng trình duyệt.

**Phân biệt quan trọng:** `npm run preview` chỉ phục vụ thử bản build trên máy local; nó không có nghĩa dự án đã được đóng gói Docker hoặc triển khai qua Nginx như mục tiêu Tuần 6.

## 7. Cấu trúc thư mục chính

```text
course-registration-frontend/
├── public/                         # Tài nguyên tĩnh
├── src/
│   ├── api/                        # Các service/điểm tích hợp API
│   ├── components/
│   │   ├── layout/                 # Header, Sidebar
│   │   └── ui/                     # Thành phần UI dùng chung
│   ├── features/
│   │   ├── courses/                # Dữ liệu, kiểu, lọc/validation học phần
│   │   ├── dashboard/              # Thống kê và tín chỉ
│   │   ├── enroll/                 # Kiểu dữ liệu đăng ký
│   │   ├── prerequisites/          # Dữ liệu mock tiên quyết
│   │   ├── timetable/              # Lưới, tiện ích và dữ liệu lịch
│   │   └── waitlist/               # Tiện ích danh sách chờ
│   ├── layouts/                    # Layout ứng dụng/sinh viên/admin
│   ├── pages/
│   │   ├── admin/
│   │   ├── auth/
│   │   └── student/
│   ├── types/                      # Kiểu dữ liệu dùng chung
│   ├── App.tsx                     # Khai báo route
│   ├── main.tsx                    # Điểm khởi chạy React
│   └── index.css                   # CSS nền
├── tests/                          # Unit test
├── package.json                    # Scripts và dependency
├── package-lock.json               # Khóa phiên bản dependency
├── tsconfig*.json                  # Cấu hình TypeScript
├── vite.config.ts                  # Cấu hình Vite
└── eslint.config.js                # Cấu hình ESLint
```

## 8. Dữ liệu demo và cách làm mới trạng thái

Ứng dụng hiện không yêu cầu database riêng để chạy các màn hình demo. Một số dữ liệu được lưu trên trình duyệt:

- `localStorage`: dữ liệu danh mục học phần và trạng thái đăng ký mock liên quan.
- `sessionStorage`: lớp thêm tạm để xem trước thời khóa biểu.

Nếu muốn thử lại từ trạng thái ban đầu, mở Developer Tools của trình duyệt → **Application** → **Local Storage** / **Session Storage** → chọn `http://localhost:5173` → xóa các khóa dữ liệu demo của ứng dụng. Thao tác này xóa trạng thái lưu trong trình duyệt hiện tại; chỉ thực hiện nếu không cần giữ dữ liệu đang kiểm thử.

Dữ liệu mock lưu ở trình duyệt không được đồng bộ giữa các máy hoặc các thành viên.

## 9. Những việc còn thiếu và thứ tự đề xuất tiếp tục

### Ưu tiên 1 — Hoàn thiện Bước 10: Quản trị điều kiện tiên quyết

- Thay trang placeholder `/admin/prerequisites` bằng giao diện quản trị thật.
- Chọn học phần và xem các quan hệ tiên quyết.
- Hỗ trợ điều kiện `AND` và các nhóm `OR` theo quy ước chung đã chốt với nhóm.
- Thêm/xóa/sửa quan hệ và kiểm tra dữ liệu nhập.
- Phát hiện chu trình trước khi lưu hoặc hiển thị rõ lỗi vòng lặp do server trả về.
- Bổ sung unit test cho nhóm `AND/OR`, tiên quyết bắc cầu và chu trình.

### Ưu tiên 2 — Chốt hợp đồng và tích hợp API backend

Làm việc với thành viên phụ trách backend để chốt endpoint, request/response, schema giải thích tiên quyết, mã lỗi, phân trang, xác thực, token, idempotency key và hành vi hàng chờ. Sau đó thay lần lượt mock service bằng API thật, không tự suy đoán quy tắc chưa được nhóm thống nhất.

### Ưu tiên 3 — Hoàn thiện xác thực, phân quyền và trạng thái lỗi

- Bảo đảm backend xác thực người dùng và kiểm tra quyền cho mọi API quản trị.
- Frontend xử lý hết phiên, lỗi mạng, lỗi nghiệp vụ và trạng thái đang tải/rỗng/lỗi một cách nhất quán.
- Không coi việc ẩn menu hoặc bảo vệ route ở frontend là bảo mật đầy đủ.

### Ưu tiên 4 — Kiểm thử, hiệu năng và đóng gói

- Bổ sung E2E smoke cho các luồng theo kế hoạch 7 tuần.
- Kiểm tra các ca biên của lịch, đăng ký, giới hạn tín chỉ và danh sách chờ.
- Phối hợp M5 để dùng kết quả kiểm thử tải, xử lý `429` và ghi số liệu hiệu năng nếu đây là yêu cầu nghiệm thu.
- Bổ sung và kiểm chứng Docker Compose/Nginx nếu nhóm yêu cầu demo bằng `docker compose up`.
- Chuẩn bị kịch bản demo, dữ liệu demo và slide frontend; xác nhận riêng vì những tài liệu này không thể hiện trong ZIP.

## 10. Ranh giới trách nhiệm và lưu ý khi nghiệm thu

- **Frontend demo:** thể hiện giao diện, điều hướng và mô phỏng một số tương tác bằng dữ liệu mock.
- **Backend cần cung cấp:** xác thực, phân quyền có hiệu lực, dữ liệu dùng chung, kiểm tra nghiệp vụ cuối cùng, chống đăng ký trùng, xử lý đồng thời và API theo hợp đồng đã thống nhất.
- **Nhóm cần chốt:** các quy tắc nghiệp vụ chưa rõ, đặc biệt nhóm tiên quyết `AND/OR`, cách giải thích môn còn thiếu, quy tắc xung đột lịch, giới hạn tín chỉ và hành vi hàng chờ.

Khi báo cáo với nhóm hoặc giảng viên, nên diễn đạt là **“đã hoàn thành các màn hình và luồng demo frontend tương ứng với một phần yêu cầu Tuần 1–4; đang tiếp tục quản trị tiên quyết và chưa tích hợp backend thật”**. Chỉ nâng trạng thái sang “hoàn thành” khi mã nguồn, kiểm thử và tiêu chí nghiệm thu tương ứng đều đã được xác nhận.
