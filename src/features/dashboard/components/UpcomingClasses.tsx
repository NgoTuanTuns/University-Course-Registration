import { ArrowRight, CalendarDays, Clock3, MapPin, UserRound } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { UpcomingClass } from '../dashboard.types'

interface UpcomingClassesProps {
  classes: UpcomingClass[]
}

export default function UpcomingClasses({
  classes,
}: UpcomingClassesProps) {
  return (
    <section className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-5 shadow-sm sm:p-6">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h3 className="text-lg font-bold text-[var(--text)]">
            Lịch học sắp tới
          </h3>
          <p className="mt-1 text-sm text-[var(--muted)]">
            Các buổi học trong dữ liệu demo
          </p>
        </div>

        <Link
          to="/student/timetable"
          className="inline-flex shrink-0 items-center gap-1 text-sm font-semibold text-blue-700 transition hover:text-blue-800"
        >
          Xem lịch
          <ArrowRight size={16} />
        </Link>
      </div>

      {classes.length === 0 ? (
        <div className="mt-6 rounded-xl border border-dashed border-[var(--border)] px-4 py-8 text-center">
          <CalendarDays
            size={28}
            className="mx-auto text-[var(--muted)]"
          />
          <p className="mt-3 font-medium text-[var(--text)]">
            Chưa có lịch học
          </p>
          <p className="mt-1 text-sm text-[var(--muted)]">
            Lịch học sẽ xuất hiện khi có lớp được đăng ký.
          </p>
        </div>
      ) : (
        <div className="mt-5 divide-y divide-[var(--border)]">
          {classes.map((item) => (
            <article
              key={item.id}
              className="flex flex-col gap-4 py-5 first:pt-0 last:pb-0 sm:flex-row"
            >
              <div className="flex shrink-0 items-center gap-3 sm:w-32 sm:flex-col sm:items-start sm:gap-1">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-700 sm:hidden">
                  <CalendarDays size={20} />
                </div>

                <div>
                  <p className="text-sm font-semibold text-[var(--text)]">
                    {item.dateLabel}
                  </p>
                  <p className="mt-1 flex items-center gap-1.5 text-sm font-medium text-blue-700">
                    <Clock3 size={15} />
                    {item.startTime}–{item.endTime}
                  </p>
                </div>
              </div>

              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="rounded-md bg-blue-50 px-2 py-1 text-xs font-bold text-blue-700">
                    {item.courseCode}
                  </span>
                </div>

                <h4 className="mt-2 font-semibold leading-6 text-[var(--text)]">
                  {item.courseName}
                </h4>

                <div className="mt-3 flex flex-wrap gap-x-4 gap-y-2 text-xs text-[var(--muted)]">
                  <span className="inline-flex items-center gap-1.5">
                    <MapPin size={14} />
                    {item.room}
                  </span>

                  <span className="inline-flex items-center gap-1.5">
                    <UserRound size={14} />
                    {item.lecturer}
                  </span>
                </div>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  )
}