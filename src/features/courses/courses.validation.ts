import type { CourseSearchItem } from './courses.types.ts'

export function validateCourseItem(
  input: Pick<CourseSearchItem, 'code' | 'name' | 'credits' | 'capacity' | 'enrolled' | 'term' | 'section'>,
  courses: CourseSearchItem[],
  currentId?: string,
): string | null {
  const code = input.code.trim().toUpperCase()
  if (!/^[A-Z0-9]{2,12}$/.test(code)) return 'Mã học phần chỉ gồm chữ in hoa và số, dài 2–12 ký tự.'
  if (!input.name.trim()) return 'Vui lòng nhập tên học phần.'
  if (!Number.isInteger(input.credits) || input.credits < 1 || input.credits > 10) return 'Số tín chỉ phải là số nguyên từ 1 đến 10.'
  if (!Number.isInteger(input.capacity) || input.capacity < 1) return 'Sĩ số tối đa phải lớn hơn 0.'
  if (!Number.isInteger(input.enrolled) || input.enrolled < 0 || input.enrolled > input.capacity) return 'Sĩ số hiện tại phải từ 0 đến sĩ số tối đa.'
  if (courses.some((course) => course.id !== currentId && course.code.toUpperCase() === code && course.term === input.term && course.section.toUpperCase() === input.section.trim().toUpperCase())) {
    return 'Mã lớp đã tồn tại trong học kỳ này.'
  }
  return null
}
