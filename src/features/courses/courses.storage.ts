import { mockCourses } from './courses.mock'
import type { CourseSearchItem } from './courses.types'

const STORAGE_KEY = 'uniportal:course-catalog:v1'

function copyMockCourses(): CourseSearchItem[] {
  return mockCourses.map((course) => ({
    ...course,
    schedule: course.schedule.map((slot) => ({ ...slot })),
    prerequisiteCodes: [...course.prerequisiteCodes],
  }))
}

export function readCourseCatalog(): CourseSearchItem[] {
  if (typeof localStorage === 'undefined') return copyMockCourses()
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return copyMockCourses()
    const parsed: unknown = JSON.parse(raw)
    if (!Array.isArray(parsed)) return copyMockCourses()
    return parsed as CourseSearchItem[]
  } catch {
    return copyMockCourses()
  }
}

export function writeCourseCatalog(courses: CourseSearchItem[]): void {
  if (typeof localStorage === 'undefined') return
  localStorage.setItem(STORAGE_KEY, JSON.stringify(courses))
}

export function resetCourseCatalog(): void {
  if (typeof localStorage !== 'undefined') localStorage.removeItem(STORAGE_KEY)
}

export { validateCourseItem } from './courses.validation'
