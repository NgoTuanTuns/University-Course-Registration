import assert from 'node:assert/strict'
import test from 'node:test'
import type { CourseSchedule } from '../src/features/courses/courses.types.ts'
import { findConflicts, parseTime, slotsOverlap } from '../src/features/timetable/timetable.utils.ts'
import type { TimetableOffering } from '../src/features/timetable/timetable.types.ts'

function slot(dayOfWeek: number, startTime: string, endTime: string): CourseSchedule {
  return { dayOfWeek, startTime, endTime }
}

function offering(
  offeringId: string,
  schedule: CourseSchedule[],
): TimetableOffering {
  return {
    id: offeringId,
    courseId: `course-${offeringId}`,
    offeringId,
    code: offeringId.toUpperCase(),
    name: `Học phần ${offeringId}`,
    section: `${offeringId.toUpperCase()}.01`,
    lecturer: 'Giảng viên demo',
    room: 'A101',
    credits: 3,
    term: '2026-1',
    schedule,
    kind: 'enrolled',
  }
}

test('parseTime converts HH:MM into minutes', () => {
  assert.equal(parseTime('07:00'), 420)
  assert.equal(parseTime('09:30'), 570)
  assert.equal(parseTime('21:00'), 1260)
})

test('slotsOverlap detects an exact overlap', () => {
  assert.equal(slotsOverlap(slot(2, '07:30', '09:30'), slot(2, '07:30', '09:30')), true)
})

test('slotsOverlap detects a partial overlap', () => {
  assert.equal(slotsOverlap(slot(2, '07:30', '09:30'), slot(2, '08:30', '10:00')), true)
})

test('adjacent classes are not considered a conflict', () => {
  assert.equal(slotsOverlap(slot(2, '07:30', '09:30'), slot(2, '09:30', '11:00')), false)
})

test('classes on different days do not conflict', () => {
  assert.equal(slotsOverlap(slot(2, '07:30', '09:30'), slot(3, '07:30', '09:30')), false)
})

test('findConflicts checks multiple sessions in a week', () => {
  const candidate = offering('candidate', [slot(2, '07:30', '09:30'), slot(4, '13:00', '15:00')])
  const current = offering('current', [slot(1, '07:30', '09:30'), slot(4, '14:00', '16:00')])
  const conflicts = findConflicts(candidate, [current])
  assert.equal(conflicts.length, 1)
  assert.equal(conflicts[0].code, 'CURRENT')
  assert.equal(conflicts[0].candidateSlot.dayOfWeek, 4)
})

test('an offering does not conflict with itself', () => {
  const same = offering('same', [slot(2, '07:30', '09:30')])
  assert.deepEqual(findConflicts(same, [same]), [])
})
