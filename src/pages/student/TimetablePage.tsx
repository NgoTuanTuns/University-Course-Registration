import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { AlertTriangle, CalendarDays, CheckCircle2, Clock3, Eye, EyeOff, Trash2 } from 'lucide-react'
import { Link } from 'react-router-dom'
import { getTimetable } from '../../api/timetable'
import TimetableGrid from '../../features/timetable/components/TimetableGrid'
import { DEFAULT_TERM } from '../../features/timetable/timetable.mock'
import {
  clearPreviewOfferings,
  readPreviewOfferings,
  removePreviewOffering,
  subscribeToPreviewChanges,
} from '../../features/timetable/timetable.storage'
import type { TimetableOffering } from '../../features/timetable/timetable.types'
import { DAY_NAMES, findConflicts } from '../../features/timetable/timetable.utils'

export default function TimetablePage() {
  const [selectedTerm, setSelectedTerm] = useState(DEFAULT_TERM)
  const [showPreview, setShowPreview] = useState(true)
  const [previewOfferings, setPreviewOfferings] = useState<TimetableOffering[]>(() => readPreviewOfferings())
  const [enrolled, setEnrolled] = useState<TimetableOffering[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => subscribeToPreviewChanges(() => setPreviewOfferings(readPreviewOfferings())), [])

  useEffect(() => {
    let cancelled = false
    void getTimetable(selectedTerm)
      .then((items) => {
        if (!cancelled) setEnrolled(items)
      })
      .catch(() => {
        if (!cancelled) setError('Không thể tải thời khóa biểu. Vui lòng thử lại.')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [selectedTerm, reloadKey])

  function handleTermChange(term: string) {
    setSelectedTerm(term)
    setLoading(true)
    setError(null)
  }

  function handleRetry() {
    setReloadKey((current) => current + 1)
    setLoading(true)
    setError(null)
  }

  const visiblePreview = useMemo(
    () => showPreview ? previewOfferings.filter((offering) => offering.term === selectedTerm) : [],
    [previewOfferings, selectedTerm, showPreview],
  )
  const allVisibleOfferings = [...enrolled, ...visiblePreview]

  const conflicts = useMemo(() => {
    const found = new Map<string, { offering: TimetableOffering; names: string[] }>()
    for (const preview of visiblePreview) {
      const previewConflicts = findConflicts(preview, enrolled)
      if (previewConflicts.length > 0) {
        found.set(preview.offeringId, {
          offering: preview,
          names: [...new Set(previewConflicts.map((item) => `${item.code} (${item.section})`))],
        })
      }
    }
    return [...found.values()]
  }, [enrolled, visiblePreview])

  const credits = enrolled.reduce((total, offering) => total + offering.credits, 0)

  return (
    <main className="space-y-6 pb-8">
      <section className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-blue-700 via-blue-600 to-indigo-600 p-6 text-white shadow-sm sm:p-8">
        <div className="pointer-events-none absolute -right-8 -top-16 h-56 w-56 rounded-full border-[28px] border-white/10" />
        <div className="pointer-events-none absolute -bottom-24 right-24 h-44 w-44 rounded-full bg-white/10 blur-2xl" />
        <div className="relative z-10 flex flex-col justify-between gap-5 lg:flex-row lg:items-end">
          <div className="max-w-2xl">
            <div className="inline-flex items-center gap-2 rounded-full bg-white/15 px-3 py-1.5 text-xs font-semibold">
              <CalendarDays size={15} /> LỊCH HỌC CÁ NHÂN
            </div>
            <h1 className="mt-4 text-2xl font-bold tracking-tight sm:text-3xl">Thời khóa biểu tuần</h1>
            <p className="mt-2 max-w-xl text-sm leading-6 text-blue-50 sm:text-base">
              Xem lịch theo lưới ngày–giờ, thêm lớp để xem trước và nhận cảnh báo trùng lịch ngay trên trình duyệt.
            </p>
          </div>
          <label className="relative z-10 block w-full text-sm font-medium text-white lg:w-64">
            Học kỳ
            <select
              value={selectedTerm}
              onChange={(event) => handleTermChange(event.target.value)}
              className="mt-2 w-full rounded-xl border border-white/25 bg-white px-3 py-2.5 font-semibold text-slate-900 outline-none ring-blue-300 focus:ring-2"
            >
              <option value="2026-1">2026-1 · Học kỳ 1</option>
              <option value="2026-2">2026-2 · Học kỳ 2</option>
            </select>
          </label>
        </div>
      </section>

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <SummaryCard icon={<CalendarDays size={19} />} label="Lớp đã đăng ký" value={String(enrolled.length)} detail="Dữ liệu mô phỏng học kỳ" />
        <SummaryCard icon={<Clock3 size={19} />} label="Tín chỉ hiện tại" value={`${credits}`} detail="Chưa bao gồm lớp xem trước" />
        <SummaryCard icon={<Eye size={19} />} label="Lớp xem trước" value={String(visiblePreview.length)} detail="Chưa đăng ký chính thức" />
        <SummaryCard icon={<AlertTriangle size={19} />} label="Lớp xem trước bị trùng" value={String(conflicts.length)} detail={conflicts.length ? 'Cần đổi lớp hoặc giờ học' : 'Không có xung đột với lớp đã đăng ký'} warning={conflicts.length > 0} />
      </section>

      {conflicts.length > 0 && (
        <section role="alert" className="rounded-xl border border-red-300 bg-red-50 p-4 text-red-900">
          <div className="flex items-start gap-3">
            <AlertTriangle size={20} className="mt-0.5 shrink-0" />
            <div>
              <p className="font-semibold">Phát hiện trùng lịch</p>
              <ul className="mt-2 space-y-1 text-sm">
                {conflicts.map(({ offering, names }) => (
                  <li key={offering.offeringId}>
                    <strong>{offering.code} ({offering.section})</strong> trùng với {names.join(', ')}.
                  </li>
                ))}
              </ul>
              <p className="mt-2 text-xs">Cảnh báo được tính tức thì ở frontend; backend sẽ là nơi xác nhận cuối cùng khi đăng ký chính thức.</p>
            </div>
          </div>
        </section>
      )}

      {error && (
        <section role="alert" className="flex flex-col gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800 sm:flex-row sm:items-center sm:justify-between">
          <p>{error}</p>
          <button type="button" onClick={handleRetry} className="rounded-lg border border-red-200 bg-white px-3 py-2 font-semibold hover:bg-red-100">Thử lại</button>
        </section>
      )}

      {loading ? (
        <section aria-live="polite" className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-12 text-center text-sm text-[var(--muted)]">
          <Clock3 size={24} className="mx-auto mb-3 animate-pulse" />
          Đang tải thời khóa biểu...
        </section>
      ) : (
      <div className="grid items-start gap-6 2xl:grid-cols-[minmax(0,1fr)_320px]">
        <TimetableGrid offerings={allVisibleOfferings} selectedTerm={selectedTerm} />

        <aside className="space-y-4 rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-4 shadow-sm sm:p-5">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="font-semibold text-[var(--text)]">Lớp học trong kỳ</h2>
              <p className="mt-1 text-xs leading-5 text-[var(--muted)]">Danh sách lớp đã đăng ký và lớp đang xem trước.</p>
            </div>
            <button
              type="button"
              onClick={() => setShowPreview((current) => !current)}
              className="inline-flex shrink-0 items-center gap-1.5 rounded-lg border border-[var(--border)] px-2.5 py-2 text-xs font-semibold text-[var(--text)] hover:bg-[var(--hover)]"
              aria-pressed={showPreview}
            >
              {showPreview ? <EyeOff size={14} /> : <Eye size={14} />}
              {showPreview ? 'Ẩn xem trước' : 'Hiện xem trước'}
            </button>
          </div>

          <div className="space-y-3">
            {enrolled.length === 0 && visiblePreview.length === 0 ? (
              <div className="rounded-xl border border-dashed border-[var(--border)] p-5 text-center">
                <CalendarDays className="mx-auto text-[var(--muted)]" size={25} />
                <p className="mt-2 text-sm font-semibold text-[var(--text)]">Chưa có lớp trong kỳ này</p>
                <p className="mt-1 text-xs leading-5 text-[var(--muted)]">Chọn lớp ở trang tra cứu để xem trước trên lưới.</p>
              </div>
            ) : (
              <>
                {enrolled.map((offering) => (
                  <OfferingItem key={offering.offeringId} offering={offering} />
                ))}
                {visiblePreview.map((offering) => {
                  const hasConflict = findConflicts(offering, enrolled).length > 0
                  return (
                    <OfferingItem
                      key={offering.offeringId}
                      offering={offering}
                      hasConflict={hasConflict}
                      onRemove={() => removePreviewOffering(offering.offeringId)}
                    />
                  )
                })}
              </>
            )}
          </div>

          {previewOfferings.length > 0 && (
            <button
              type="button"
              onClick={clearPreviewOfferings}
              className="inline-flex w-full items-center justify-center gap-2 rounded-xl border border-[var(--border)] px-3 py-2.5 text-sm font-semibold text-[var(--muted)] transition hover:bg-[var(--hover)] hover:text-[var(--text)]"
            >
              <Trash2 size={16} /> Xóa tất cả lớp xem trước
            </button>
          )}

          <Link to="/student/courses" className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-blue-700">
            <CalendarDays size={16} /> Tra cứu và thêm lớp xem trước
          </Link>
          <p className="text-xs leading-5 text-[var(--muted)]">Lớp xem trước chỉ tồn tại trong phiên trình duyệt hiện tại, không làm thay đổi đăng ký thật.</p>
        </aside>
      </div>
      )}

      <div className="flex items-start gap-3 rounded-xl border border-blue-200 bg-blue-50 p-4 text-blue-950">
        <CheckCircle2 size={19} className="mt-0.5 shrink-0 text-blue-700" />
        <p className="text-sm leading-6">Đây là bản demo sử dụng dữ liệu mẫu. Thuật toán phát hiện xung đột không gọi server; API thời khóa biểu thật sẽ được nối khi nhóm thống nhất hợp đồng `GET /timetable` với backend.</p>
      </div>
    </main>
  )
}

function SummaryCard({ icon, label, value, detail, warning = false }: { icon: ReactNode; label: string; value: string; detail: string; warning?: boolean }) {
  return (
    <article className={`rounded-xl border bg-[var(--surface)] p-4 ${warning ? 'border-red-300' : 'border-[var(--border)]'}`}>
      <div className="flex items-center gap-2 text-[var(--muted)]">{icon}<span className="text-sm">{label}</span></div>
      <p className={`mt-3 text-2xl font-bold ${warning ? 'text-red-600' : 'text-[var(--text)]'}`}>{value}</p>
      <p className="mt-1 text-xs leading-5 text-[var(--muted)]">{detail}</p>
    </article>
  )
}

function OfferingItem({ offering, hasConflict = false, onRemove }: { offering: TimetableOffering; hasConflict?: boolean; onRemove?: () => void }) {
  return (
    <article className={`rounded-xl border p-3 ${offering.kind === 'preview' ? 'border-dashed border-indigo-300 bg-indigo-50/50' : 'border-[var(--border)]'} ${hasConflict ? 'border-red-300 bg-red-50/70' : ''}`}>
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-sm font-bold text-[var(--text)]">{offering.code}</span>
            <span className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${offering.kind === 'preview' ? 'bg-indigo-100 text-indigo-800' : 'bg-emerald-100 text-emerald-800'}`}>
              {offering.kind === 'preview' ? 'Xem trước' : 'Đã đăng ký'}
            </span>
          </div>
          <p className="mt-1 text-sm font-medium leading-5 text-[var(--text)]">{offering.name}</p>
          <p className="mt-1 text-xs text-[var(--muted)]">{offering.section} · {offering.credits} tín chỉ</p>
        </div>
        {onRemove && (
          <button type="button" onClick={onRemove} aria-label={`Bỏ xem trước ${offering.code}`} title="Bỏ lớp xem trước" className="rounded-lg p-2 text-[var(--muted)] hover:bg-white hover:text-red-600">
            <Trash2 size={15} />
          </button>
        )}
      </div>
      <div className="mt-3 space-y-1.5 text-xs text-[var(--muted)]">
        {offering.schedule.map((slot, index) => (
          <p key={`${slot.dayOfWeek}-${slot.startTime}-${index}`}>{DAY_NAMES.find((day) => day.day === slot.dayOfWeek)?.label ?? 'Chưa rõ ngày'} · {slot.startTime}–{slot.endTime} · Phòng {offering.room}</p>
        ))}
      </div>
      {hasConflict && <p className="mt-2 flex items-center gap-1.5 text-xs font-bold text-red-700"><AlertTriangle size={13} /> Có khung giờ trùng với lớp đã đăng ký</p>}
    </article>
  )
}
