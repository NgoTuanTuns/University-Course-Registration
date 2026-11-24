import type { Enrollment } from "../../types";
import { parseTime } from "./conflicts";

// Học kỳ 2026-2 bắt đầu từ Thứ Hai 28/12/2026 đến hết 31/05/2027
const TERM_START_MONDAY = { year: 2026, month: 12, day: 28 };
const TERM_UNTIL_UTC = "20270531T235959Z";

function pad2(n: number): string {
  return String(n).padStart(2, "0");
}

function getShiftLabel(start: string): string {
  const m = parseTime(start);
  if (m < 9 * 60 + 25) return "Ca 1";
  if (m < 12 * 60 + 15) return "Ca 2";
  if (m < 15 * 60 + 20) return "Ca 3";
  if (m < 18 * 60) return "Ca 4";
  return "Ca 5";
}

function escapeIcsText(text: string): string {
  return text
    .replace(/\\/g, "\\\\")
    .replace(/\n/g, "\\n")
    .replace(/,/g, "\\,")
    .replace(/;/g, "\\;");
}

function formatLocalDateTime(
  dayOfWeek: number,
  hhmm: string,
): { dateStr: string; timeStr: string } {
  // dayOfWeek: 1 = Monday ... 7 = Sunday
  const base = new Date(
    Date.UTC(
      TERM_START_MONDAY.year,
      TERM_START_MONDAY.month - 1,
      TERM_START_MONDAY.day + (dayOfWeek - 1),
    ),
  );
  const [h, m] = hhmm.split(":").map(Number);
  const dateStr = `${base.getUTCFullYear()}${pad2(base.getUTCMonth() + 1)}${pad2(base.getUTCDate())}`;
  const timeStr = `${pad2(h || 0)}${pad2(m || 0)}00`;
  return { dateStr, timeStr };
}

export function generateTimetableIcs(
  regs: Enrollment[],
  term = "2026-2",
): string {
  const now = new Date();
  const dtstamp =
    `${now.getUTCFullYear()}${pad2(now.getUTCMonth() + 1)}${pad2(now.getUTCDate())}` +
    `T${pad2(now.getUTCHours())}${pad2(now.getUTCMinutes())}${pad2(now.getUTCSeconds())}Z`;

  const lines: string[] = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//UniFlow TDTU//Course Registration Timetable//VI",
    "CALSCALE:GREGORIAN",
    "METHOD:PUBLISH",
    `X-WR-CALNAME:${escapeIcsText(`UniFlow TKB Học kỳ ${term}`)}`,
    "X-WR-TIMEZONE:Asia/Ho_Chi_Minh",
  ];

  for (const enr of regs) {
    const o = enr.offering;
    o.schedule.forEach((slot, idx) => {
      const startDt = formatLocalDateTime(slot.day, slot.start);
      const endDt = formatLocalDateTime(slot.day, slot.end);
      const shiftLabel = getShiftLabel(slot.start);
      const summary = `[${o.code}] ${o.name} (Lớp ${o.section} · ${shiftLabel})`;
      const description = escapeIcsText(
        [
          `Học phần: ${o.code} - ${o.name}`,
          `Lớp: ${o.section} (${o.credits} tín chỉ)`,
          `Giảng viên: ${o.instructor || "Đang cập nhật"}`,
          `Ca học: ${shiftLabel} (${slot.start}-${slot.end})`,
          `Học kỳ: ${term}`,
        ].join("\n"),
      );

      lines.push(
        "BEGIN:VEVENT",
        `UID:uniflow-${term}-${o.id}-${idx}@tdtu.edu.vn`,
        `DTSTAMP:${dtstamp}`,
        `DTSTART;TZID=Asia/Ho_Chi_Minh:${startDt.dateStr}T${startDt.timeStr}`,
        `DTEND;TZID=Asia/Ho_Chi_Minh:${endDt.dateStr}T${endDt.timeStr}`,
        `RRULE:FREQ=WEEKLY;UNTIL=${TERM_UNTIL_UTC}`,
        `SUMMARY:${escapeIcsText(summary)}`,
        `LOCATION:${escapeIcsText(`Phòng ${o.room || "Đang cập nhật"} - TDTU`)}`,
        `DESCRIPTION:${description}`,
        "END:VEVENT",
      );
    });
  }

  lines.push("END:VCALENDAR", "");
  return lines.join("\r\n");
}

export function downloadTimetableIcs(
  regs: Enrollment[],
  term = "2026-2",
): void {
  const content = generateTimetableIcs(regs, term);
  const blob = new Blob([content], { type: "text/calendar;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `UniFlow-TKB-${term}.ics`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
