import test from 'node:test'
import assert from 'node:assert/strict'
import { validateCourseItem } from '../src/features/courses/courses.validation.ts'
import type { CourseSearchItem } from '../src/features/courses/courses.types.ts'

const existing: CourseSearchItem[] = [{
  id: 'off-1', courseId: 'course-int101', offeringId: 'off-1', code: 'INT101', name: 'Nhập môn lập trình', credits: 3,
  term: '2026-1', section: 'INT101.01', lecturer: 'Demo', room: 'A101', schedule: [{ dayOfWeek: 3, startTime: '07:30', endTime: '09:30' }],
  capacity: 40, enrolled: 20, status: 'open', prerequisiteCodes: [], description: '',
}]

function input(overrides: Partial<CourseSearchItem> = {}) {
  return { code: 'WEB301', name: 'Phát triển web nâng cao', credits: 3, capacity: 40, enrolled: 20, term: '2026-2', section: 'WEB301.01', ...overrides }
}

test('accepts valid course data', () => assert.equal(validateCourseItem(input(), existing), null))
test('rejects credit values outside 1–10', () => assert.match(validateCourseItem(input({ credits: 11 }), existing) ?? '', /từ 1 đến 10/))
test('rejects duplicate class code, term and section', () => assert.match(validateCourseItem(input({ code: 'INT101', term: '2026-1', section: 'INT101.01' }), existing) ?? '', /đã tồn tại/))
test('allows another section of the same course in the same term', () => assert.equal(validateCourseItem(input({ code: 'INT101', term: '2026-1', section: 'INT101.02' }), existing), null))
test('rejects enrollment greater than capacity', () => assert.match(validateCourseItem(input({ enrolled: 41 }), existing) ?? '', /Sĩ số hiện tại/i))
