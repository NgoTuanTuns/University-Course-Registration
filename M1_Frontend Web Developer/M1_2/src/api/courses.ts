import type { Offering, Paginated } from "../types";
import { getStaticOfferings } from "../mocks/data";
import { http, mockMode } from "./http";

const week = Number(import.meta.env.VITE_WEEK || 1);

export async function courses(query: string, signal?: AbortSignal): Promise<Paginated<Offering>> {
  // Week 3: backend chưa có GET /courses cho sinh viên. Dùng danh mục tĩnh bám seed KIT.
  if (!mockMode && week >= 3) {
    const params = new URLSearchParams(query);
    const items = getStaticOfferings().filter((item) => {
      const keyword = (params.get("q") || "").toLowerCase();
      return (
        `${item.code} ${item.name}`.toLowerCase().includes(keyword) &&
        item.section.toLowerCase().includes((params.get("section") || "").toLowerCase()) &&
        (!params.get("credits") || item.credits === Number(params.get("credits"))) &&
        item.instructor.toLowerCase().includes((params.get("instructor") || "").toLowerCase()) &&
        item.schedule.some((slot) =>
          (!params.get("day") || slot.day === Number(params.get("day"))) &&
          (!params.get("start") || slot.end > params.get("start")!) &&
          (!params.get("end") || slot.start < params.get("end")!),
        )
      );
    });
    if (signal?.aborted) throw new DOMException("Request aborted", "AbortError");
    const page = Math.max(1, Number(params.get("page") || 1));
    const pageSize = 20;
    return { items: items.slice((page - 1) * pageSize, page * pageSize), total: items.length, page, pageSize };
  }
  return http<Paginated<Offering>>(`/courses?${query}`, "GET", undefined, signal);
}
