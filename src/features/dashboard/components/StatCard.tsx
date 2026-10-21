import type { DashboardStat } from '../dashboard.types'

interface StatCardProps {
  stat: DashboardStat
}

export default function StatCard({ stat }: StatCardProps) {
  const Icon = stat.icon

  return (
    <article className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-medium text-[var(--muted)]">
            {stat.title}
          </p>

          <p className="mt-3 text-3xl font-bold tracking-tight text-[var(--text)]">
            {stat.value}
          </p>
        </div>

        <div
          className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ${stat.iconBackgroundClass} ${stat.iconColorClass}`}
        >
          <Icon size={22} />
        </div>
      </div>

      <p className="mt-4 text-xs leading-5 text-[var(--muted)]">
        {stat.description}
      </p>
    </article>
  )
}