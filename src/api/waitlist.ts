import { http } from "./http";
import type { Offering, Paginated } from "../types";

export interface WaitlistEntry {
  id: number;
  offeringId: number;
  position: number;
  enqueuedAt: string;
  offering: Offering;
  blockedReason?: string | null;
}

interface WaitlistApiItem extends Offering {
  waitlistId: number;
  position: number;
  enqueuedAt: string;
  blockedReason?: string | null;
}

export async function getWaitlist(): Promise<Paginated<WaitlistEntry>> {
  const data = await http<Paginated<WaitlistApiItem>>("/waitlist?page=1&page_size=100");
  return {
    ...data,
    items: data.items.map((item) => ({
      id: item.waitlistId,
      offeringId: item.id,
      position: item.position,
      enqueuedAt: item.enqueuedAt,
      blockedReason: item.blockedReason,
      offering: item,
    })),
  };
}
export const leaveWaitlist = (waitlistId: number) =>
  http<{ id: number; offeringId: number; status: string }>(
    `/waitlist/${waitlistId}`,
    "DELETE",
  );
