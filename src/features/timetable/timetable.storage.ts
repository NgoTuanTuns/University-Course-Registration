import type { CourseSearchItem } from '../courses/courses.types'
import type { TimetableOffering } from './timetable.types'
import { toTimetableOffering } from './timetable.types'

const PREVIEW_STORAGE_KEY = 'uniportal:timetable-preview:v1'
const PREVIEW_EVENT = 'uniportal:timetable-preview-changed'

export function readPreviewOfferings(): TimetableOffering[] {
  try {
    const raw = sessionStorage.getItem(PREVIEW_STORAGE_KEY)
    if (!raw) return []
    const parsed: unknown = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    return parsed.filter(isTimetableOffering)
  } catch {
    return []
  }
}

export function addPreviewOffering(course: CourseSearchItem): void {
  const current = readPreviewOfferings()
  if (current.some((item) => item.offeringId === course.offeringId)) return
  const next = [...current, toTimetableOffering(course, 'preview')]
  sessionStorage.setItem(PREVIEW_STORAGE_KEY, JSON.stringify(next))
  window.dispatchEvent(new Event(PREVIEW_EVENT))
}

export function removePreviewOffering(offeringId: string): void {
  const next = readPreviewOfferings().filter((item) => item.offeringId !== offeringId)
  sessionStorage.setItem(PREVIEW_STORAGE_KEY, JSON.stringify(next))
  window.dispatchEvent(new Event(PREVIEW_EVENT))
}

export function clearPreviewOfferings(): void {
  sessionStorage.removeItem(PREVIEW_STORAGE_KEY)
  window.dispatchEvent(new Event(PREVIEW_EVENT))
}

export function subscribeToPreviewChanges(callback: () => void): () => void {
  window.addEventListener(PREVIEW_EVENT, callback)
  return () => window.removeEventListener(PREVIEW_EVENT, callback)
}

function isTimetableOffering(value: unknown): value is TimetableOffering {
  if (!value || typeof value !== 'object') return false
  const offering = value as Partial<TimetableOffering>
  return typeof offering.offeringId === 'string'
    && typeof offering.code === 'string'
    && Array.isArray(offering.schedule)
    && offering.kind === 'preview'
}
