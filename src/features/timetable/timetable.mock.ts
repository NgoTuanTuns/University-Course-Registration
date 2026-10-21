import { mockCourses } from '../courses/courses.mock'
import type { TimetableOffering } from './timetable.types'
import { toTimetableOffering } from './timetable.types'

// Dữ liệu mô phỏng đăng ký hiện tại cho học kỳ 2026-1.
export const mockEnrolledOfferings: TimetableOffering[] = [
  toTimetableOffering(mockCourses[0], 'enrolled'),
  toTimetableOffering(mockCourses[4], 'enrolled'),
  toTimetableOffering(mockCourses[6], 'enrolled'),
]

export const DEFAULT_TERM = '2026-1'
