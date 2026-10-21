import { useEffect, useMemo, useState } from 'react'
import { BellRing, GraduationCap, RefreshCw } from 'lucide-react'

import {
  creditSummary as initialCreditSummary,
  dashboardStats as initialDashboardStats,
  quickActions,
  studentProfile,
  upcomingClasses,
} from '../../features/dashboard/dashboard.mock'

import CreditProgress from '../../features/dashboard/components/CreditProgress'
import QuickActions from '../../features/dashboard/components/QuickActions'
import StatCard from '../../features/dashboard/components/StatCard'
import UpcomingClasses from '../../features/dashboard/components/UpcomingClasses'
import { getEnrollments } from '../../api/enroll'
import type { EnrollmentRecord } from '../../features/enroll/enroll.types'
import { getEnrollmentSummary } from '../../features/dashboard/dashboard.utils'

const CURRENT_TERM = '2026-1'
const MAX_CREDITS = 25

export default function DashboardPage() {
  const [records, setRecords] = useState<EnrollmentRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const summary = useMemo(() => getEnrollmentSummary(records), [records])

  useEffect(() => {
    let cancelled = false
    void getEnrollments(CURRENT_TERM).then((data) => {
      if (!cancelled) {
        setRecords(data)
        setError(false)
      }
    }).catch(() => {
      if (!cancelled) setError(true)
    }).finally(() => {
      if (!cancelled) setLoading(false)
    })
    return () => { cancelled = true }
  }, [])

  const dashboardStats = useMemo(() => initialDashboardStats.map((stat) => {
    if (stat.id === 'registered') return { ...stat, value: String(summary.registeredClasses) }
    if (stat.id === 'waitlist') return { ...stat, value: String(summary.waitlistedClasses) }
    return stat
  }), [summary.registeredClasses, summary.waitlistedClasses])

  const creditSummary = {
    ...initialCreditSummary,
    registeredCredits: summary.registeredCredits,
    maxCredits: MAX_CREDITS,
  }

  return (
    <div className="space-y-6">
      <section className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-blue-700 via-blue-600 to-indigo-600 p-6 text-white shadow-sm sm:p-8">
        <div className="pointer-events-none absolute -right-10 -top-16 h-56 w-56 rounded-full border-[30px] border-white/10" />
        <div className="pointer-events-none absolute -bottom-20 right-28 h-48 w-48 rounded-full bg-white/5" />
        <div className="relative flex flex-col justify-between gap-6 sm:flex-row sm:items-center">
          <div className="max-w-2xl">
            <div className="inline-flex items-center gap-2 rounded-full bg-white/15 px-3 py-1.5 text-xs font-medium text-blue-50"><GraduationCap size={16} />{studentProfile.semester}</div>
            <h2 className="mt-4 text-2xl font-bold tracking-tight sm:text-3xl">Xin chào, {studentProfile.fullName}!</h2>
            <p className="mt-3 max-w-xl text-sm leading-6 text-blue-100 sm:text-base">Chào mừng bạn quay lại UniPortal. Hãy kiểm tra tiến độ tín chỉ, lịch học và trạng thái đăng ký của mình.</p>
            <div className="mt-5 flex flex-wrap gap-x-5 gap-y-2 text-sm text-blue-100"><span>MSSV: {studentProfile.studentId}</span><span>Ngành: {studentProfile.program}</span></div>
          </div>
          <div className="hidden h-24 w-24 shrink-0 items-center justify-center rounded-3xl border border-white/20 bg-white/10 sm:flex"><GraduationCap size={54} strokeWidth={1.5} /></div>
        </div>
      </section>

      {error && <div role="alert" className="flex items-center gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800"><BellRing size={18} />Không thể tải dữ liệu đăng ký để cập nhật Dashboard. Các số liệu có thể chưa mới nhất.</div>}

      <section>
        <div className="mb-4"><h3 className="text-lg font-bold text-[var(--text)]">Tổng quan đăng ký</h3><p className="mt-1 text-sm text-[var(--muted)]">Số liệu được tính từ các đăng ký trong học kỳ hiện tại; lớp đang chờ không tính vào tín chỉ.</p></div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">{dashboardStats.map((stat) => <StatCard key={stat.id} stat={stat} />)}</div>
      </section>

      {loading ? <section className="flex items-center gap-2 rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-5 text-sm text-[var(--muted)]"><RefreshCw size={16} className="animate-spin" />Đang đồng bộ số liệu tín chỉ...</section> : <CreditProgress summary={creditSummary} />}

      <div className="grid grid-cols-1 items-start gap-6 xl:grid-cols-[1.15fr_0.85fr]"><UpcomingClasses classes={upcomingClasses} /><QuickActions actions={quickActions} /></div>

      <aside className="flex items-start gap-3 rounded-xl border border-blue-200 bg-blue-50 p-4 text-blue-950"><BellRing size={20} className="mt-0.5 shrink-0 text-blue-700" /><div><p className="text-sm font-semibold">Thông tin dành cho bản demo</p><p className="mt-1 text-sm leading-6 text-blue-900">Số lớp và tín chỉ đã đăng ký lấy từ dữ liệu mock lưu trên trình duyệt, nên sẽ thay đổi khi bạn đăng ký hoặc hủy lớp ở các trang khác. Lịch học sắp tới và số tín chỉ đã hoàn thành vẫn là dữ liệu minh họa; backend thật chưa được kết nối.</p></div></aside>
    </div>
  )
}
