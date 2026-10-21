import { Search, X } from 'lucide-react'
import type { CourseSearchFilters } from '../courses.types'

interface CourseFiltersProps {
  filters: CourseSearchFilters
  onChange: (next: CourseSearchFilters) => void
  onReset: () => void
}

const inputClass =
  'w-full rounded-xl border border-[var(--border)] bg-[var(--surface)] px-3 py-2.5 text-sm text-[var(--text)] outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-500/15'

export default function CourseFilters({
  filters,
  onChange,
  onReset,
}: CourseFiltersProps) {
  function update<K extends keyof CourseSearchFilters>(
    key: K,
    value: CourseSearchFilters[K],
  ) {
    onChange({
      ...filters,
      [key]: value,
      page: 1,
    })
  }

  return (
    <section className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-4 shadow-sm sm:p-5">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <h2 className="font-semibold text-[var(--text)]">
            Bộ lọc học phần
          </h2>
          <p className="mt-1 text-sm text-[var(--muted)]">
            Kết hợp nhiều điều kiện để tìm lớp phù hợp.
          </p>
        </div>

        <button
          type="button"
          onClick={onReset}
          className="inline-flex shrink-0 items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium text-[var(--muted)] transition hover:bg-[var(--background)] hover:text-[var(--text)]"
        >
          <X size={16} />
          Xóa lọc
        </button>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <label className="sm:col-span-2 xl:col-span-2">
          <span className="mb-1.5 block text-sm font-medium text-[var(--text)]">
            Từ khóa
          </span>
          <div className="relative">
            <Search
              size={18}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted)]"
            />
            <input
              className={`${inputClass} pl-10`}
              value={filters.keyword}
              onChange={(event) =>
                update('keyword', event.target.value)
              }
              placeholder="Mã môn, tên môn, giảng viên..."
            />
          </div>
        </label>

        <label>
          <span className="mb-1.5 block text-sm font-medium text-[var(--text)]">
            Mã lớp
          </span>
          <input
            className={inputClass}
            value={filters.section}
            onChange={(event) =>
              update('section', event.target.value)
            }
            placeholder="VD: INT130.01"
          />
        </label>

        <label>
          <span className="mb-1.5 block text-sm font-medium text-[var(--text)]">
            Số tín chỉ
          </span>
          <select
            className={inputClass}
            value={filters.credits}
            onChange={(event) =>
              update(
                'credits',
                event.target.value === 'all'
                  ? 'all'
                  : Number(event.target.value),
              )
            }
          >
            <option value="all">Tất cả</option>
            <option value="2">2 tín chỉ</option>
            <option value="3">3 tín chỉ</option>
            <option value="4">4 tín chỉ</option>
          </select>
        </label>

        <label>
          <span className="mb-1.5 block text-sm font-medium text-[var(--text)]">
            Học kỳ
          </span>
          <select
            className={inputClass}
            value={filters.term}
            onChange={(event) => update('term', event.target.value)}
          >
            <option value="all">Tất cả học kỳ</option>
            <option value="2026-1">Học kỳ 1 · 2026–2027</option>
            <option value="2026-2">Học kỳ 2 · 2026–2027</option>
          </select>
        </label>

        <label>
          <span className="mb-1.5 block text-sm font-medium text-[var(--text)]">
            Ngày học
          </span>
          <select
            className={inputClass}
            value={filters.dayOfWeek}
            onChange={(event) =>
              update(
                'dayOfWeek',
                event.target.value === 'all'
                  ? 'all'
                  : Number(event.target.value),
              )
            }
          >
            <option value="all">Tất cả ngày</option>
            <option value="1">Thứ Hai</option>
            <option value="2">Thứ Ba</option>
            <option value="3">Thứ Tư</option>
            <option value="4">Thứ Năm</option>
            <option value="5">Thứ Sáu</option>
            <option value="6">Thứ Bảy</option>
            <option value="7">Chủ nhật</option>
          </select>
        </label>
      </div>
    </section>
  )
}