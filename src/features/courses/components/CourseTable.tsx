import { BookOpen, CalendarPlus, Clock3, Users, GraduationCap } from 'lucide-react'
import type {
  CourseSearchItem,
  CourseStatus,
} from '../courses.types'

interface CourseTableProps {
  courses: CourseSearchItem[]
  loading: boolean
  onPreview: (course: CourseSearchItem) => void
  onEnroll: (course: CourseSearchItem) => void
}

const statusLabels: Record<CourseStatus, string> = {
  open: 'Đang mở',
  full: 'Đã đầy',
  closed: 'Đã đóng',
}

const statusClasses: Record<CourseStatus, string> = {
  open: 'bg-emerald-50 text-emerald-700',
  full: 'bg-amber-50 text-amber-700',
  closed: 'bg-gray-100 text-gray-600',
}

const dayNames: Record<number, string> = {
  1: 'T2',
  2: 'T3',
  3: 'T4',
  4: 'T5',
  5: 'T6',
  6: 'T7',
  7: 'CN',
}

function formatSchedule(course: CourseSearchItem): string {
  if (course.schedule.length === 0) return 'Chưa cập nhật lịch'

  return course.schedule
    .map(
      (slot) =>
        `${dayNames[slot.dayOfWeek] ?? `Thứ ${slot.dayOfWeek}`} ${slot.startTime}–${slot.endTime}`,
    )
    .join(', ')
}

