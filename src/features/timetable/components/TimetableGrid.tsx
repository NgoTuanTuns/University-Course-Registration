import { AlertTriangle, Clock3, MapPin } from 'lucide-react'
import type { CourseSchedule } from '../../courses/courses.types'
import type { TimetableOffering } from '../timetable.types'
import {
  DAY_NAMES,
  TIMETABLE_END_HOUR,
  TIMETABLE_START_HOUR,
  findConflicts,
  formatMinutes,
  getCourseColor,
  getDayLayout,
  getSlotPosition,
  parseTime,
} from '../timetable.utils'

interface TimetableGridProps {
  offerings: TimetableOffering[]
  selectedTerm: string
}

interface PositionedEvent {
  key: string
  offering: TimetableOffering
  slot: CourseSchedule
  conflictNames: string[]
  lane: number
  laneCount: number
}

const HOUR_HEIGHT = 60
const GRID_HEIGHT = (TIMETABLE_END_HOUR - TIMETABLE_START_HOUR) * HOUR_HEIGHT

export default function TimetableGrid({ offerings, selectedTerm }: TimetableGridProps) {
  const semesterOfferings = offerings.filter((item) => item.term === selectedTerm)
  const eventsByDay = new Map<number, PositionedEvent[]>()

  for (const day of DAY_NAMES) {
    const dayEvents: PositionedEvent[] = []
    for (const offering of semesterOfferings) {
      for (const [index, slot] of offering.schedule.entries()) {
        if (slot.dayOfWeek !== day.day) continue
        const conflicts = findConflicts(offering, semesterOfferings)
          .filter((conflict) => conflict.candidateSlot === slot)
        dayEvents.push({
          key: `${offering.offeringId}-${index}`,
          offering,
          slot,
          conflictNames: [...new Set(conflicts.map((item) => `${item.code} (${item.section})`))],
          lane: 0,
          laneCount: 1,
        })
      }
    }
    const layout = getDayLayout(dayEvents.map((event) => ({ key: event.key, slot: event.slot })))
    for (const event of dayEvents) {
      const position = layout.find((item) => item.key === event.key)
      if (position) {
        event.lane = position.lane
        event.laneCount = position.laneCount
      }
    }
    eventsByDay.set(day.day, dayEvents)
  }

  const hours = Array.from(
    { length: TIMETABLE_END_HOUR - TIMETABLE_START_HOUR },
    (_, index) => TIMETABLE_START_HOUR + index,
  )

  return (
    <section className="overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--surface)] shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--border)] px-4 py-4 sm:px-5">
        <div>
          <h2 className="font-semibold text-[var(--text)]">Lịch học trong tuần</h2>
          <p className="mt-1 text-xs text-[var(--muted)]">Mỗi ô tương ứng một ngày; chiều cao khối phản ánh thời lượng học.</p>
        </div>
        <span className="rounded-lg bg-[var(--hover)] px-3 py-1.5 text-xs font-semibold text-[var(--muted)]">
          {selectedTerm === '2026-1' ? 'Học kỳ 1 · 2026–2027' : 'Học kỳ 2 · 2026–2027'}
        </span>
      </div>

      {semesterOfferings.length === 0 ? (
        <div className="px-6 py-16 text-center">
          <Clock3 className="mx-auto text-[var(--muted)]" size={34} />
          <p className="mt-3 font-semibold text-[var(--text)]">Chưa có lớp học trong học kỳ này</p>
          <p className="mt-1 text-sm text-[var(--muted)]">Hãy chọn học kỳ khác hoặc xem trước một lớp từ trang Tra cứu học phần.</p>
        </div>
      ) : (
        <div className="overflow-x-auto" aria-label="Lưới thời khóa biểu theo tuần">
          <div className="min-w-[1050px]">
            <div className="grid grid-cols-[68px_repeat(7,minmax(0,1fr))] border-b border-[var(--border)] bg-[var(--hover)]/60">
              <div className="border-r border-[var(--border)] px-2 py-3 text-center text-[10px] font-bold uppercase tracking-wide text-[var(--muted)]">Giờ</div>
              {DAY_NAMES.map((day) => {
                const count = (eventsByDay.get(day.day) ?? []).length
                return (
                  <div key={day.day} className="border-r border-[var(--border)] px-2 py-3 text-center last:border-r-0">
                    <p className="text-xs font-bold text-[var(--text)]">{day.label}</p>
                    <p className="mt-1 text-[10px] text-[var(--muted)]">{count} buổi học</p>
                  </div>
                )
              })}
            </div>

            <div className="grid grid-cols-[68px_repeat(7,minmax(0,1fr))]">
              <div className="relative border-r border-[var(--border)]" style={{ height: GRID_HEIGHT }}>
                {hours.map((hour) => (
                  <div key={hour} className="absolute right-0 left-0 border-t border-[var(--border)]" style={{ top: (hour - TIMETABLE_START_HOUR) * HOUR_HEIGHT }}>
                    <span className="relative -top-2.5 bg-[var(--surface)] px-1.5 text-[10px] font-medium tabular-nums text-[var(--muted)]">{formatMinutes(hour * 60)}</span>
                  </div>
                ))}
              </div>

              {DAY_NAMES.map((day) => (
                <div key={day.day} className="relative border-r border-[var(--border)] last:border-r-0" style={{ height: GRID_HEIGHT }}>
                  {hours.map((hour) => (
                    <div key={hour} className="absolute right-0 left-0 border-t border-dashed border-[var(--border)]/80" style={{ top: (hour - TIMETABLE_START_HOUR) * HOUR_HEIGHT }} />
                  ))}
                  {Array.from({ length: hours.length }, (_, index) => (
                    <div key={`half-${index}`} className="absolute right-0 left-0 border-t border-dotted border-[var(--border)]/50" style={{ top: index * HOUR_HEIGHT + HOUR_HEIGHT / 2 }} />
                  ))}
                  {(eventsByDay.get(day.day) ?? []).map((event) => {
                    const { top, height } = getSlotPosition(event.slot)
                    const color = getCourseColor(event.offering.courseId)
                    const hasConflict = event.conflictNames.length > 0
                    const visibleTop = Math.max(top, 0)
                    const visibleHeight = Math.min(top + height, GRID_HEIGHT) - visibleTop
                    if (visibleHeight <= 0 || parseTime(event.slot.endTime) <= TIMETABLE_START_HOUR * 60 || parseTime(event.slot.startTime) >= TIMETABLE_END_HOUR * 60) return null
                    return (
                      <article
                        key={event.key}
                        title={hasConflict ? `Trùng với ${event.conflictNames.join(', ')}` : `${event.offering.name} · ${event.offering.section}`}
                        className={`absolute z-10 overflow-hidden rounded-md border-l-[3px] px-1.5 py-1 text-left text-[10px] leading-tight shadow-sm sm:px-2 ${event.offering.kind === 'preview' ? 'border-dashed opacity-65' : ''} ${hasConflict ? 'ring-2 ring-red-500 ring-inset' : ''}`}
                        style={{
                          top: visibleTop,
                          height: visibleHeight,
                          left: `calc(${(event.lane / event.laneCount) * 100}% + 2px)`,
                          width: `calc(${100 / event.laneCount}% - 4px)`,
                          backgroundColor: hasConflict ? '#fee2e2' : color.background,
                          borderLeftColor: hasConflict ? '#dc2626' : color.border,
                          color: hasConflict ? '#991b1b' : color.text,
                        }}
                      >
                        <div className="flex items-start gap-1 font-extrabold">
                          <span className="min-w-0 break-words">{event.offering.code}</span>
                          {hasConflict && <AlertTriangle size={12} className="shrink-0" aria-label="Có trùng lịch" />}
                        </div>
                        <p className="mt-0.5 line-clamp-2 font-semibold">{event.offering.section}</p>
                        {visibleHeight >= 54 && <p className="mt-1 line-clamp-2">{event.offering.name}</p>}
                        {visibleHeight >= 70 && <p className="mt-1 flex items-center gap-1"><MapPin size={10} />{event.offering.room}</p>}
                        {visibleHeight >= 88 && <p className="mt-1 tabular-nums">{event.slot.startTime}–{event.slot.endTime}</p>}
                        {hasConflict && <p className="mt-1 font-bold">Trùng: {event.conflictNames.join(', ')}</p>}
                      </article>
                    )
                  })}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
      <div className="flex flex-wrap gap-x-4 gap-y-2 border-t border-[var(--border)] px-4 py-3 text-xs text-[var(--muted)] sm:px-5">
        <span className="inline-flex items-center gap-2"><span className="h-3 w-3 rounded-sm border border-blue-500 bg-blue-100" />Đã đăng ký</span>
        <span className="inline-flex items-center gap-2"><span className="h-3 w-3 rounded-sm border border-dashed border-slate-500 bg-slate-100 opacity-70" />Xem trước</span>
        <span className="inline-flex items-center gap-2"><span className="h-3 w-3 rounded-sm border-2 border-red-600 bg-red-100" />Trùng lịch (có viền đỏ và cảnh báo)</span>
      </div>
    </section>
  )
}
