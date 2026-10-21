import { readCourseCatalog } from '../features/courses/courses.storage'
import type { CourseSearchItem } from '../features/courses/courses.types'
import { mockEnrolledOfferings } from '../features/timetable/timetable.mock'
import { findConflicts } from '../features/timetable/timetable.utils'
import { toTimetableOffering } from '../features/timetable/timetable.types'
import { explainPrerequisites } from '../features/prerequisites/prerequisites.mock'
import { EnrollmentError, type EnrollmentRecord } from '../features/enroll/enroll.types'

const STORAGE_KEY = 'uniportal:enrollments:v1'
const MAX_CREDITS = 25

function initialRecords(): EnrollmentRecord[] {
  return mockEnrolledOfferings.map((offering) => {
    const course = readCourseCatalog().find((item) => item.offeringId === offering.offeringId) ?? readCourseCatalog()[0]
    return {
      id: `enr-${offering.offeringId}`,
      offeringId: course.offeringId,
      courseId: course.courseId,
      code: course.code,
      name: course.name,
      section: course.section,
      credits: course.credits,
      term: course.term,
      status: 'active',
      enrolledAt: '2026-10-01T09:00:00.000Z',
      course,
    }
  })
}

function readRecords(): EnrollmentRecord[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return initialRecords()
    const parsed: unknown = JSON.parse(raw)
    if (!Array.isArray(parsed)) return initialRecords()
    return parsed as EnrollmentRecord[]
  } catch {
    return initialRecords()
  }
}

function writeRecords(records: EnrollmentRecord[]): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(records))
}

export async function getEnrollments(term = '2026-1'): Promise<EnrollmentRecord[]> {
  return readRecords().filter((record) => record.term === term)
}

export async function registerCourse(course: CourseSearchItem, idempotencyKey: string): Promise<EnrollmentRecord> {
  // The key is accepted here to keep the mock contract aligned with POST /enroll.
  if (!idempotencyKey) throw new EnrollmentError('CONCURRENT_UPDATE', 'Không xác định được yêu cầu đăng ký. Vui lòng thử lại.')
  const records = readRecords()
  if (records.some((record) => record.offeringId === course.offeringId)) {
    throw new EnrollmentError('ALREADY_ENROLLED', 'Bạn đã đăng ký lớp học phần này rồi.')
  }
  if (course.status === 'closed') throw new EnrollmentError('CLOSED', 'Lớp học phần đã đóng đăng ký.')

  const prerequisite = explainPrerequisites(course.code)
  if (!prerequisite.satisfied) {
    throw new EnrollmentError('PREREQ_NOT_MET', prerequisite.explanation, prerequisite.missingCodes)
  }

  const currentTermRecords = records.filter((record) => record.term === course.term && record.status === 'active')
  const credits = currentTermRecords.reduce((sum, record) => sum + record.credits, 0)
  if (credits + course.credits > MAX_CREDITS) {
    throw new EnrollmentError('CREDIT_LIMIT_EXCEEDED', `Đăng ký lớp này sẽ vượt hạn mức ${MAX_CREDITS} tín chỉ của học kỳ.`)
  }

  const currentOfferings = currentTermRecords.map((record) => toTimetableOffering(record.course, 'enrolled'))
  const conflicts = findConflicts(toTimetableOffering(course, 'preview'), currentOfferings)
  if (conflicts.length > 0) {
    const names = [...new Set(conflicts.map((conflict) => `${conflict.code} (${conflict.section})`))]
    throw new EnrollmentError('SCHEDULE_CONFLICT', `Lịch học bị trùng với ${names.join(', ')}.`, names)
  }

  const waitlisted = course.status === 'full' || course.enrolled >= course.capacity
  const record: EnrollmentRecord = {
    id: `enr-${course.offeringId}-${Date.now()}`,
    offeringId: course.offeringId,
    courseId: course.courseId,
    code: course.code,
    name: course.name,
    section: course.section,
    credits: course.credits,
    term: course.term,
    status: waitlisted ? 'waitlisted' : 'active',
    enrolledAt: new Date().toISOString(),
    course,
    ...(waitlisted ? { position: records.filter((item) => item.offeringId === course.offeringId && item.status === 'waitlisted').length + 1 } : {}),
  }
  writeRecords([...records, record])
  return record
}

export async function cancelEnrollment(enrollmentId: string): Promise<void> {
  const records = readRecords()
  const next = records.filter((record) => record.id !== enrollmentId)
  if (next.length === records.length) throw new EnrollmentError('CONCURRENT_UPDATE', 'Không tìm thấy đăng ký cần hủy. Danh sách đã được làm mới.')
  writeRecords(next)
}

export async function getAllCourseItems(): Promise<CourseSearchItem[]> {
  return readCourseCatalog()
}
