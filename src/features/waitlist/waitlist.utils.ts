import type { EnrollmentRecord } from '../enroll/enroll.types'

export function sortWaitlistRecords(records: EnrollmentRecord[]): EnrollmentRecord[] {
  return records
    .filter((record) => record.status === 'waitlisted')
    .sort((a, b) => (a.position ?? Number.MAX_SAFE_INTEGER) - (b.position ?? Number.MAX_SAFE_INTEGER)
      || a.enrolledAt.localeCompare(b.enrolledAt))
}

export function formatEnqueuedAt(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'Chưa có thông tin'
  return new Intl.DateTimeFormat('vi-VN', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  }).format(date)
}
