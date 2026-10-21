import AppLayout from './AppLayout'
import type { Theme } from '../components/ui/ThemeToggle'

interface StudentLayoutProps {
  theme: Theme
  onToggleTheme: () => void
}

export default function StudentLayout(props: StudentLayoutProps) {
  return <AppLayout role="student" {...props} />
}
