import type { EnrollmentRecord } from '../enroll/enroll.types'

export function getEnrollmentSummary(records: EnrollmentRecord[]) {
  const active = records.filter((record) => record.status === 'active')
  const waitlisted = records.filter((record) => record.status === 'waitlisted')
  return {
    registeredClasses: active.length,
    waitlistedClasses: waitlisted.length,
    registeredCredits: active.reduce((total, record) => total + record.credits, 0),
  }
}

export function getCreditPercentage(registeredCredits: number, maxCredits: number): number {
  if (maxCredits <= 0) return 0
  return Math.min(100, Math.round((Math.max(0, registeredCredits) / maxCredits) * 100))
}
