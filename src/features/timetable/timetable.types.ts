import type { CourseSearchItem, CourseSchedule } from '../courses/courses.types'

export interface TimetableOffering {
  id: string
  courseId: string
  offeringId: string
  code: string
  name: string
  section: string
  lecturer: string
  room: string
  credits: number
  term: string
  schedule: CourseSchedule[]
  kind: 'enrolled' | 'preview'
}

export interface ScheduleConflict {
  offeringId: string
  code: string
  name: string
  section: string
  candidateSlot: CourseSchedule
  currentSlot: CourseSchedule
}

export function toTimetableOffering(
  course: CourseSearchItem,
  kind: TimetableOffering['kind'],
): TimetableOffering {
  return {
    id: course.id,
    courseId: course.courseId,
    offeringId: course.offeringId,
    code: course.code,
    name: course.name,
    section: course.section,
    lecturer: course.lecturer,
    room: course.room,
    credits: course.credits,
    term: course.term,
    schedule: course.schedule,
    kind,
  }
}
