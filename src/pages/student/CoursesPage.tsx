import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AlertTriangle, BookOpen, CheckCircle2, RefreshCw, Search, X } from 'lucide-react'
import { searchCourses } from '../../api/courses'
import CourseFilters from '../../features/courses/components/CourseFilters'
import CoursePagination from '../../features/courses/components/CoursePagination'
import CourseTable from '../../features/courses/components/CourseTable'
import { addPreviewOffering } from '../../features/timetable/timetable.storage'
import { registerCourse } from '../../api/enroll'
import { EnrollmentError } from '../../features/enroll/enroll.types'
import type { CourseSearchItem } from '../../features/courses/courses.types'
import type {
  CourseSearchFilters,
  CourseSearchResponse,
} from '../../features/courses/courses.types'

const initialFilters: CourseSearchFilters = {
  keyword: '',
  section: '',
  credits: 'all',
  term: 'all',
  dayOfWeek: 'all',
  page: 1,
  pageSize: 5,
}

export default function CoursesPage() {
  const navigate = useNavigate()
  const [filters, setFilters] =
    useState<CourseSearchFilters>(initialFilters)

  const [result, setResult] = useState<CourseSearchResponse>({
    items: [],
    total: 0,
    page: 1,
    pageSize: 5,
    totalPages: 0,
  })

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [reloadKey, setReloadKey] = useState(0)
  const [selectedCourse, setSelectedCourse] = useState<CourseSearchItem | null>(null)
  const [enrolling, setEnrolling] = useState(false)
  const [enrollError, setEnrollError] = useState<{ message: string; codes: string[] } | null>(null)
  const [enrollSuccess, setEnrollSuccess] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    async function loadCourses() {
      setLoading(true)
      setError(null)

      try {
        const data = await searchCourses(filters)

        if (!cancelled) {
          setResult(data)
        }
      } catch (err: unknown) {
        if (!cancelled) {
          setError(
            err instanceof Error
              ? err.message
              : 'Không thể tải danh sách học phần.',
          )
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    void loadCourses()

    return () => {
      cancelled = true
    }
  }, [filters, reloadKey])

  function handleFilterChange(next: CourseSearchFilters) {
    setFilters(next)
  }

  function handleReset() {
    setFilters({ ...initialFilters })
  }

  function handlePageChange(page: number) {
    setFilters((current) => ({
      ...current,
      page,
    }))
  }

  function handlePageSizeChange(pageSize: number) {
    setFilters((current) => ({
      ...current,
      page: 1,
      pageSize,
    }))
  }

  function handlePreviewCourse(course: CourseSearchItem) {
    addPreviewOffering(course)
    navigate('/student/timetable')
  }

  async function handleConfirmEnrollment() {
    if (!selectedCourse || enrolling) return
    setEnrolling(true)
    setEnrollError(null)
    setEnrollSuccess(null)
    // UUID acts as the idempotency key for this enrollment attempt.
    const idempotencyKey = typeof crypto !== 'undefined' && 'randomUUID' in crypto
      ? crypto.randomUUID()
      : `${selectedCourse.offeringId}-${Date.now()}`
    try {
      const record = await registerCourse(selectedCourse, idempotencyKey)
      setEnrollSuccess(record.status === 'waitlisted'
        ? `${record.code} đã đầy; bạn đã được đưa vào danh sách chờ ở vị trí ${record.position ?? 1}.`
        : `Đăng ký ${record.code} – ${record.section} thành công.`)
      setSelectedCourse(null)
    } catch (error: unknown) {
      if (error instanceof EnrollmentError) {
        setEnrollError({ message: error.message, codes: error.relatedCodes })
      } else {
        setEnrollError({ message: 'Không thể hoàn tất đăng ký. Vui lòng thử lại.', codes: [] })
      }
    } finally {
      setEnrolling(false)
    }
  }

  return (
    <main className="space-y-6 pb-8">
      <section className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-blue-700 via-blue-600 to-indigo-600 p-6 text-white shadow-sm sm:p-8">
        <div className="relative z-10 max-w-2xl">
          <div className="inline-flex items-center gap-2 rounded-full bg-white/15 px-3 py-1.5 text-xs font-semibold">
            <BookOpen size={15} />
            CỔNG ĐĂNG KÝ HỌC PHẦN
          </div>

          <h1 className="mt-4 text-2xl font-bold tracking-tight sm:text-3xl">
            Tra cứu học phần
          </h1>

          <p className="mt-2 max-w-xl text-sm leading-6 text-blue-50 sm:text-base">
            Tìm lớp học phù hợp với kế hoạch học tập của bạn.
            Xem tín chỉ, lịch học, sĩ số và điều kiện tiên quyết
            trước khi đăng ký.
          </p>
        </div>

        <div className="pointer-events-none absolute -right-8 -top-16 h-56 w-56 rounded-full border-[28px] border-white/10" />
        <div className="pointer-events-none absolute -bottom-24 right-24 h-44 w-44 rounded-full bg-white/10 blur-2xl" />
      </section>

      <section className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
          <p className="text-sm text-[var(--muted)]">
            Tổng lớp phù hợp
          </p>
          <p className="mt-2 text-2xl font-bold text-[var(--text)]">
            {result.total}
          </p>
        </div>

        <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
          <p className="text-sm text-[var(--muted)]">
            Đang mở đăng ký
          </p>
          <p className="mt-2 text-2xl font-bold text-emerald-600">
            {result.items.filter((item) => item.status === 'open').length}
          </p>
          <p className="mt-1 text-xs text-[var(--muted)]">
            Trong trang kết quả hiện tại
          </p>
        </div>

        <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
          <p className="text-sm text-[var(--muted)]">
            Số trang kết quả
          </p>
          <p className="mt-2 text-2xl font-bold text-[var(--text)]">
            {Math.max(result.totalPages, 1)}
          </p>
        </div>
      </section>

      <CourseFilters
        filters={filters}
        onChange={handleFilterChange}
        onReset={handleReset}
      />

      {error && (
        <section
          role="alert"
          className="flex flex-col gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800 sm:flex-row sm:items-center sm:justify-between"
        >
          <div>
            <p className="font-semibold">
              Không tải được danh sách học phần
            </p>
            <p className="mt-1 break-words">{error}</p>
          </div>

          <button
            type="button"
            onClick={() => setReloadKey((current) => current + 1)}
            className="inline-flex shrink-0 items-center justify-center gap-2 rounded-lg border border-red-200 bg-white px-3 py-2 font-medium transition hover:bg-red-100"
          >
            <RefreshCw size={15} />
            Thử lại
          </button>
        </section>
      )}

      {enrollSuccess && <section role="status" className="flex items-start gap-3 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900"><CheckCircle2 size={19} className="mt-0.5 shrink-0"/><div className="flex-1"><p className="font-semibold">Kết quả đăng ký</p><p className="mt-1">{enrollSuccess}</p><button type="button" onClick={() => navigate('/student/enrollment')} className="mt-2 font-semibold underline">Xem đăng ký của tôi</button></div><button aria-label="Đóng thông báo" onClick={() => setEnrollSuccess(null)}><X size={17}/></button></section>}

      <CourseTable
        courses={result.items}
        loading={loading}
        onPreview={handlePreviewCourse}
        onEnroll={(course) => { setSelectedCourse(course); setEnrollError(null); setEnrollSuccess(null) }}
      />

      {!error && (
        <CoursePagination
          page={result.page}
          pageSize={result.pageSize}
          total={result.total}
          totalPages={result.totalPages}
          onPageChange={handlePageChange}
          onPageSizeChange={handlePageSizeChange}
        />
      )}

      {selectedCourse && <div className="fixed inset-0 z-[80] flex items-center justify-center bg-slate-950/50 p-4" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget && !enrolling) setSelectedCourse(null) }}>
        <section role="dialog" aria-modal="true" aria-labelledby="enrollment-dialog-title" className="w-full max-w-lg rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-5 shadow-2xl sm:p-6">
          <div className="flex items-start justify-between gap-3"><div><p className="text-xs font-semibold uppercase tracking-wide text-blue-700">Xác nhận đăng ký</p><h2 id="enrollment-dialog-title" className="mt-1 text-xl font-bold text-[var(--text)]">{selectedCourse.code} · {selectedCourse.name}</h2></div><button type="button" aria-label="Đóng" disabled={enrolling} onClick={() => setSelectedCourse(null)} className="rounded-lg p-2 text-[var(--muted)] hover:bg-[var(--hover)]"><X size={18}/></button></div>
          <div className="mt-4 space-y-2 rounded-xl bg-[var(--background)] p-4 text-sm text-[var(--text)]"><p><strong>Lớp:</strong> {selectedCourse.section}</p><p><strong>Tín chỉ:</strong> {selectedCourse.credits}</p><p><strong>Giảng viên:</strong> {selectedCourse.lecturer}</p><p><strong>Lịch học:</strong> {selectedCourse.schedule.map((slot) => `Thứ ${slot.dayOfWeek === 7 ? 'CN' : slot.dayOfWeek + 1}, ${slot.startTime}–${slot.endTime}`).join(' · ')}</p><p><strong>Sĩ số:</strong> {selectedCourse.enrolled}/{selectedCourse.capacity}</p></div>
          {enrollError && <div role="alert" className="mt-4 rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-950"><div className="flex items-start gap-2"><AlertTriangle size={18} className="mt-0.5 shrink-0"/><div><p className="font-semibold">Chưa thể đăng ký</p><p className="mt-1 leading-6">{enrollError.message}</p>{enrollError.codes.length > 0 && <p className="mt-2">Môn còn thiếu: <strong>{enrollError.codes.join(', ')}</strong></p>}<button type="button" onClick={() => { setSelectedCourse(null); navigate('/student/prerequisites') }} className="mt-2 font-semibold underline">Xem điều kiện tiên quyết</button></div></div></div>}
          <p className="mt-4 text-xs leading-5 text-[var(--muted)]">Hệ thống sẽ kiểm tra tiên quyết, trùng lịch và hạn mức tín chỉ trước khi ghi nhận. Lớp đã đầy sẽ được đưa vào danh sách chờ theo dữ liệu mô phỏng.</p>
          <div className="mt-5 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end"><button type="button" disabled={enrolling} onClick={() => setSelectedCourse(null)} className="rounded-xl border border-[var(--border)] px-4 py-2.5 text-sm font-semibold text-[var(--text)] hover:bg-[var(--hover)]">Để sau</button><button type="button" disabled={enrolling} onClick={() => void handleConfirmEnrollment()} className="rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-wait disabled:opacity-60">{enrolling ? 'Đang kiểm tra...' : 'Xác nhận đăng ký'}</button></div>
        </section>
      </div>}

      <p className="flex items-start gap-2 text-xs leading-5 text-[var(--muted)]">
        <Search size={15} className="mt-0.5 shrink-0" />
        Dữ liệu hiện tại dùng để minh họa giao diện. Trạng thái đủ
        điều kiện và quyết định đăng ký chính thức sẽ được xác nhận
        bởi backend khi tích hợp.
      </p>
    </main>
  )
}