import type { Enrollment, Slot } from "../types";
import { http } from "./http";

interface TimetableResponse {
  term: string;
  items: Array<{
    enrollmentId: number;
    id: number;
    courseId: number;
    code: string;
    name: string;
    credits: number;
    section: string;
    instructor?: string | null;
    room?: string | null;
    schedule: Slot[];
    capacity: number;
    enrolledCount: number;
    version?: number;
    myStatus?: string;
  }>;
  totalCredits: number;
  maxCredits: number;
}

export async function timetable(): Promise<Enrollment[]> {
  try {
    const data = await http<TimetableResponse | Enrollment[]>(
      "/timetable?term=2026-1",
    );
    if (Array.isArray(data)) {
      return data;
    }
    if (data && Array.isArray(data.items)) {
      return data.items.map((item) => ({
        id: item.enrollmentId,
        offering: {
          id: item.id,
          courseId: item.courseId,
          code: item.code,
          name: item.name,
          credits: item.credits,
          section: item.section,
          instructor: item.instructor || "",
          room: item.room || "",
          schedule: item.schedule || [],
          capacity: item.capacity,
          enrolledCount: item.enrolledCount,
        },
        status: "ACTIVE",
      }));
    }
    return [];
  } catch (err) {
    console.error("Lỗi khi tải thời khóa biểu:", err);
    return [];
  }
}
