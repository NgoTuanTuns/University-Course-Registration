import { useEffect, useMemo, useState } from 'react'
import { AlertCircle, CheckCircle2, Clock3, GraduationCap, RefreshCw, Trash2 } from 'lucide-react'
import { Link } from 'react-router-dom'
import { cancelEnrollment, getEnrollments } from '../../api/enroll'
import type { EnrollmentRecord } from '../../features/enroll/enroll.types'

export default function EnrollmentPage() {
  const [term, setTerm] = useState('2026-1')
  const [records, setRecords] = useState<EnrollmentRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [reloadKey, setReloadKey] = useState(0)
  const active = useMemo(() => records.filter((record) => record.status === 'active'), [records])
  const waitlisted = useMemo(() => records.filter((record) => record.status === 'waitlisted'), [records])
  const credits = active.reduce((sum, record) => sum + record.credits, 0)
  const percentage = Math.min(100, Math.round((credits / 25) * 100))

  useEffect(() => {
    let cancelled = false
    void getEnrollments(term).then((data) => {
      if (!cancelled) setRecords(data)
    }).catch(() => {
      if (!cancelled) setError('Không thể tải đăng ký học phần. Vui lòng thử lại.')
    }).finally(() => {
      if (!cancelled) setLoading(false)
    })
    return () => { cancelled = true }
  }, [term, reloadKey])

  async function handleCancel(record: EnrollmentRecord) {
    const confirmed = window.confirm(`Bạn có chắc muốn hủy ${record.code} – ${record.section}?`)
    if (!confirmed) return
    try {
      await cancelEnrollment(record.id)
      setMessage(`Đã hủy ${record.code} – ${record.section}.`)
      setLoading(true)
      setReloadKey((value) => value + 1)
    } catch {
      setError('Không thể hủy đăng ký lúc này. Vui lòng tải lại danh sách.')
    }
  }

  return <main className="space-y-6 pb-8">
    <section className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-blue-700 via-blue-600 to-indigo-600 p-6 text-white shadow-sm sm:p-8">
      <div className="relative z-10 flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
        <div><div className="inline-flex items-center gap-2 rounded-full bg-white/15 px-3 py-1.5 text-xs font-semibold"><GraduationCap size={15} /> QUẢN LÝ ĐĂNG KÝ</div><h1 className="mt-4 text-2xl font-bold sm:text-3xl">Đăng ký học phần</h1><p className="mt-2 max-w-2xl text-sm leading-6 text-blue-50">Theo dõi lớp đã đăng ký, tổng tín chỉ và trạng thái danh sách chờ. Hủy lớp sẽ cập nhật lại danh sách trên giao diện.</p></div>
        <label className="block text-sm font-medium">Học kỳ<select value={term} onChange={(event) => { setLoading(true); setError(null); setTerm(event.target.value) }} className="mt-2 block w-full rounded-xl border border-white/25 bg-white px-3 py-2.5 font-semibold text-slate-900 sm:w-52"><option value="2026-1">2026-1 · Học kỳ 1</option><option value="2026-2">2026-2 · Học kỳ 2</option></select></label>
      </div>
    </section>

    {message && <div role="status" className="flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800"><CheckCircle2 size={18} />{message}<button className="ml-auto font-semibold" onClick={() => setMessage(null)}>Đóng</button></div>}
    {error && <div role="alert" className="flex items-center justify-between gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800"><span>{error}</span><button onClick={() => { setLoading(true); setError(null); setReloadKey((value) => value + 1) }} className="inline-flex items-center gap-2 rounded-lg bg-white px-3 py-2 font-semibold"><RefreshCw size={15}/> Thử lại</button></div>}

    <section className="grid gap-3 sm:grid-cols-3">
      <Metric label="Lớp đã đăng ký" value={String(active.length)} detail="Trạng thái chính thức" />
      <Metric label="Tín chỉ đã đăng ký" value={`${credits}/25`} detail="Hạn mức mô phỏng mỗi học kỳ" />
      <Metric label="Lớp trong danh sách chờ" value={String(waitlisted.length)} detail="Chưa tính vào tín chỉ chính thức" />
    </section>
    <section className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5"><div className="flex items-center justify-between gap-3"><div><h2 className="font-semibold text-[var(--text)]">Tiến độ tín chỉ</h2><p className="mt-1 text-sm text-[var(--muted)]">Đã đăng ký {credits} trên 25 tín chỉ tối đa.</p></div><strong className={`text-lg ${percentage >= 100 ? 'text-red-600' : percentage >= 90 ? 'text-amber-600' : 'text-blue-700'}`}>{percentage}%</strong></div><div className="mt-4 h-3 overflow-hidden rounded-full bg-slate-100"><div className={`h-full rounded-full transition-all ${percentage >= 100 ? 'bg-red-500' : percentage >= 90 ? 'bg-amber-500' : 'bg-blue-600'}`} style={{ width: `${percentage}%` }}/></div></section>

    <section className="overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--surface)] shadow-sm"><div className="border-b border-[var(--border)] p-5"><h2 className="font-semibold text-[var(--text)]">Danh sách lớp học phần</h2><p className="mt-1 text-sm text-[var(--muted)]">Lớp chờ không được cộng vào tổng tín chỉ.</p></div>
      {loading ? <div className="p-10 text-center text-sm text-[var(--muted)]">Đang tải đăng ký...</div> : records.length === 0 ? <div className="p-10 text-center"><GraduationCap size={30} className="mx-auto text-[var(--muted)]"/><p className="mt-3 font-semibold text-[var(--text)]">Chưa có lớp đăng ký trong học kỳ này</p><Link to="/student/courses" className="mt-3 inline-flex rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white">Tra cứu học phần</Link></div> : <div className="divide-y divide-[var(--border)]">{records.map((record) => <article key={record.id} className="flex flex-col gap-4 p-4 sm:flex-row sm:items-center sm:justify-between sm:p-5"><div className="flex items-start gap-3"><div className={`mt-0.5 rounded-xl p-2 ${record.status === 'active' ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'}`}>{record.status === 'active' ? <CheckCircle2 size={20}/> : <Clock3 size={20}/>}</div><div><div className="flex flex-wrap items-center gap-2"><strong className="text-blue-700">{record.code}</strong><span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${record.status === 'active' ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'}`}>{record.status === 'active' ? 'Đã đăng ký' : `Đang chờ · vị trí ${record.position ?? 1}`}</span></div><h3 className="mt-1 font-semibold text-[var(--text)]">{record.name}</h3><p className="mt-1 text-sm text-[var(--muted)]">Lớp {record.section} · {record.credits} tín chỉ · {record.course.lecturer}</p></div></div><button type="button" onClick={() => void handleCancel(record)} className="inline-flex items-center justify-center gap-2 rounded-lg border border-red-200 px-3 py-2 text-sm font-semibold text-red-700 transition hover:bg-red-50"><Trash2 size={15}/> {record.status === 'active' ? 'Hủy đăng ký' : 'Rời hàng chờ'}</button></article>)}</div>}
    </section>
    <div className="flex items-start gap-3 rounded-xl border border-blue-200 bg-blue-50 p-4 text-sm leading-6 text-blue-950"><AlertCircle size={18} className="mt-0.5 shrink-0 text-blue-700"/><p>Bản hiện tại dùng mock API ở trình duyệt. Quyết định chính thức về điều kiện tiên quyết, tín chỉ, xung đột và danh sách chờ phải được backend xác nhận khi tích hợp.</p></div>
  </main>
}

function Metric({ label, value, detail }: { label: string; value: string; detail: string }) { return <article className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4"><p className="text-sm text-[var(--muted)]">{label}</p><p className="mt-2 text-2xl font-bold text-[var(--text)]">{value}</p><p className="mt-1 text-xs text-[var(--muted)]">{detail}</p></article> }
