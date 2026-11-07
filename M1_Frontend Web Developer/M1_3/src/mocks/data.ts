import type { Enrollment, Offering } from "../types";

const courseNames = [
  "Lập trình căn bản", "Cấu trúc dữ liệu và giải thuật", "Cơ sở dữ liệu",
  "Công nghệ phần mềm", "Mạng máy tính", "Trí tuệ nhân tạo",
  "Toán rời rạc", "Hệ điều hành", "Phân tích thiết kế hệ thống",
];
const instructors = ["Nguyễn Minh Anh", "Trần Quang Huy", "Lê Thu Hà", "Phạm Quốc Bảo"];

export const offerings: Offering[] = Array.from({ length: 40 }, (_, index) => {
  const id = index + 1;
  const day = index < 3 ? 2 : (index % 5) + 1;
  const start = index === 1 ? "08:00" : index === 2 ? "09:30" : index % 2 ? "09:30" : "07:00";
  const end = index === 1 ? "10:00" : index === 2 ? "12:00" : index % 2 ? "12:00" : "09:30";
  return {
    id,
    courseId: id,
    code: `INT${131 + index}`,
    name: courseNames[index % courseNames.length],
    credits: (index % 3) + 2,
    section: `N${(index % 3) + 1}`,
    instructor: instructors[index % instructors.length],
    room: `A${201 + (index % 8)}`,
    schedule: [
      { day, start, end },
      ...(index % 7 === 0 ? [{ day: 6, start: "13:00", end: "15:30" }] : []),
    ],
    enrolledCount: index % 6 === 0 ? 40 : 20 + (index % 20),
    capacity: 40,
  };
});

export const registrations: Enrollment[] = [
  { id: 101, offering: offerings[0], status: "ACTIVE" },
  { id: 102, offering: offerings[8], status: "ACTIVE" },
];

export function removeRegistration(id: number): void {
  const index = registrations.findIndex((entry) => entry.id === id);
  if (index >= 0) registrations.splice(index, 1);
}

// Các ID bên dưới khớp thứ tự 12 học phần/lớp KIT trong seed_data.py của backend nhóm.
// Chỉ dùng làm danh mục đọc/xem trước ở Week 3 vì backend chưa có GET /courses.
const seedCatalog: Offering[] = [
  { id: 1, courseId: 1, code: "INT101", name: "Nhập môn lập trình", credits: 3, section: "01", instructor: "Nguyễn Minh Anh", room: "A1-101", schedule: [{ day: 1, start: "07:00", end: "09:30" }, { day: 4, start: "07:00", end: "09:30" }], enrolledCount: 0, capacity: 60 },
  { id: 2, courseId: 4, code: "INT131", name: "Lập trình hướng đối tượng", credits: 3, section: "01", instructor: "Trần Quang Huy", room: "A1-102", schedule: [{ day: 2, start: "07:00", end: "09:30" }], enrolledCount: 0, capacity: 50 },
  { id: 3, courseId: 5, code: "INT221", name: "Cấu trúc dữ liệu", credits: 3, section: "01", instructor: "Lê Thu Hà", room: "A1-103", schedule: [{ day: 3, start: "07:00", end: "09:30" }], enrolledCount: 1, capacity: 50 },
  { id: 4, courseId: 6, code: "INT222", name: "Cơ sở dữ liệu", credits: 3, section: "01", instructor: "Phạm Quốc Bảo", room: "A1-104", schedule: [{ day: 3, start: "08:00", end: "10:30" }], enrolledCount: 0, capacity: 50 },
  { id: 5, courseId: 2, code: "MAT201", name: "Giải tích 2", credits: 3, section: "01", instructor: "Nguyễn Minh Anh", room: "A1-105", schedule: [{ day: 3, start: "09:30", end: "11:30" }], enrolledCount: 0, capacity: 60 },
  { id: 6, courseId: 3, code: "MAT202", name: "Đại số tuyến tính", credits: 3, section: "01", instructor: "Trần Quang Huy", room: "A1-106", schedule: [{ day: 2, start: "13:00", end: "15:30" }], enrolledCount: 0, capacity: 60 },
  { id: 7, courseId: 7, code: "INT231", name: "Giải thuật", credits: 3, section: "01", instructor: "Lê Thu Hà", room: "A1-107", schedule: [{ day: 1, start: "13:00", end: "15:30" }], enrolledCount: 29, capacity: 30 },
  { id: 8, courseId: 9, code: "INT331", name: "Phân tích thiết kế hệ thống", credits: 3, section: "01", instructor: "Phạm Quốc Bảo", room: "A1-108", schedule: [{ day: 5, start: "07:00", end: "09:30" }], enrolledCount: 15, capacity: 15 },
  { id: 9, courseId: 10, code: "INT341", name: "Học máy", credits: 3, section: "01", instructor: "Nguyễn Minh Anh", room: "A1-109", schedule: [{ day: 4, start: "13:00", end: "15:30" }], enrolledCount: 0, capacity: 1 },
  { id: 10, courseId: 8, code: "INT321", name: "Hệ quản trị CSDL", credits: 3, section: "01", instructor: "Trần Quang Huy", room: "A1-110", schedule: [{ day: 6, start: "07:00", end: "09:30" }], enrolledCount: 0, capacity: 40 },
  { id: 11, courseId: 12, code: "INT431", name: "Đồ án chuyên ngành", credits: 3, section: "01", instructor: "Lê Thu Hà", room: "A1-111", schedule: [{ day: 6, start: "09:30", end: "12:00" }], enrolledCount: 0, capacity: 40 },
  { id: 12, courseId: 11, code: "INT451", name: "Chuyên đề", credits: 3, section: "01", instructor: "Phạm Quốc Bảo", room: "A1-112", schedule: [{ day: 6, start: "13:00", end: "15:30" }], enrolledCount: 0, capacity: 40 },
];

export function getStaticOfferings(): Offering[] {
  return seedCatalog;
}
