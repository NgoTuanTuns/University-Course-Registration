
import { NavLink } from 'react-router-dom'
import {
  BookOpen,
  CalendarDays,
  ClipboardCheck,
  GraduationCap,
  LayoutDashboard,
  ListChecks,
  Settings,
  Users,
  X,
} from 'lucide-react'

interface SidebarProps {
  role: 'student' | 'admin'
  mobileOpen: boolean
  onClose: () => void
}

const studentLinks = [
  { to: '/student/dashboard', label: 'Tổng quan', icon: LayoutDashboard },
  { to: '/student/courses', label: 'Tra cứu học phần', icon: BookOpen },
  { to: '/student/timetable', label: 'Thời khóa biểu', icon: CalendarDays },
  { to: '/student/prerequisites', label: 'Điều kiện tiên quyết', icon: ClipboardCheck },
  { to: '/student/enrollment', label: 'Đăng ký học phần', icon: GraduationCap },
  { to: '/student/waitlist', label: 'Danh sách chờ', icon: ListChecks },
]

const adminLinks = [
  { to: '/admin/courses', label: 'Quản lý học phần', icon: BookOpen },
  { to: '/admin/prerequisites', label: 'Quản lý tiên quyết', icon: ClipboardCheck },
]

export default function Sidebar({
  role,
  mobileOpen,
  onClose,
}: SidebarProps) {
  const links = role === 'student' ? studentLinks : adminLinks

  return (
    <>
      {mobileOpen && (
        <button
          type="button"
          aria-label="Đóng menu"
          onClick={onClose}
          className="fixed inset-0 z-40 bg-slate-950/40 lg:hidden"
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-[var(--border)] bg-[var(--surface)] transition-transform duration-200 lg:static lg:translate-x-0 ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex h-20 items-center justify-between border-b border-[var(--border)] px-5">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-600 text-white">
              <GraduationCap size={23} />
            </div>

            <div>
              <p className="font-bold tracking-tight text-[var(--text)]">
                UniPortal
              </p>
              <p className="text-xs text-[var(--muted)]">
                Course Registration
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            aria-label="Đóng sidebar"
            className="rounded-lg p-2 text-[var(--muted)] hover:bg-[var(--hover)] lg:hidden"
          >
            <X size={20} />
          </button>
        </div>

        <div className="px-4 pt-6">
          <p className="mb-3 px-3 text-xs font-semibold uppercase tracking-wider text-[var(--muted)]">
            {role === 'student' ? 'Không gian sinh viên' : 'Quản trị hệ thống'}
          </p>

          <nav className="space-y-1">
            {links.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                onClick={onClose}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-medium transition ${
                    isActive
                      ? 'bg-blue-600 text-white shadow-md shadow-blue-600/20'
                      : 'text-[var(--muted)] hover:bg-[var(--hover)] hover:text-[var(--text)]'
                  }`
                }
              >
                <Icon size={19} />
                <span>{label}</span>
              </NavLink>
            ))}
          </nav>
        </div>

        <div className="mt-auto border-t border-[var(--border)] p-4">
          <div className="flex items-center gap-3 rounded-xl p-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-indigo-100 font-semibold text-indigo-700">
              {role === 'student' ? 'SV' : 'AD'}
            </div>

            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-[var(--text)]">
                {role === 'student' ? 'Sinh viên demo' : 'Quản trị viên demo'}
              </p>
              <p className="text-xs text-[var(--muted)]">
                {role === 'student' ? 'Student account' : 'Admin account'}
              </p>
            </div>
          </div>

          <NavLink
            to="/login"
            onClick={onClose}
            className="mt-2 flex items-center gap-3 rounded-xl px-3 py-3 text-sm text-[var(--muted)] transition hover:bg-[var(--hover)] hover:text-[var(--text)]"
          >
            <Users size={18} />
            Đăng nhập / Đổi vai trò
          </NavLink>

          <div className="mt-1 flex items-center gap-3 px-3 py-2 text-xs text-[var(--muted)]">
            <Settings size={15} />
            Bản giao diện thử nghiệm
          </div>
        </div>
      </aside>
    </>
  )
}
