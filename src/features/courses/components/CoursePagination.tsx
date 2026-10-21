import { ChevronLeft, ChevronRight } from 'lucide-react'

interface CoursePaginationProps {
  page: number
  pageSize: number
  total: number
  totalPages: number
  onPageChange: (page: number) => void
  onPageSizeChange: (pageSize: number) => void
}

export default function CoursePagination({
  page,
  pageSize,
  total,
  totalPages,
  onPageChange,
  onPageSizeChange,
}: CoursePaginationProps) {
  const start = total === 0 ? 0 : (page - 1) * pageSize + 1
  const end = Math.min(page * pageSize, total)

  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="text-sm text-[var(--muted)]">
        Hiển thị{' '}
        <span className="font-semibold text-[var(--text)]">{start}–{end}</span>
        {' '}trong{' '}
        <span className="font-semibold text-[var(--text)]">{total}</span>
        {' '}kết quả
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <label className="mr-1 flex items-center gap-2 text-sm text-[var(--muted)]">
          Mỗi trang
          <select
            value={pageSize}
            onChange={(event) =>
              onPageSizeChange(Number(event.target.value))
            }
            className="rounded-lg border border-[var(--border)] bg-[var(--surface)] px-2 py-2 text-[var(--text)] outline-none focus:border-blue-500"
          >
            <option value={5}>5</option>
            <option value={10}>10</option>
            <option value={20}>20</option>
          </select>
        </label>

        <button
          type="button"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
          className="inline-flex items-center gap-1 rounded-lg border border-[var(--border)] px-3 py-2 text-sm text-[var(--text)] transition hover:bg-[var(--background)] disabled:cursor-not-allowed disabled:opacity-40"
        >
          <ChevronLeft size={16} />
          Trước
        </button>

        <span className="min-w-24 text-center text-sm text-[var(--text)]">
          Trang {page} / {Math.max(totalPages, 1)}
        </span>

        <button
          type="button"
          disabled={page >= totalPages || totalPages === 0}
          onClick={() => onPageChange(page + 1)}
          className="inline-flex items-center gap-1 rounded-lg border border-[var(--border)] px-3 py-2 text-sm text-[var(--text)] transition hover:bg-[var(--background)] disabled:cursor-not-allowed disabled:opacity-40"
        >
          Sau
          <ChevronRight size={16} />
        </button>
      </div>
    </div>
  )
}