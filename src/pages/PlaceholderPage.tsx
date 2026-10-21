
import { Construction } from 'lucide-react'

interface PlaceholderPageProps {
  title: string
  description: string
}

export default function PlaceholderPage({
  title,
  description,
}: PlaceholderPageProps) {
  return (
    <section className="space-y-6">
      <div>
        <p className="text-sm font-medium text-blue-600">
          UNIPORTAL / M1 FRONTEND
        </p>
        <h2 className="mt-2 text-2xl font-bold tracking-tight text-[var(--text)] sm:text-3xl">
          {title}
        </h2>
        <p className="mt-2 max-w-2xl leading-7 text-[var(--muted)]">
          {description}
        </p>
      </div>

      <div className="rounded-2xl border border-dashed border-[var(--border)] bg-[var(--surface)] px-5 py-12 text-center sm:px-10">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-50 text-blue-600">
          <Construction size={27} />
        </div>

        <h3 className="mt-5 text-lg font-semibold text-[var(--text)]">
          Khu vực đã sẵn sàng
        </h3>

        <p className="mx-auto mt-2 max-w-lg text-sm leading-6 text-[var(--muted)]">
          Điều hướng đã hoạt động. Nội dung nghiệp vụ của trang này sẽ được
          triển khai ở bước tiếp theo bằng dữ liệu mẫu trước khi tích hợp API.
        </p>

        <span className="mt-5 inline-flex rounded-full bg-amber-50 px-3 py-1 text-xs font-medium text-amber-700">
          Đang phát triển
        </span>
      </div>
    </section>
  )
}
