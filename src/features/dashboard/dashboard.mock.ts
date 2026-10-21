import {
  BookOpen,
  CalendarDays,
  CheckCircle2,
  Clock3,
  ClipboardCheck,
  //GraduationCap,
  ListChecks,
  Search,
} from 'lucide-react'

import type {
  CreditSummary,
  DashboardStat,
  EnrollmentSummary,
  QuickAction,
  StudentProfile,
  UpcomingClass,
} from './dashboard.types'

export const studentProfile: StudentProfile = {
  fullName: 'Nguyễn Minh Anh',
  studentId: 'SV2026001',
  program: 'Công nghệ thông tin',
  semester: 'Học kỳ 1 · Năm học 2026–2027',
}

export const creditSummary: CreditSummary = {
  registeredCredits: 15,
  maxCredits: 24,
  completedCredits: 72,
}

export const enrollmentSummary: EnrollmentSummary = {
  registeredClasses: 4,
  waitlistedClasses: 1,
  pendingClasses: 0,
}

export const dashboardStats: DashboardStat[] = [
  {
    id: 'registered',
    title: 'Lớp đã đăng ký',
    value: String(enrollmentSummary.registeredClasses),
    description: 'Lớp có trạng thái đăng ký thành công',
    icon: CheckCircle2,
    iconColorClass: 'text-emerald-700',
    iconBackgroundClass: 'bg-emerald-50',
  },
  {
    id: 'waitlist',
    title: 'Lớp đang chờ',
    value: String(enrollmentSummary.waitlistedClasses),
    description: 'Lớp trong danh sách chờ',
    icon: Clock3,
    iconColorClass: 'text-amber-700',
    iconBackgroundClass: 'bg-amber-50',
  },
  {
    id: 'pending',
    title: 'Đang xử lý',
    value: String(enrollmentSummary.pendingClasses),
    description: 'Yêu cầu đang chờ phản hồi',
    icon: BookOpen,
    iconColorClass: 'text-blue-700',
    iconBackgroundClass: 'bg-blue-50',
  },
]

export const upcomingClasses: UpcomingClass[] = [
  {
    id: 'class-1',
    courseCode: 'INT130',
    courseName: 'Lập trình hướng đối tượng',
    dateLabel: 'Thứ Năm, 22/10/2026',
    startTime: '07:30',
    endTime: '09:30',
    room: 'Phòng A203',
    lecturer: 'Nguyễn Văn Bình',
  },
  {
    id: 'class-2',
    courseCode: 'MAT101',
    courseName: 'Toán rời rạc',
    dateLabel: 'Thứ Sáu, 23/10/2026',
    startTime: '09:45',
    endTime: '11:45',
    room: 'Phòng B105',
    lecturer: 'Trần Thị Hương',
  },
  {
    id: 'class-3',
    courseCode: 'WEB201',
    courseName: 'Phát triển ứng dụng web',
    dateLabel: 'Thứ Bảy, 24/10/2026',
    startTime: '13:00',
    endTime: '15:00',
    room: 'Phòng Lab 02',
    lecturer: 'Lê Quốc Huy',
  },
]

export const quickActions: QuickAction[] = [
  {
    id: 'search',
    title: 'Tra cứu học phần',
    description: 'Tìm môn học, lớp và số tín chỉ',
    to: '/student/courses',
    icon: Search,
    iconColorClass: 'text-blue-700',
    iconBackgroundClass: 'bg-blue-50',
  },
  {
    id: 'timetable',
    title: 'Thời khóa biểu',
    description: 'Xem lịch học và kiểm tra trùng lịch',
    to: '/student/timetable',
    icon: CalendarDays,
    iconColorClass: 'text-violet-700',
    iconBackgroundClass: 'bg-violet-50',
  },
  {
    id: 'prerequisites',
    title: 'Điều kiện tiên quyết',
    description: 'Kiểm tra các học phần cần hoàn thành',
    to: '/student/prerequisites',
    icon: ClipboardCheck,
    iconColorClass: 'text-emerald-700',
    iconBackgroundClass: 'bg-emerald-50',
  },
  {
    id: 'waitlist',
    title: 'Danh sách chờ',
    description: 'Theo dõi các lớp đang chờ',
    to: '/student/waitlist',
    icon: ListChecks,
    iconColorClass: 'text-amber-700',
    iconBackgroundClass: 'bg-amber-50',
  },
]