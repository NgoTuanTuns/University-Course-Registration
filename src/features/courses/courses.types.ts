export type CourseStatus = 'open' | 'full' | 'closed'

export interface CourseSchedule {
  dayOfWeek: number
  startTime: string
  endTime: string
}

export interface CourseSearchItem {
  id: string
  courseId: string
  offeringId: string
  code: string
  name: string
  credits: number
  term: string
  section: string
  lecturer: string
  room: string
  schedule: CourseSchedule[]
  capacity: number
  enrolled: number
  status: CourseStatus
  prerequisiteCodes: string[]
  description: string
}

export interface CourseSearchFilters {
  keyword: string
  section: string
  credits: number | 'all'
  term: string
  dayOfWeek: number | 'all'
  page: number
  pageSize: number
}

export interface CourseSearchResponse {
  items: CourseSearchItem[]
  total: number
  page: number
  pageSize: number
  totalPages: number
}

export interface CourseSearchApiParams {
  keyword?: string
  section?: string
  credits?: number
  term?: string
  dayOfWeek?: number
  page: number
  pageSize: number
}