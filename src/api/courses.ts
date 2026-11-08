import type { Offering, Paginated } from "../types";
import { getStaticOfferings } from "../mocks/data";
import { http, mockMode } from "./http";

export async function courses(
  query: string,
  signal?: AbortSignal,
): Promise<Paginated<Offering>> {
  if (mockMode) {
    const params = new URLSearchParams(query);
    const items = getStaticOfferings().filter((item) => {
      const keyword = (params.get("q") || "").toLowerCase();
      return (
        `${item.code} ${item.name}`.toLowerCase().includes(keyword) &&
        item.section
          .toLowerCase()
          .includes((params.get("section") || "").toLowerCase()) &&
        (!params.get("credits") ||
          item.credits === Number(params.get("credits"))) &&
        item.instructor
          .toLowerCase()
          .includes((params.get("instructor") || "").toLowerCase()) &&
        item.schedule.some(
          (slot) =>
            (!params.get("day") || slot.day === Number(params.get("day"))) &&
            (!params.get("start") || slot.end > params.get("start")!) &&
            (!params.get("end") || slot.start < params.get("end")!),
        )
      );
    });
    if (signal?.aborted)
      throw new DOMException("Request aborted", "AbortError");
    const page = Math.max(1, Number(params.get("page") || 1));
    const pageSize = 20;
    return {
      items: items.slice((page - 1) * pageSize, page * pageSize),
      total: items.length,
      page,
      pageSize,
    };
  }

  // Chuyển đổi tham số bộ lọc từ UI (start, end) sang định dạng API backend M3 (from, to)
  const params = new URLSearchParams(query);
  if (params.has("start")) {
    params.set("from", params.get("start")!);
    params.delete("start");
  }
  if (params.has("end")) {
    params.set("to", params.get("end")!);
    params.delete("end");
  }

  return http<Paginated<Offering>>(
    `/courses?${params.toString()}`,
    "GET",
    undefined,
    signal,
  );
}