export default function CourseTable({
  courses,
  loading,
  onPreview,
  onEnroll,
}: CourseTableProps) {
  return (
    <section className="overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--surface)] shadow-sm">
      <div className="flex items-center gap-3 border-b border-[var(--border)] p-4 sm:p-5">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-50 text-blue-700">
          <BookOpen size={21} />
        </div>
        <div>
          <h2 className="font-semibold text-[var(--text)]">
            Danh sách lớp học phần
          </h2>
          <p className="mt-1 text-sm text-[var(--muted)]">
            Kiểm tra thông tin lớp trước khi đăng ký.
          </p>
        </div>
      </div>

      {loading ? (
        <div className="p-12 text-center text-sm text-[var(--muted)]">
          Đang tải danh sách học phần...
        </div>
      ) : courses.length === 0 ? (
        <div className="p-12 text-center">
          <BookOpen
            size={34}
            className="mx-auto text-[var(--muted)]"
          />
          <p className="mt-3 font-semibold text-[var(--text)]">
            Không tìm thấy học phần phù hợp
          </p>
          <p className="mt-1 text-sm text-[var(--muted)]">
            Thử thay đổi từ khóa hoặc xóa bớt bộ lọc.
          </p>
        </div>
      ) : (
        <>
          <div className="hidden overflow-x-auto lg:block">
            <table className="w-full min-w-[950px] text-left text-sm">
              <thead className="bg-[var(--background)] text-xs uppercase tracking-wide text-[var(--muted)]">
                <tr>
                  <th className="px-5 py-3 font-semibold">Học phần</th>
                  <th className="px-4 py-3 font-semibold">Lớp</th>
                  <th className="px-4 py-3 font-semibold">Tín chỉ</th>
                  <th className="px-4 py-3 font-semibold">Lịch học</th>
                  <th className="px-4 py-3 font-semibold">Sĩ số</th>
                  <th className="px-4 py-3 font-semibold">Tiên quyết</th>
                  <th className="px-4 py-3 font-semibold">Trạng thái</th>
                  <th className="px-4 py-3 font-semibold">Thao tác</th>
                </tr>
              </thead>

              <tbody className="divide-y divide-[var(--border)]">
                {courses.map((course) => (
                  <tr
                    key={course.offeringId}
                    className="transition hover:bg-[var(--background)]"
                  >
                    <td className="px-5 py-4">
                      <p className="font-semibold text-blue-700">
                        {course.code}
                      </p>
                      <p className="mt-1 max-w-64 font-medium text-[var(--text)]">
                        {course.name}
                      </p>
                      <p className="mt-1 text-xs text-[var(--muted)]">
                        {course.lecturer}
                      </p>
                    </td>

                    <td className="px-4 py-4 text-[var(--text)]">
                      {course.section}
                      <p className="mt-1 text-xs text-[var(--muted)]">
                        Phòng {course.room}
                      </p>
                    </td>

                    <td className="px-4 py-4 font-medium text-[var(--text)]">
                      {course.credits}
                    </td>

                    <td className="max-w-60 px-4 py-4 text-[var(--text)]">
                      <div className="flex items-start gap-2">
                        <Clock3
                          size={16}
                          className="mt-0.5 shrink-0 text-[var(--muted)]"
                        />
                        <span>{formatSchedule(course)}</span>
                      </div>
                    </td>

                    <td className="px-4 py-4 text-[var(--text)]">
                      <div className="flex items-center gap-1.5">
                        <Users size={15} className="text-[var(--muted)]" />
                        {course.enrolled}/{course.capacity}
                      </div>
                    </td>

                    <td className="px-4 py-4">
                      {course.prerequisiteCodes.length > 0 ? (
                        <div className="flex flex-wrap gap-1">
                          {course.prerequisiteCodes.map((code) => (
                            <span
                              key={code}
                              className="rounded-md bg-violet-50 px-2 py-1 text-xs font-medium text-violet-700"
                            >
                              {code}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span className="text-[var(--muted)]">
                          Không có
                        </span>
                      )}
                    </td>

                    <td className="px-4 py-4">
                      <span
                        className={`inline-flex whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-semibold ${statusClasses[course.status]}`}
                      >
                        {statusLabels[course.status]}
                      </span>
                    </td>
                    <td className="px-4 py-4">
                      <div className="flex flex-col items-start gap-2">
                        <button
                          type="button"
                          onClick={() => onPreview(course)}
                          className="inline-flex items-center gap-1.5 whitespace-nowrap rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-xs font-semibold text-blue-700 transition hover:bg-blue-100"
                        >
                          <CalendarPlus size={14} /> Xem trước trên TKB
                        </button>
                        <button
                          type="button"
                          onClick={() => onEnroll(course)}
                          disabled={course.status === 'closed'}
                          className="inline-flex items-center gap-1.5 whitespace-nowrap rounded-lg bg-blue-600 px-3 py-2 text-xs font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300"
                        >
                          <GraduationCap size={14} /> Đăng ký
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="grid gap-3 p-3 sm:p-4 lg:hidden">
            {courses.map((course) => (
              <article
                key={course.offeringId}
                className="rounded-xl border border-[var(--border)] p-4"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-semibold text-blue-700">
                      {course.code}
                    </p>
                    <h3 className="mt-1 font-semibold text-[var(--text)]">
                      {course.name}
                    </h3>
                    <p className="mt-1 text-sm text-[var(--muted)]">
                      Lớp {course.section} · {course.credits} tín chỉ
                    </p>
                  </div>
                  <span
                    className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-semibold ${statusClasses[course.status]}`}
                  >
                    {statusLabels[course.status]}
                  </span>
                </div>

                <div className="mt-3 space-y-2 text-sm text-[var(--muted)]">
                  <p>{course.lecturer} · Phòng {course.room}</p>
                  <p>{formatSchedule(course)}</p>
                  <p>
                    Sĩ số: {course.enrolled}/{course.capacity}
                  </p>
                  <p>
                    Tiên quyết:{' '}
                    {course.prerequisiteCodes.length > 0
                      ? course.prerequisiteCodes.join(', ')
                      : 'Không có'}
                  </p>
                </div>
                <div className="mt-4 grid grid-cols-1 gap-2 sm:grid-cols-2">
                  <button
                    type="button"
                    onClick={() => onPreview(course)}
                    className="inline-flex w-full items-center justify-center gap-2 rounded-lg border border-blue-200 bg-blue-50 px-3 py-2.5 text-sm font-semibold text-blue-700 transition hover:bg-blue-100"
                  >
                    <CalendarPlus size={16} /> Xem trước TKB
                  </button>
                  <button
                    type="button"
                    onClick={() => onEnroll(course)}
                    disabled={course.status === 'closed'}
                    className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-3 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300"
                  >
                    <GraduationCap size={16} /> Đăng ký
                  </button>
                </div>
              </article>
            ))}
          </div>
        </>
      )}
    </section>
  )
}