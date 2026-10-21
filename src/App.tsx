import DashboardPage from './pages/student/DashboardPage'
import CoursesPage from './pages/student/CoursesPage'
import TimetablePage from './pages/student/TimetablePage'
import EnrollmentPage from './pages/student/EnrollmentPage'
import PrerequisitesPage from './pages/student/PrerequisitesPage'
import WaitlistPage from './pages/student/WaitlistPage'
import CoursesAdminPage from './pages/admin/CoursesAdminPage'
import { useState } from 'react'
import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
} from 'react-router-dom'

import StudentLayout from './layouts/StudentLayout'
import AdminLayout from './layouts/AdminLayout'
import PlaceholderPage from './pages/PlaceholderPage'
import NotFoundPage from './pages/NotFoundPage'
import LoginPage from './pages/auth/LoginPage'
import type { Theme } from './components/ui/ThemeToggle'

function App() {
  const [theme, setTheme] = useState<Theme>('light')

  function toggleTheme() {
    setTheme((current) => current === 'light' ? 'dark' : 'light')
  }

  return (
    <div
      data-theme={theme}
      className="min-h-screen bg-[var(--app-bg)] text-[var(--text)]"
    >
      <BrowserRouter>
        <Routes>
          <Route
            path="/"
            element={<Navigate to="/student/dashboard" replace />}
          />

          <Route path="/login" element={<LoginPage />} />

          <Route
            path="/student"
            element={
              <StudentLayout
                theme={theme}
                onToggleTheme={toggleTheme}
              />
            }
          >
            <Route
              index
              element={<Navigate to="dashboard" replace />}
            />

            <Route
              path="dashboard"
              element={<DashboardPage />}
            />

            <Route
              path="courses"
              element={<CoursesPage />}
            />

            <Route path="timetable" element={<TimetablePage />} />

            <Route path="prerequisites" element={<PrerequisitesPage />} />

            <Route path="enrollment" element={<EnrollmentPage />} />

            <Route path="waitlist" element={<WaitlistPage />} />
          </Route>

          <Route
            path="/admin"
            element={
              <AdminLayout
                theme={theme}
                onToggleTheme={toggleTheme}
              />
            }
          >
            <Route
              index
              element={<Navigate to="courses" replace />}
            />

            <Route path="courses" element={<CoursesAdminPage />} />

            <Route
              path="prerequisites"
              element={
                <PlaceholderPage
                  title="Quản lý điều kiện tiên quyết"
                  description="Khu vực quản trị các quan hệ tiên quyết giữa những học phần."
                />
              }
            />
          </Route>

          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </BrowserRouter>
    </div>
  )
}

export default App
