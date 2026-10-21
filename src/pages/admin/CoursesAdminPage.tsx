import { useCallback, useEffect, useMemo, useState } from 'react'
import { AlertCircle, BookOpen, CheckCircle2, Edit3, Plus, RefreshCw, Search, Trash2, X } from 'lucide-react'
import { deleteAdminCourse, listAdminCourses, saveAdminCourse, type CourseAdminInput } from '../../api/adminCourses'
import type { CourseSearchItem } from '../../features/courses/courses.types'

const emptyForm: CourseAdminInput = {
  code: '', name: '', credits: 3, term: '2026-2', section: '', lecturer: '', room: '',
  capacity: 40, enrolled: 0, status: 'open', dayOfWeek: 2, startTime: '07:30', endTime: '09:30',
  prerequisiteCodes: [], description: '',
}

const inputClass = 'mt-1.5 w-full rounded-xl border border-[var(--border)] bg-[var(--surface)] px-3 py-2.5 text-sm text-[var(--text)] outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-500/15'
const labelClass = 'block text-sm font-medium text-[var(--text)]'

export default function CoursesAdminPage() {
  const [courses, setCourses] = useState<CourseSearchItem[]>([])
  const [loading, setLoading] = useState(true)
  const [query, setQuery] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [editingId, setEditingId] = useState<string | undefined>()
  const [form, setForm] = useState<CourseAdminInput>(emptyForm)
  const [prerequisiteText, setPrerequisiteText] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try { setCourses(await listAdminCourses()) }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Không thể tải danh sách học phần.') }
    finally { setLoading(false) }
  }, [])

  useEffect(() => {
    let cancelled = false
    listAdminCourses().then((items) => {
      if (!cancelled) setCourses(items)
    }).catch((cause: unknown) => {
      if (!cancelled) setError(cause instanceof Error ? cause.message : 'Không thể tải danh sách học phần.')
    }).finally(() => {
      if (!cancelled) setLoading(false)
    })
    return () => { cancelled = true }
  }, [])

  const filtered = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase('vi')
    return courses.filter((course) => !needle || [course.code, course.name, course.section, course.lecturer].some((value) => value.toLocaleLowerCase('vi').includes(needle)))
  }, [courses, query])

  function openCreate() {
    setEditingId(undefined); setForm({ ...emptyForm }); setPrerequisiteText(''); setError(null); setNotice(null); setModalOpen(true)
  }

  function openEdit(course: CourseSearchItem) {
    const slot = course.schedule[0]
    setEditingId(course.id)
    setForm({
      code: course.code, name: course.name, credits: course.credits, term: course.term, section: course.section,
      lecturer: course.lecturer, room: course.room, capacity: course.capacity, enrolled: course.enrolled,
      status: course.status, dayOfWeek: slot?.dayOfWeek ?? 2, startTime: slot?.startTime ?? '07:30', endTime: slot?.endTime ?? '09:30',
      prerequisiteCodes: [...course.prerequisiteCodes], description: course.description,
    })
    setPrerequisiteText(course.prerequisiteCodes.join(', ')); setError(null); setNotice(null); setModalOpen(true)
  }

  function update<K extends keyof CourseAdminInput>(key: K, value: CourseAdminInput[K]) {
    setForm((current) => ({ ...current, [key]: value }))
  }

  async function handleSave(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSaving(true); setError(null); setNotice(null)
    try {
      const saved = await saveAdminCourse({ ...form, prerequisiteCodes: prerequisiteText.split(',').map((code) => code.trim().toUpperCase()).filter(Boolean) }, editingId)
      setNotice(editingId ? `Đã cập nhật học phần ${saved.code}.` : `Đã thêm học phần ${saved.code}.`)
      setModalOpen(false)
      await load()
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Không thể lưu học phần.') }
    finally { setSaving(false) }
  }

  async function handleDelete(course: CourseSearchItem) {
    if (!window.confirm(`Bạn có chắc muốn xóa lớp ${course.code} – ${course.section}? Thao tác này không thể hoàn tác.`)) return
    setError(null); setNotice(null)
    try { await deleteAdminCourse(course.id); setNotice(`Đã xóa lớp ${course.code} – ${course.section}.`); await load() }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Không thể xóa học phần.') }
  }

  return <main className="space-y-6 pb-8">
    <section className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-slate-900 via-blue-900 to-indigo-800 p-6 text-white shadow-sm sm:p-8">
      <div className="relative z-10 flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
        <div className="max-w-2xl"><div className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1.5 text-xs font-semibold"><BookOpen size={14}/> QUẢN TRỊ HỌC PHẦN</div><h1 className="mt-4 text-2xl font-bold tracking-tight sm:text-3xl">Quản lý học phần</h1><p className="mt-2 text-sm leading-6 text-blue-100 sm:text-base">Thêm, chỉnh sửa và quản lý thông tin học phần/lớp mở trong danh mục demo.</p></div>
        <button type="button" onClick={openCreate} className="inline-flex shrink-0 items-center justify-center gap-2 rounded-xl bg-white px-4 py-3 text-sm font-semibold text-blue-900 transition hover:bg-blue-50"><Plus size={17}/> Thêm học phần</button>
      </div><div className="pointer-events-none absolute -right-10 -top-16 h-56 w-56 rounded-full border-[28px] border-white/5"/>
    </section>

    <section className="grid gap-3 sm:grid-cols-3">
      {[{label:'Tổng số lớp',value:courses.length},{label:'Đang mở',value:courses.filter((course) => course.status === 'open').length},{label:'Đã đầy',value:courses.filter((course) => course.status === 'full').length}].map((item) => <div key={item.label} className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4"><p className="text-sm text-[var(--muted)]">{item.label}</p><p className="mt-2 text-2xl font-bold text-[var(--text)]">{item.value}</p></div>)}
    </section>

    {notice && <div role="status" className="flex items-start gap-2 rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-900"><CheckCircle2 size={18} className="mt-0.5 shrink-0"/><p>{notice}</p><button aria-label="Đóng thông báo" className="ml-auto" onClick={() => setNotice(null)}><X size={16}/></button></div>}
    {error && !modalOpen && <div role="alert" className="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-900"><AlertCircle size={18} className="mt-0.5 shrink-0"/><p>{error}</p><button type="button" className="ml-auto underline" onClick={() => void load()}>Tải lại</button></div>}

    <section className="overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--surface)]">
      <div className="flex flex-col gap-3 border-b border-[var(--border)] p-4 sm:flex-row sm:items-center sm:justify-between"><div><h2 className="font-semibold text-[var(--text)]">Danh mục học phần</h2><p className="mt-1 text-sm text-[var(--muted)]">{filtered.length} kết quả · Dữ liệu mock được chia sẻ với trang tra cứu sinh viên</p></div><div className="flex gap-2"><div className="relative min-w-0 flex-1 sm:w-72"><Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted)]"/><input aria-label="Tìm học phần" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Tìm mã, tên, lớp, giảng viên..." className={`${inputClass} mt-0 pl-9`}/></div><button type="button" aria-label="Làm mới danh sách" onClick={() => void load()} className="rounded-xl border border-[var(--border)] px-3 text-[var(--muted)] hover:bg-[var(--hover)]"><RefreshCw size={17}/></button></div></div>
      {loading ? <div className="p-12 text-center text-sm text-[var(--muted)]">Đang tải danh sách học phần...</div> : filtered.length === 0 ? <div className="p-12 text-center"><BookOpen size={28} className="mx-auto text-[var(--muted)]"/><p className="mt-3 font-semibold text-[var(--text)]">Không tìm thấy học phần</p><p className="mt-1 text-sm text-[var(--muted)]">Thử từ khóa khác hoặc thêm học phần mới.</p></div> : <div className="overflow-x-auto"><table className="w-full min-w-[900px] text-left text-sm"><thead className="bg-[var(--background)] text-xs uppercase tracking-wide text-[var(--muted)]"><tr><th className="px-4 py-3 font-semibold">Học phần</th><th className="px-4 py-3 font-semibold">Lớp / Học kỳ</th><th className="px-4 py-3 font-semibold">Tín chỉ</th><th className="px-4 py-3 font-semibold">Sĩ số</th><th className="px-4 py-3 font-semibold">Trạng thái</th><th className="px-4 py-3 text-right font-semibold">Thao tác</th></tr></thead><tbody className="divide-y divide-[var(--border)]">{filtered.map((course) => <tr key={course.id} className="transition hover:bg-[var(--hover)]"><td className="px-4 py-4"><p className="font-semibold text-[var(--text)]">{course.code} · {course.name}</p><p className="mt-1 max-w-sm truncate text-xs text-[var(--muted)]">{course.description || 'Chưa có mô tả'}</p></td><td className="px-4 py-4"><p className="font-medium text-[var(--text)]">{course.section}</p><p className="mt-1 text-xs text-[var(--muted)]">Kỳ {course.term}</p></td><td className="px-4 py-4 text-[var(--text)]">{course.credits}</td><td className="px-4 py-4 text-[var(--text)]">{course.enrolled}/{course.capacity}</td><td className="px-4 py-4"><span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${course.status === 'open' ? 'bg-emerald-50 text-emerald-700' : course.status === 'full' ? 'bg-amber-50 text-amber-700' : 'bg-slate-100 text-slate-600'}`}>{course.status === 'open' ? 'Đang mở' : course.status === 'full' ? 'Đã đầy' : 'Đã đóng'}</span></td><td className="px-4 py-4"><div className="flex justify-end gap-2"><button type="button" onClick={() => openEdit(course)} className="inline-flex items-center gap-1.5 rounded-lg border border-[var(--border)] px-3 py-2 text-xs font-semibold text-[var(--text)] hover:bg-[var(--hover)]"><Edit3 size={14}/> Sửa</button><button type="button" onClick={() => void handleDelete(course)} className="inline-flex items-center gap-1.5 rounded-lg border border-red-200 px-3 py-2 text-xs font-semibold text-red-700 hover:bg-red-50"><Trash2 size={14}/> Xóa</button></div></td></tr>)}</tbody></table></div>}
    </section>

    {modalOpen && <div className="fixed inset-0 z-[90] flex items-center justify-center bg-slate-950/55 p-3 sm:p-5" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget && !saving) setModalOpen(false) }}><section role="dialog" aria-modal="true" aria-labelledby="course-modal-title" className="max-h-[94vh] w-full max-w-3xl overflow-y-auto rounded-2xl border border-[var(--border)] bg-[var(--surface)] shadow-2xl"><div className="sticky top-0 z-10 flex items-start justify-between gap-3 border-b border-[var(--border)] bg-[var(--surface)] p-5"><div><p className="text-xs font-semibold uppercase tracking-wide text-blue-600">Danh mục học phần</p><h2 id="course-modal-title" className="mt-1 text-xl font-bold text-[var(--text)]">{editingId ? 'Chỉnh sửa học phần' : 'Thêm học phần mới'}</h2><p className="mt-1 text-sm text-[var(--muted)]">Các trường có dấu * là bắt buộc.</p></div><button type="button" aria-label="Đóng biểu mẫu" disabled={saving} onClick={() => setModalOpen(false)} className="rounded-lg p-2 text-[var(--muted)] hover:bg-[var(--hover)]"><X size={19}/></button></div>
      <form onSubmit={(event) => void handleSave(event)} className="space-y-5 p-5">
        {error && <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-900">{error}</div>}
        <div className="grid gap-4 sm:grid-cols-2"><label className={labelClass}>Mã học phần *<input required maxLength={12} value={form.code} onChange={(event) => update('code', event.target.value.toUpperCase())} placeholder="VD: WEB301" className={inputClass}/></label><label className={labelClass}>Tên học phần *<input required maxLength={120} value={form.name} onChange={(event) => update('name', event.target.value)} placeholder="Tên học phần" className={inputClass}/></label><label className={labelClass}>Số tín chỉ *<input required type="number" min={1} max={10} value={form.credits} onChange={(event) => update('credits', Number(event.target.value))} className={inputClass}/></label><label className={labelClass}>Học kỳ *<input required value={form.term} onChange={(event) => update('term', event.target.value)} placeholder="2026-2" className={inputClass}/></label><label className={labelClass}>Mã lớp *<input required value={form.section} onChange={(event) => update('section', event.target.value)} placeholder="WEB301.01" className={inputClass}/></label><label className={labelClass}>Giảng viên<input value={form.lecturer} onChange={(event) => update('lecturer', event.target.value)} className={inputClass}/></label><label className={labelClass}>Phòng học<input value={form.room} onChange={(event) => update('room', event.target.value)} className={inputClass}/></label><label className={labelClass}>Trạng thái<select value={form.status} onChange={(event) => update('status', event.target.value as CourseAdminInput['status'])} className={inputClass}><option value="open">Đang mở</option><option value="full">Đã đầy</option><option value="closed">Đã đóng</option></select></label><label className={labelClass}>Sĩ số tối đa *<input required type="number" min={1} value={form.capacity} onChange={(event) => update('capacity', Number(event.target.value))} className={inputClass}/></label><label className={labelClass}>Sĩ số hiện tại *<input required type="number" min={0} max={form.capacity} value={form.enrolled} onChange={(event) => update('enrolled', Number(event.target.value))} className={inputClass}/></label></div>
        <div><p className="text-sm font-semibold text-[var(--text)]">Lịch học chính *</p><div className="mt-2 grid gap-3 sm:grid-cols-3"><label className={labelClass}>Thứ<select value={form.dayOfWeek} onChange={(event) => update('dayOfWeek', Number(event.target.value))} className={inputClass}>{[{value:1,label:'Thứ Hai'},{value:2,label:'Thứ Ba'},{value:3,label:'Thứ Tư'},{value:4,label:'Thứ Năm'},{value:5,label:'Thứ Sáu'},{value:6,label:'Thứ Bảy'},{value:7,label:'Chủ nhật'}].map((day) => <option key={day.value} value={day.value}>{day.label}</option>)}</select></label><label className={labelClass}>Bắt đầu<input required type="time" value={form.startTime} onChange={(event) => update('startTime', event.target.value)} className={inputClass}/></label><label className={labelClass}>Kết thúc<input required type="time" min={form.startTime} value={form.endTime} onChange={(event) => update('endTime', event.target.value)} className={inputClass}/></label></div><p className="mt-2 text-xs text-[var(--muted)]">Bản demo hiện nhập một buổi học cho mỗi lớp; lớp nhiều buổi có thể được mở rộng khi chốt API.</p></div>
        <label className={labelClass}>Môn tiên quyết<input value={prerequisiteText} onChange={(event) => setPrerequisiteText(event.target.value)} placeholder="INT101, MAT101" className={inputClass}/><span className="mt-1 block text-xs font-normal text-[var(--muted)]">Nhập mã môn, phân tách bằng dấu phẩy.</span></label>
        <label className={labelClass}>Mô tả<textarea rows={3} value={form.description} onChange={(event) => update('description', event.target.value)} placeholder="Mô tả ngắn về nội dung học phần..." className={inputClass}/></label>
        <div className="flex flex-col-reverse gap-2 border-t border-[var(--border)] pt-4 sm:flex-row sm:justify-end"><button type="button" disabled={saving} onClick={() => setModalOpen(false)} className="rounded-xl border border-[var(--border)] px-4 py-2.5 text-sm font-semibold text-[var(--text)] hover:bg-[var(--hover)]">Hủy</button><button type="submit" disabled={saving} className="rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-wait disabled:opacity-60">{saving ? 'Đang lưu...' : editingId ? 'Lưu thay đổi' : 'Thêm học phần'}</button></div>
      </form></section></div>}
  </main>
}
