import type { LucideIcon } from 'lucide-react'

export interface StudentProfile {
  fullName: string
  studentId: string
  program: string
  semester: string
}

export interface CreditSummary {
  registeredCredits: number
  maxCredits: number
  completedCredits: number
}

export type EnrollmentStatus =
  | 'registered'
  | 'waitlisted'
  | 'pending'

export interface EnrollmentSummary {
  registeredClasses: number
  waitlistedClasses: number
  pendingClasses: number
}

export interface UpcomingClass {
  id: string
  courseCode: string
  courseName: string
  dateLabel: string
  startTime: string
  endTime: string
  room: string
  lecturer: string
}

export interface DashboardStat {
  id: string
  title: string
  value: string
  description: string
  icon: LucideIcon
  iconColorClass: string
  iconBackgroundClass: string
}

export interface QuickAction {
  id: string
  title: string
  description: string
  to: string
  icon: LucideIcon
  iconColorClass: string
  iconBackgroundClass: string
}