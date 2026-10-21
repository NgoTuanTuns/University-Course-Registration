import type { TimetableOffering } from '../features/timetable/timetable.types'
import { toTimetableOffering } from '../features/timetable/timetable.types'
import { getEnrollments } from './enroll'

/** Mock GET /timetable. Replace with the frozen backend contract when agreed with M3. */
export async function getTimetable(term: string): Promise<TimetableOffering[]> {
  const records = await getEnrollments(term)
  return records
    .filter((record) => record.status === 'active')
    .map((record) => toTimetableOffering(record.course, 'enrolled'))
}
