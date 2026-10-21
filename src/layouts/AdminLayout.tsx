import AppLayout from './AppLayout'
import type { Theme } from '../components/ui/ThemeToggle'

interface AdminLayoutProps {
  theme: Theme
  onToggleTheme: () => void
}

export default function AdminLayout(props: AdminLayoutProps) {
  return <AppLayout role="admin" {...props} />
}
