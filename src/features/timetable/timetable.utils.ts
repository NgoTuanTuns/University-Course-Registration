import type { CourseSchedule } from '../courses/courses.types'
import type { ScheduleConflict, TimetableOffering } from './timetable.types'

export const TIMETABLE_START_HOUR = 7
export const TIMETABLE_END_HOUR = 21
export const MINUTES_PER_HOUR = 60
export const DAY_NAMES = [
  { day: 1, label: 'Thứ Hai', short: 'T2' },
  { day: 2, label: 'Thứ Ba', short: 'T3' },
  { day: 3, label: 'Thứ Tư', short: 'T4' },
  { day: 4, label: 'Thứ Năm', short: 'T5' },
  { day: 5, label: 'Thứ Sáu', short: 'T6' },
  { day: 6, label: 'Thứ Bảy', short: 'T7' },
  { day: 7, label: 'Chủ nhật', short: 'CN' },
] as const

export function parseTime(time: string): number {
  const match = /^(\d{2}):(\d{2})$/.exec(time)
  if (!match) throw new Error(`Giờ không hợp lệ: ${time}`)
  const hours = Number(match[1])
  const minutes = Number(match[2])
  if (hours > 23 || minutes > 59) throw new Error(`Giờ không hợp lệ: ${time}`)
  return hours * MINUTES_PER_HOUR + minutes
}

export function formatMinutes(totalMinutes: number): string {
  const hours = Math.floor(totalMinutes / MINUTES_PER_HOUR)
  const minutes = totalMinutes % MINUTES_PER_HOUR
  return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`
}

export function slotsOverlap(a: CourseSchedule, b: CourseSchedule): boolean {
  if (a.dayOfWeek !== b.dayOfWeek) return false
  const aStart = parseTime(a.startTime)
  const aEnd = parseTime(a.endTime)
  const bStart = parseTime(b.startTime)
  const bEnd = parseTime(b.endTime)
  if (aStart >= aEnd || bStart >= bEnd) return false
  return aStart < bEnd && bStart < aEnd
}

export function findConflicts(
  candidateOffering: TimetableOffering,
  currentOfferings: TimetableOffering[],
): ScheduleConflict[] {
  const conflicts: ScheduleConflict[] = []
  for (const current of currentOfferings) {
    if (current.offeringId === candidateOffering.offeringId) continue
    for (const candidateSlot of candidateOffering.schedule) {
      for (const currentSlot of current.schedule) {
        if (slotsOverlap(candidateSlot, currentSlot)) {
          conflicts.push({
            offeringId: current.offeringId,
            code: current.code,
            name: current.name,
            section: current.section,
            candidateSlot,
            currentSlot,
          })
        }
      }
    }
  }
  return conflicts
}

export function getCourseColor(courseId: string): { background: string; border: string; text: string } {
  const palette = [
    { background: '#dbeafe', border: '#3b82f6', text: '#1e40af' },
    { background: '#dcfce7', border: '#22c55e', text: '#166534' },
    { background: '#f3e8ff', border: '#a855f7', text: '#6b21a8' },
    { background: '#ffedd5', border: '#f97316', text: '#9a3412' },
    { background: '#cffafe', border: '#06b6d4', text: '#155e75' },
    { background: '#fce7f3', border: '#ec4899', text: '#9d174d' },
    { background: '#e0e7ff', border: '#6366f1', text: '#3730a3' },
  ]
  let hash = 0
  for (let index = 0; index < courseId.length; index += 1) {
    hash = (hash * 31 + courseId.charCodeAt(index)) | 0
  }
  return palette[Math.abs(hash) % palette.length]
}

export function getSlotPosition(slot: CourseSchedule): { top: number; height: number } {
  const start = parseTime(slot.startTime)
  const end = parseTime(slot.endTime)
  const startOfDay = TIMETABLE_START_HOUR * MINUTES_PER_HOUR
  const pixelsPerMinute = 1
  return {
    top: (start - startOfDay) * pixelsPerMinute,
    height: Math.max((end - start) * pixelsPerMinute, 22),
  }
}

export function getDayLayout(
  events: Array<{ key: string; slot: CourseSchedule }>,
): Array<{ key: string; lane: number; laneCount: number }> {
  const sorted = [...events].sort((a, b) => parseTime(a.slot.startTime) - parseTime(b.slot.startTime))
  const groups: Array<typeof sorted> = []
  let group: typeof sorted = []
  let groupEnd = -1

  for (const event of sorted) {
    const start = parseTime(event.slot.startTime)
    const end = parseTime(event.slot.endTime)
    if (group.length > 0 && start >= groupEnd) {
      groups.push(group)
      group = []
      groupEnd = -1
    }
    group.push(event)
    groupEnd = Math.max(groupEnd, end)
  }
  if (group.length > 0) groups.push(group)

  const result: Array<{ key: string; lane: number; laneCount: number }> = []
  for (const overlappingGroup of groups) {
    const laneEnds: number[] = []
    for (const event of overlappingGroup) {
      const start = parseTime(event.slot.startTime)
      let lane = laneEnds.findIndex((end) => end <= start)
      if (lane === -1) lane = laneEnds.length
      laneEnds[lane] = parseTime(event.slot.endTime)
      result.push({ key: event.key, lane, laneCount: Math.max(laneEnds.length, 1) })
    }
    const laneCount = Math.max(laneEnds.length, 1)
    for (const item of result) {
      if (overlappingGroup.some((event) => event.key === item.key)) item.laneCount = laneCount
    }
  }
  return result
}
