import test from 'node:test'
import assert from 'node:assert/strict'
import { sortWaitlistRecords, formatEnqueuedAt } from '../src/features/waitlist/waitlist.utils.ts'
import type { EnrollmentRecord } from '../src/features/enroll/enroll.types.ts'

function record(id: string, status: 'active' | 'waitlisted', position: number, enrolledAt: string): EnrollmentRecord {
  return {
    id, offeringId: id, courseId: id, code: id, name: id, section: '01', credits: 3,
    term: '2026-1', status, position, enrolledAt,
    course: { id, courseId: id, offeringId: id, code: id, name: id, credits: 3, term: '2026-1', section: '01', lecturer: 'Demo', room: 'A1', schedule: [], capacity: 10, enrolled: 10, status: 'full', prerequisiteCodes: [], description: '' },
  }
}

test('waitlist shows only queued records and sorts by position then enqueue time', () => {
  const result = sortWaitlistRecords([
    record('later', 'waitlisted', 2, '2026-10-02T10:00:00.000Z'),
    record('active', 'active', 1, '2026-10-01T10:00:00.000Z'),
    record('first', 'waitlisted', 1, '2026-10-03T10:00:00.000Z'),
  ])
  assert.deepEqual(result.map((item) => item.id), ['first', 'later'])
})

test('invalid enqueue date has a friendly fallback', () => {
  assert.equal(formatEnqueuedAt('not-a-date'), 'Chưa có thông tin')
})
