import type { Enrollment } from "../types";
import { http, mockMode } from "./http";

const week = Number(import.meta.env.VITE_WEEK || 1);

export async function timetable(): Promise<Enrollment[]> {
  // API GET /timetable chưa có trong backend nhóm; không giả lập request ở Week 3.
  if (!mockMode && week >= 3) return [];
  return http<Enrollment[]>("/timetable?term=2026-1");
}
