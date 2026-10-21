
import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import Sidebar from '../components/layout/Sidebar'
import Header from '../components/layout/Header'
import type { Theme } from '../components/ui/ThemeToggle'

interface AppLayoutProps {
  role: 'student' | 'admin'
  theme: Theme
  onToggleTheme: () => void
}

export default function AppLayout({
  role,
  theme,
  onToggleTheme,
}: AppLayoutProps) {
  const [mobileOpen, setMobileOpen] = useState(false)

  return (
    <div className="flex min-h-screen bg-[var(--app-bg)] text-[var(--text)]">
      <Sidebar
        role={role}
        mobileOpen={mobileOpen}
        onClose={() => setMobileOpen(false)}
      />

      <div className="flex min-w-0 flex-1 flex-col">
        <Header
          role={role}
          theme={theme}
          onToggleTheme={onToggleTheme}
          onOpenMenu={() => setMobileOpen(true)}
        />

        <main className="flex-1 p-4 sm:p-6 lg:p-8">
          <div className="mx-auto w-full max-w-7xl">
            <Outlet />
          </div>
        </main>

        <footer className="border-t border-[var(--border)] px-6 py-4 text-center text-xs text-[var(--muted)]">
          UniPortal · Hệ thống đăng ký học phần · M1 Frontend
        </footer>
      </div>
    </div>
  )
}
