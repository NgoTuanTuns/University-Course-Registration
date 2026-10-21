import { readCourseCatalog, validateCourseItem, writeCourseCatalog } from '../features/courses/courses.storage'
import type { CourseSearchItem } from '../features/courses/courses.types'

export interface CourseAdminInput {
  code: string
  name: string
  credits: number
  term: string
  section: string
  lecturer: string
  room: string
  capacity: number
  enrolled: number
  status: CourseSearchItem['status']
  dayOfWeek: number
  startTime: string
  endTime: string
  prerequisiteCodes: string[]
  description: string
}

export async function listAdminCourses(): Promise<CourseSearchItem[]> {
  return readCourseCatalog().sort((a, b) => a.code.localeCompare(b.code, 'vi'))
}

export async function saveAdminCourse(input: CourseAdminInput, id?: string): Promise<CourseSearchItem> {
  const courses = readCourseCatalog()
  const existing = id ? courses.find((course) => course.id === id) : undefined
  if (id && !existing) throw new Error('Không tìm thấy học phần cần cập nhật. Hãy tải lại danh sách.')
  const normalized: CourseSearchItem = {
    id: existing?.id ?? `off-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    courseId: existing?.courseId ?? `course-${input.code.trim().toLowerCase()}`,
    offeringId: existing?.offeringId ?? `off-${Date.now()}`,
    code: input.code.trim().toUpperCase(),
    name: input.name.trim(),
    credits: input.credits,
    term: input.term,
    section: input.section.trim(),
    lecturer: input.lecturer.trim() || 'Chưa phân công',
    room: input.room.trim() || 'Chưa xếp phòng',
    schedule: [{ dayOfWeek: input.dayOfWeek, startTime: input.startTime, endTime: input.endTime }],
    capacity: input.capacity,
    enrolled: input.enrolled,
    status: input.status,
    prerequisiteCodes: [...new Set(input.prerequisiteCodes.map((code) => code.trim().toUpperCase()).filter(Boolean))],
    description: input.description.trim(),
  }
  const error = validateCourseItem(normalized, courses, id)
  if (error) throw new Error(error)
  const next = existing
    ? courses.map((course) => course.id === id ? normalized : course)
    : [...courses, normalized]
  writeCourseCatalog(next)
  return normalized
}

export async function deleteAdminCourse(id: string): Promise<void> {
  const courses = readCourseCatalog()
  const course = courses.find((item) => item.id === id)
  if (!course) throw new Error('Học phần không còn tồn tại. Vui lòng tải lại danh sách.')
  if (typeof localStorage !== 'undefined') {
    try {
      const enrollmentsRaw = localStorage.getItem('uniportal:enrollments:v1')
      const enrollments: unknown = enrollmentsRaw ? JSON.parse(enrollmentsRaw) : []
      if (Array.isArray(enrollments) && enrollments.some((record) => {
        if (!record || typeof record !== 'object') return false
        const item = record as { offeringId?: string; status?: string }
        return item.offeringId === course.offeringId && (item.status === 'active' || item.status === 'waitlisted')
      })) {
        throw new Error('Không thể xóa lớp đang có sinh viên đăng ký hoặc trong danh sách chờ. Hãy xử lý các đăng ký trước.')
      }
    } catch (error) {
      if (error instanceof Error && error.message.startsWith('Không thể xóa')) throw error
      throw new Error('Không thể kiểm tra đăng ký hiện tại. Vui lòng thử lại.', { cause: error })
    }
  }
  writeCourseCatalog(courses.filter((item) => item.id !== id))
}
