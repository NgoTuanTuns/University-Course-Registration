import { describe, expect, it } from "vitest";
import type { Offering, Slot } from "../../types";
import {
  findConflicts,
  findSlotConflicts,
  formatTime,
  parseTime,
  slotsOverlap,
} from "./conflicts";

const slot = (day: number, start: string, end: string): Slot => ({
  day,
  start,
  end,
});
const offering = (id: number, schedule: Slot[]): Offering => ({
  id,
  courseId: id,
  code: `CS${id}`,
  name: `Học phần ${id}`,
  credits: 3,
  section: "01",
  instructor: "Giảng viên mẫu",
  room: "A101",
  schedule,
  enrolledCount: 10,
  capacity: 40,
});

describe("parseTime / formatTime", () => {
  it("chuyển HH:MM thành phút và ngược lại", () => {
    expect(parseTime("07:00")).toBe(420);
    expect(parseTime("09:30")).toBe(570);
    expect(formatTime(570)).toBe("09:30");
  });
  it("từ chối giờ không hợp lệ", () => {
    expect(() => parseTime("25:00")).toThrow();
    expect(() => parseTime("7:00")).toThrow();
  });
});

describe("slotsOverlap", () => {
  const base = slot(1, "07:00", "09:30");
  it("phát hiện trùng hoàn toàn", () =>
    expect(slotsOverlap(base, slot(1, "07:00", "09:30"))).toBe(true));
  it("phát hiện trùng một phần ở đầu hoặc cuối", () => {
    expect(slotsOverlap(base, slot(1, "06:30", "08:00"))).toBe(true);
    expect(slotsOverlap(base, slot(1, "09:00", "10:00"))).toBe(true);
  });
  it("không coi hai ca liền kề là trùng", () => {
    expect(slotsOverlap(base, slot(1, "09:30", "12:00"))).toBe(false);
    expect(slotsOverlap(base, slot(1, "05:00", "07:00"))).toBe(false);
  });
  it("không trùng khi khác ngày", () =>
    expect(slotsOverlap(base, slot(2, "07:00", "09:30"))).toBe(false));
  it("không tính khoảng thời gian không hợp lệ là xung đột", () =>
    expect(slotsOverlap(base, slot(1, "10:00", "09:00"))).toBe(false));
});

describe("findConflicts", () => {
  const a = offering(1, [slot(1, "07:00", "09:30"), slot(3, "13:00", "15:30")]);
  const b = offering(2, [slot(1, "08:00", "10:00")]);
  const c = offering(3, [slot(3, "14:00", "16:00")]);
  const d = offering(4, [slot(2, "07:00", "09:30")]);

  it("phát hiện nhiều lớp xung đột qua nhiều buổi trong tuần", () => {
    expect(
      findConflicts(a, [a, b, c, d])
        .map((x) => x.id)
        .sort(),
    ).toEqual([2, 3]);
  });
  it("không báo lớp tự xung đột khi đối chiếu chính nó", () => {
    expect(findConflicts(a, [a])).toEqual([]);
  });
  it("không nhân đôi một lớp nếu nhiều buổi của lớp đó cùng xung đột", () => {
    const multi = offering(5, [
      slot(1, "07:30", "08:30"),
      slot(1, "08:00", "09:00"),
    ]);
    expect(findConflicts(a, [a, multi])).toHaveLength(1);
  });
  it("trả về buổi cụ thể bị xung đột", () => {
    expect(findSlotConflicts(a, a.schedule[0], [a, b])).toHaveLength(1);
  });
});
