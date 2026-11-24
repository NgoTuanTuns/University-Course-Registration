import { describe, expect, it } from "vitest";
import type { Enrollment } from "../../types";
import { generateTimetableIcs } from "./icsExport";

const sampleEnrollment: Enrollment = {
  id: 1,
  status: "ACTIVE",
  offering: {
    id: 42,
    courseId: 10,
    code: "INT131",
    name: "Lập trình hướng đối tượng",
    credits: 3,
    section: "01",
    instructor: "Ngô Ngọc Hà",
    room: "A2-273",
    capacity: 50,
    enrolledCount: 10,
    schedule: [
      { day: 2, start: "06:50", end: "09:20" },
      { day: 4, start: "09:30", end: "12:00" },
    ],
  },
};

describe("generateTimetableIcs", () => {
  it("generates valid RFC 5545 calendar with VEVENT per shift", () => {
    const ics = generateTimetableIcs([sampleEnrollment], "2026-2");
    expect(ics).toContain("BEGIN:VCALENDAR");
    expect(ics).toContain("END:VCALENDAR");
    expect(ics).toContain("X-WR-TIMEZONE:Asia/Ho_Chi_Minh");
    expect(ics.match(/BEGIN:VEVENT/g)?.length).toBe(2);
    expect(ics).toContain("DTSTART;TZID=Asia/Ho_Chi_Minh:20261229T065000");
    expect(ics).toContain("DTEND;TZID=Asia/Ho_Chi_Minh:20261229T092000");
    expect(ics).toContain("DTSTART;TZID=Asia/Ho_Chi_Minh:20261231T093000");
    expect(ics).toContain("RRULE:FREQ=WEEKLY;UNTIL=20270531T235959Z");
    expect(ics).toContain("INT131");
    expect(ics).toContain("Ca 1");
    expect(ics).toContain("Ca 2");
    expect(ics).toContain("A2-273");
  });

  it("handles empty enrollment list cleanly", () => {
    const ics = generateTimetableIcs([], "2026-2");
    expect(ics).toContain("BEGIN:VCALENDAR");
    expect(ics).not.toContain("BEGIN:VEVENT");
  });

  it("escapes RFC 5545 special characters in description and summary", () => {
    const special: Enrollment = {
      ...sampleEnrollment,
      offering: {
        ...sampleEnrollment.offering,
        name: "Lập trình C, C++; Cấu trúc",
        instructor: "TS. Nguyễn, Văn A",
      },
    };
    const ics = generateTimetableIcs([special], "2026-2");
    expect(ics).toContain("Lập trình C\\, C++\\; Cấu trúc");
    expect(ics).toContain("TS. Nguyễn\\, Văn A");
  });
});
