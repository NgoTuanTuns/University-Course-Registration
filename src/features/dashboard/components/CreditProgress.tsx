import { GraduationCap } from 'lucide-react'
import type { CreditSummary } from '../dashboard.types'
import { getCreditPercentage } from '../dashboard.utils'

interface CreditProgressProps {
  summary: CreditSummary
}

export default function CreditProgress({
  summary,
}: CreditProgressProps) {
  const percentage = getCreditPercentage(summary.registeredCredits, summary.maxCredits)

  const remainingCredits = Math.max(
    0,
    summary.maxCredits - summary.registeredCredits,
  )

  return (
    <section className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-5 shadow-sm sm:p-6">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-[var(--muted)]">
            Tiến độ tín chỉ
          </p>

          <h3 className="mt-2 text-xl font-bold text-[var(--text)]">
            Tín chỉ học kỳ này
          </h3>
        </div>

        <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-50 text-blue-700">
          <GraduationCap size={23} />
        </div>
      </div>

      <div className="mt-6 flex items-end justify-between gap-3">
        <p className="text-3xl font-bold tracking-tight text-[var(--text)]">
          {summary.registeredCredits}
          <span className="ml-2 text-sm font-medium text-[var(--muted)]">
            / {summary.maxCredits} tín chỉ
          </span>
        </p>

        <p className="text-sm font-semibold text-blue-700">
          {percentage}%
        </p>
      </div>

      <div
        className="mt-4 h-3 overflow-hidden rounded-full bg-slate-100"
        role="progressbar"
        aria-label="Tiến độ đăng ký tín chỉ"
        aria-valuemin={0}
        aria-valuemax={summary.maxCredits}
        aria-valuenow={summary.registeredCredits}
      >
        <div
          className="h-full rounded-full bg-blue-600 transition-all duration-500"
          style={{ width: `${percentage}%` }}
        />
      </div>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-2 text-sm">
        <span className="text-[var(--muted)]">
          Đã hoàn thành trước đây: {summary.completedCredits} tín chỉ
        </span>

        <span className="font-medium text-[var(--text)]">
          Còn {remainingCredits} tín chỉ trong hạn mức
        </span>
      </div>

      <p className="mt-3 text-xs leading-5 text-[var(--muted)]">
        Số liệu minh họa. Khi tích hợp backend, hạn mức và số tín chỉ
        thực tế sẽ lấy từ dữ liệu sinh viên và các lớp đã đăng ký.
      </p>
    </section>
  )
}