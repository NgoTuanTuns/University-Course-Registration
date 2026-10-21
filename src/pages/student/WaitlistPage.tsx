import { useCallback, useEffect, useMemo, useState } from 'react'
import { AlertCircle, ArrowRight, Clock3, ListChecks, RefreshCw, Trash2 } from 'lucide-react'
import { Link } from 'react-router-dom'
import { cancelEnrollment, getEnrollments } from '../../api/enroll'
import type { EnrollmentRecord } from '../../features/enroll/enroll.types'
import { formatEnqueuedAt, sortWaitlistRecords } from '../../features/waitlist/waitlist.utils'

const TERM = '2026-1'

export default function WaitlistPage() {
  const [records, setRecords] = useState<EnrollmentRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [busyId, setBusyId] = useState<string | null>(null)
  const [reloadKey, setReloadKey] = useState(0)

  const load = useCallback(async () => {
    setError(null)
    try {
      const data = await getEnrollments(TERM)
      setRecords(data)
    } catch {
      setError('Không thể tải danh sách chờ. Vui lòng thử lại.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    void getEnrollments(TERM).then((data) => {
      if (!cancelled) setRecords(data)
    }).catch(() => {
      if (!cancelled) setError('Không thể tải danh sách chờ. Vui lòng thử lại.')
    }).finally(() => {
      if (!cancelled) setLoading(false)
    })
    return () => { cancelled = true }
  }, [reloadKey])

  const waitlisted = useMemo(() => sortWaitlistRecords(records), [records])

  async function handleLeave(record: EnrollmentRecord) {
    if (!window.confirm(`Bạn có chắc muốn rời danh sách chờ của ${record.code} – ${record.section}?`)) return
    setBusyId(record.id)
    setError(null)
    setMessage(null)
    try {
      await cancelEnrollment(record.id)
      setMessage(`Đã rời danh sách chờ của ${record.code} – ${record.section}.`)
      setLoading(true)
      setReloadKey((value) => value + 1)
    } catch {
      setError('Không thể rời danh sách chờ lúc này. Hãy tải lại danh sách và thử lại.')
    } finally {
      setBusyId(null)
    }
  }

  async function handleRefresh() {
    setLoading(true)
    await load()
  }

  return <main className="space-y-6 pb-8">
    <section className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-amber-600 via-orange-500 to-rose-500 p-6 text-white shadow-sm sm:p-8">
      <div className="pointer-events-none absolute -right-8 -top-12 h-48 w-48 rounded-full border-[24px] border-white/10" />
      <div className="relative z-10 flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
        <div>
          <div className="inline-flex items-center gap-2 rounded-full bg-white/15 px-3 py-1.5 text-xs font-semibold"><ListChecks size={15} /> THEO DÕI HÀNG CHỜ</div>
          <h1 className="mt-4 text-2xl font-bold sm:text-3xl">Danh sách chờ</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-orange-50">Theo dõi vị trí và thời điểm đăng ký chờ của từng lớp. Lớp đang chờ chưa được tính vào tổng tín chỉ chính thức.</p>
        </div>
        <button type="button" onClick={() => void handleRefresh()} disabled={loading} className="inline-flex items-center justify-center gap-2 rounded-xl border border-white/30 bg-white/10 px-4 py-2.5 text-sm font-semibold transition hover:bg-white/20 disabled:cursor-not-allowed disabled:opacity-60"><RefreshCw size={16} className={loading ? 'animate-spin' : ''} /> Làm mới</button>
      </div>
    </section>

    {message && <div role="status" className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">{message}</div>}
    {error && <div role="alert" className="flex items-center justify-between gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800"><span>{error}</span><button type="button" onClick={() => { setLoading(true); setReloadKey((value) => value + 1) }} className="inline-flex shrink-0 items-center gap-2 rounded-lg bg-white px-3 py-2 font-semibold"><RefreshCw size={15} /> Thử lại</button></div>}

    <section className="grid gap-3 sm:grid-cols-3">
      <Metric label="Lớp đang chờ" value={String(waitlisted.length)} detail="Các lớp chưa có suất chính thức" />
      <Metric label="Vị trí gần nhất" value={waitlisted.length ? `#${Math.min(...waitlisted.map((item) => item.position ?? 1))}` : '—'} detail="Vị trí do dữ liệu đăng ký cung cấp" />
      <Metric label="Học kỳ" value="2026-1" detail="Học kỳ 1 · Năm học 2026–2027" />
    </section>

    <section className="overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--surface)] shadow-sm">
      <div className="border-b border-[var(--border)] p-5"><h2 className="font-semibold text-[var(--text)]">Các lớp đang chờ</h2><p className="mt-1 text-sm text-[var(--muted)]">Thứ tự hiển thị dựa trên vị trí hàng chờ, sau đó là thời điểm vào hàng.</p></div>
      {loading ? <div className="p-10 text-center text-sm text-[var(--muted)]">Đang tải danh sách chờ...</div> : waitlisted.length === 0 ? <div className="p-10 text-center"><div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-700"><ListChecks size={28} /></div><h3 className="mt-4 font-semibold text-[var(--text)]">Bạn chưa có lớp nào trong danh sách chờ</h3><p className="mx-auto mt-2 max-w-md text-sm leading-6 text-[var(--muted)]">Khi một lớp đã đầy nhưng vẫn nhận đăng ký chờ, lớp đó sẽ xuất hiện tại đây.</p><Link to="/student/courses" className="mt-4 inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-700">Tra cứu học phần <ArrowRight size={16} /></Link></div> : <div className="divide-y divide-[var(--border)]">{waitlisted.map((record) => <article key={record.id} className="flex flex-col gap-4 p-4 sm:flex-row sm:items-center sm:justify-between sm:p-5"><div className="flex min-w-0 items-start gap-3"><div className="mt-0.5 rounded-xl bg-amber-50 p-2.5 text-amber-700"><Clock3 size={21} /></div><div className="min-w-0"><div className="flex flex-wrap items-center gap-2"><strong className="text-blue-700">{record.code}</strong><span className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-800">Đang chờ · vị trí {record.position ?? 1}</span></div><h3 className="mt-1 font-semibold text-[var(--text)]">{record.name}</h3><p className="mt-1 text-sm text-[var(--muted)]">Lớp {record.section} · {record.credits} tín chỉ · {record.course.lecturer}</p><p className="mt-2 text-xs text-[var(--muted)]">Vào hàng chờ: {formatEnqueuedAt(record.enrolledAt)}</p></div></div><button type="button" onClick={() => void handleLeave(record)} disabled={busyId === record.id} className="inline-flex shrink-0 items-center justify-center gap-2 rounded-lg border border-red-200 px-3 py-2 text-sm font-semibold text-red-700 transition hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-50"><Trash2 size={15} />{busyId === record.id ? 'Đang xử lý...' : 'Rời hàng chờ'}</button></article>)}</div>}
    </section>

    <aside className="flex items-start gap-3 rounded-xl border border-blue-200 bg-blue-50 p-4 text-sm leading-6 text-blue-950"><AlertCircle size={18} className="mt-0.5 shrink-0 text-blue-700" /><div><p className="font-semibold">Lưu ý về trạng thái hàng chờ</p><p className="mt-1">Khi backend xác nhận bạn đã được đôn lên lớp chính thức, trạng thái sẽ chuyển thành “Đã đăng ký”; lớp đó sẽ không còn nằm trong danh sách chờ và sẽ được tính vào tín chỉ cũng như thời khóa biểu. Bản demo hiện dùng dữ liệu lưu trên trình duyệt, chưa mô phỏng tự động đôn hàng chờ.</p></div></aside>
  </main>
}

function Metric({ label, value, detail }: { label: string; value: string; detail: string }) {
  return <article className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4"><p className="text-sm text-[var(--muted)]">{label}</p><p className="mt-2 text-2xl font-bold text-[var(--text)]">{value}</p><p className="mt-1 text-xs text-[var(--muted)]">{detail}</p></article>
}
