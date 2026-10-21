import test from 'node:test'
import assert from 'node:assert/strict'
import { getCreditPercentage, getEnrollmentSummary } from '../src/features/dashboard/dashboard.utils.ts'
import type { EnrollmentRecord } from '../src/features/enroll/enroll.types.ts'

function record(id: string, status: 'active' | 'waitlisted', credits: number): EnrollmentRecord {
  return {
    id, offeringId: id, courseId: id, code: id, name: `Course ${id}`, section: '01',
    credits, term: '2026-1', status, enrolledAt: '2026-10-01T09:00:00.000Z',
    position: status === 'waitlisted' ? 1 : undefined,
    course: {
      id, courseId: id, offeringId: id, code: id, name: `Course ${id}`, credits,
      term: '2026-1', section: '01', lecturer: 'Demo', room: 'A1', schedule: [],
      capacity: 20, enrolled: 10, status: 'open', prerequisiteCodes: [], description: '',
    },
  }
}

test('dashboard counts active credits but excludes waitlisted classes', () => {
  assert.deepEqual(getEnrollmentSummary([record('A', 'active', 3), record('B', 'waitlisted', 4), record('C', 'active', 2)]), {
    registeredClasses: 2, waitlistedClasses: 1, registeredCredits: 5,
  })
})

test('credit progress stays between 0 and 100 percent', () => {
  assert.equal(getCreditPercentage(15, 25), 60)
  assert.equal(getCreditPercentage(30, 25), 100)
  assert.equal(getCreditPercentage(-2, 25), 0)
  assert.equal(getCreditPercentage(5, 0), 0)
})
