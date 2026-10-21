import { apiGet } from './http'
import { readCourseCatalog } from '../features/courses/courses.storage'
import type {
  CourseSearchApiParams,
  CourseSearchFilters,
  CourseSearchItem,
  CourseSearchResponse,
} from '../features/courses/courses.types'

function filterMockCourses(
  filters: CourseSearchFilters,
): CourseSearchItem[] {
  const keyword = filters.keyword.trim().toLowerCase()
  const section = filters.section.trim().toLowerCase()

  return readCourseCatalog().filter((course) => {
    const matchesKeyword =
      keyword === '' ||
      course.code.toLowerCase().includes(keyword) ||
      course.name.toLowerCase().includes(keyword) ||
      course.lecturer.toLowerCase().includes(keyword)

    const matchesSection =
      section === '' ||
      course.section.toLowerCase().includes(section)

    const matchesCredits =
      filters.credits === 'all' ||
      course.credits === filters.credits

    const matchesTerm =
      filters.term === 'all' || course.term === filters.term

    const matchesDay =
      filters.dayOfWeek === 'all' ||
      course.schedule.some(
        (slot) => slot.dayOfWeek === filters.dayOfWeek,
      )

    return (
      matchesKeyword &&
      matchesSection &&
      matchesCredits &&
      matchesTerm &&
      matchesDay
    )
  })
}

function paginateMockCourses(
  courses: CourseSearchItem[],
  page: number,
  pageSize: number,
): CourseSearchResponse {
  const total = courses.length
  const totalPages = Math.ceil(total / pageSize)
  const safePage = Math.min(page, Math.max(totalPages, 1))
  const start = (safePage - 1) * pageSize

  return {
    items: courses.slice(start, start + pageSize),
    total,
    page: safePage,
    pageSize,
    totalPages,
  }
}

export async function searchCourses(
  filters: CourseSearchFilters,
): Promise<CourseSearchResponse> {
  const useMockData =
    import.meta.env.VITE_USE_MOCK_DATA !== 'false'

  if (useMockData) {
    const filtered = filterMockCourses(filters)

    return paginateMockCourses(
      filtered,
      filters.page,
      filters.pageSize,
    )
  }

  const params: CourseSearchApiParams = {
    page: filters.page,
    pageSize: filters.pageSize,
    ...(filters.keyword.trim()
      ? { keyword: filters.keyword.trim() }
      : {}),
    ...(filters.section.trim()
      ? { section: filters.section.trim() }
      : {}),
    ...(filters.credits !== 'all'
      ? { credits: filters.credits }
      : {}),
    ...(filters.term !== 'all' ? { term: filters.term } : {}),
    ...(filters.dayOfWeek !== 'all'
      ? { dayOfWeek: filters.dayOfWeek }
      : {}),
  }

  // Dự kiến: GET /courses/search
  // Cần đối chiếu query params và response với OpenAPI của backend.
  const response = await apiGet<CourseSearchResponse>(
    '/courses/search',
    params as unknown as Record<string, string | number | undefined>,
  )

  return response
}