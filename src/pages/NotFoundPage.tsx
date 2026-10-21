
import { Link } from 'react-router-dom'

export default function NotFoundPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-[var(--app-bg)] px-5">
      <div className="max-w-md text-center">
        <p className="text-sm font-bold uppercase tracking-widest text-blue-600">
          Lỗi 404
        </p>

        <h1 className="mt-3 text-3xl font-bold text-[var(--text)]">
          Không tìm thấy trang
        </h1>

        <p className="mt-3 leading-7 text-[var(--muted)]">
          Đường dẫn này chưa tồn tại trong hệ thống.
        </p>

        <Link
          to="/student/dashboard"
          className="mt-6 inline-flex rounded-xl bg-blue-600 px-5 py-3 font-semibold text-white transition hover:bg-blue-700"
        >
          Về trang tổng quan
        </Link>
      </div>
    </main>
  )
}
