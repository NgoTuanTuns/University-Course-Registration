
import { Bell, Menu, Search } from 'lucide-react'
import { useLocation } from 'react-router-dom'
import ThemeToggle, { type Theme } from '../ui/ThemeToggle'

interface HeaderProps {
  role: 'student' | 'admin'
  theme: Theme
  onToggleTheme: () => void
  onOpenMenu: () => void
}

const pageTitles: Record<string, string> = {
  '/student/dashboard': 'Tổng quan sinh viên',
  '/student/courses': 'Tra cứu học phần',
  '/student/timetable': 'Thời khóa biểu',
  '/student/prerequisites': 'Điều kiện tiên quyết',
  '/student/enrollment': 'Đăng ký học phần',
  '/student/waitlist': 'Danh sách chờ',
  '/admin/courses': 'Quản lý học phần',
  '/admin/prerequisites': 'Quản lý điều kiện tiên quyết',
  '/login': 'Đăng nhập',
}

export default function Header({
  role,
  theme,
  onToggleTheme,
  onOpenMenu,
}: HeaderProps) {
  const location = useLocation()
  const title = pageTitles[location.pathname] ?? 'UniPortal'

  return (
    <header className="sticky top-0 z-30 flex min-h-20 items-center justify-between gap-3 border-b border-[var(--border)] bg-[var(--surface)]/95 px-4 backdrop-blur sm:px-6 lg:px-8">
      <div className="flex min-w-0 items-center gap-3">
        <button
          type="button"
          onClick={onOpenMenu}
          aria-label="Mở menu điều hướng"
          className="rounded-xl p-2 text-[var(--muted)] hover:bg-[var(--hover)] lg:hidden"
        >
          <Menu size={22} />
        </button>

        <div className="min-w-0">
          <p className="text-xs text-[var(--muted)]">
            {role === 'student' ? 'CỔNG SINH VIÊN' : 'KHU VỰC QUẢN TRỊ'}
          </p>
          <h1 className="truncate text-lg font-bold text-[var(--text)] sm:text-xl">
            {title}
          </h1>
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-2">
        <button
          type="button"
          aria-label="Tìm kiếm (sắp triển khai)"
          title="Tìm kiếm sẽ được bổ sung sau"
          className="hidden h-10 w-10 items-center justify-center rounded-xl text-[var(--muted)] hover:bg-[var(--hover)] sm:inline-flex"
        >
          <Search size={19} />
        </button>

        <button
          type="button"
          aria-label="Thông báo (bản demo)"
          title="Thông báo chưa được kết nối"
          className="relative flex h-10 w-10 items-center justify-center rounded-xl text-[var(--muted)] hover:bg-[var(--hover)]"
        >
          <Bell size={19} />
          <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-blue-600" />
        </button>

        <ThemeToggle theme={theme} onToggle={onToggleTheme} />
      </div>
    </header>
  )
}
