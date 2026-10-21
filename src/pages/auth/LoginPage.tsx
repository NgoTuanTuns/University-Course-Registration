
import { Link } from 'react-router-dom'
import { GraduationCap, ShieldCheck } from 'lucide-react'

export default function LoginPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-[var(--app-bg)] px-4 py-10">
      <section className="w-full max-w-lg rounded-3xl border border-[var(--border)] bg-[var(--surface)] p-6 shadow-xl sm:p-10">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-600 text-white">
          <GraduationCap size={29} />
        </div>

        <div className="mt-5 text-center">
          <h1 className="text-2xl font-bold text-[var(--text)]">
            Chào mừng đến UniPortal
          </h1>
          <p className="mt-2 text-sm leading-6 text-[var(--muted)]">
            Chọn khu vực để xem giao diện tương ứng.
          </p>
        </div>

        <div className="mt-8 space-y-3">
          <Link
            to="/student/dashboard"
            className="flex items-center gap-4 rounded-2xl border border-[var(--border)] p-4 transition hover:border-blue-400 hover:bg-[var(--hover)]"
          >
            <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-50 text-blue-700">
              <GraduationCap size={22} />
            </span>
            <span>
              <span className="block font-semibold text-[var(--text)]">
                Khu vực sinh viên
              </span>
              <span className="mt-1 block text-sm text-[var(--muted)]">
                Tra cứu và đăng ký học phần
              </span>
            </span>
          </Link>

          <Link
            to="/admin/courses"
            className="flex items-center gap-4 rounded-2xl border border-[var(--border)] p-4 transition hover:border-blue-400 hover:bg-[var(--hover)]"
          >
            <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-violet-50 text-violet-700">
              <ShieldCheck size={22} />
            </span>
            <span>
              <span className="block font-semibold text-[var(--text)]">
                Khu vực quản trị
              </span>
              <span className="mt-1 block text-sm text-[var(--muted)]">
                Quản lý học phần và điều kiện tiên quyết
              </span>
            </span>
          </Link>
        </div>

        <p className="mt-6 text-center text-xs leading-5 text-[var(--muted)]">
          Đây là lựa chọn khu vực cho bản demo, chưa kiểm tra danh tính hoặc quyền truy cập.
        </p>
      </section>
    </main>
  )
}
