import type { CourseSearchItem } from '../courses/courses.types'

export type EnrollmentStatus = 'active' | 'waitlisted'

export interface EnrollmentRecord {
  id: string
  offeringId: string
  courseId: string
  code: string
  name: string
  section: string
  credits: number
  term: string
  status: EnrollmentStatus
  enrolledAt: string
  course: CourseSearchItem
  position?: number
}

export type EnrollmentErrorCode =
  | 'PREREQ_NOT_MET'
  | 'CREDIT_LIMIT_EXCEEDED'
  | 'SCHEDULE_CONFLICT'
  | 'ALREADY_ENROLLED'
  | 'CONCURRENT_UPDATE'
  | 'CLOSED'

export class EnrollmentError extends Error {
  readonly code: EnrollmentErrorCode
  readonly relatedCodes: string[]

  constructor(code: EnrollmentErrorCode, message: string, relatedCodes: string[] = []) {
    super(message)
    this.name = 'EnrollmentError'
    this.code = code
    this.relatedCodes = relatedCodes
  }
}
