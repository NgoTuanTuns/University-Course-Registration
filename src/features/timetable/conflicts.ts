import type { Offering, Slot } from "../../types";

export function parseTime(value: string): number {
  const match = /^(\d{2}):(\d{2})$/.exec(value);
  if (!match) throw new Error(`Giờ không hợp lệ: ${value}`);
  const hours = Number(match[1]);
  const minutes = Number(match[2]);
  if (hours > 23 || minutes > 59) throw new Error(`Giờ không hợp lệ: ${value}`);
  return hours * 60 + minutes;
}

export function formatTime(totalMinutes: number): string {
  const safe = Math.max(0, Math.min(1439, Math.trunc(totalMinutes)));
  return `${String(Math.floor(safe / 60)).padStart(2, "0")}:${String(safe % 60).padStart(2, "0")}`;
}

export function slotsOverlap(a: Slot, b: Slot): boolean {
  if (a.day !== b.day) return false;
  const aStart = parseTime(a.start);
  const aEnd = parseTime(a.end);
  const bStart = parseTime(b.start);
  const bEnd = parseTime(b.end);
  if (aStart >= aEnd || bStart >= bEnd) return false;
  return aStart < bEnd && bStart < aEnd;
}

export interface SlotConflict {
  offering: Offering;
  candidateSlot: Slot;
  conflictingSlot: Slot;
}

export function findSlotConflicts(
  candidate: Offering,
  slot: Slot,
  all: Offering[],
): SlotConflict[] {
  const conflicts: SlotConflict[] = [];
  for (const offering of all) {
    if (offering.id === candidate.id) continue;
    for (const otherSlot of offering.schedule) {
      if (slotsOverlap(slot, otherSlot)) {
        conflicts.push({
          offering,
          candidateSlot: slot,
          conflictingSlot: otherSlot,
        });
      }
    }
  }
  return conflicts;
}

export function findConflicts(
  candidate: Offering,
  all: Offering[],
): Offering[] {
  const found = new Map<number, Offering>();
  for (const slot of candidate.schedule) {
    for (const conflict of findSlotConflicts(candidate, slot, all)) {
      found.set(conflict.offering.id, conflict.offering);
    }
  }
  return [...found.values()];
}
