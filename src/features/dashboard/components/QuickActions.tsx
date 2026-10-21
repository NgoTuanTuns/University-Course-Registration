import { ArrowUpRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { QuickAction } from '../dashboard.types'

interface QuickActionsProps {
  actions: QuickAction[]
}

export default function QuickActions({
  actions,
}: QuickActionsProps) {
  return (
    <section className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-5 shadow-sm sm:p-6">
      <div>
        <h3 className="text-lg font-bold text-[var(--text)]">
          Thao tác nhanh
        </h3>
        <p className="mt-1 text-sm text-[var(--muted)]">
          Truy cập các chức năng thường dùng
        </p>
      </div>

      <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-2">
        {actions.map((action) => {
          const Icon = action.icon

          return (
            <Link
              key={action.id}
              to={action.to}
              className="group flex min-w-0 items-start gap-3 rounded-xl border border-[var(--border)] p-4 transition hover:border-blue-300 hover:bg-[var(--hover)]"
            >
              <div
                className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${action.iconBackgroundClass} ${action.iconColorClass}`}
              >
                <Icon size={20} />
              </div>

              <div className="min-w-0 flex-1">
                <h4 className="font-semibold text-[var(--text)]">
                  {action.title}
                </h4>

                <p className="mt-1 text-xs leading-5 text-[var(--muted)]">
                  {action.description}
                </p>
              </div>

              <ArrowUpRight
                size={17}
                className="shrink-0 text-[var(--muted)] transition group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-blue-700"
              />
            </Link>
          )
        })}
      </div>
    </section>
  )
}