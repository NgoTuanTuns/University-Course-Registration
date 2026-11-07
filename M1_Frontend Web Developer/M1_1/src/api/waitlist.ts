import { http } from "./http";

export interface WaitlistEntry {
  id: number;
  offeringId: number;
  position: number;
  enqueuedAt: string;
}

// Các hàm này phục vụ mock/tuần sau; backend nhóm chưa công bố contract waitlist.
export const getWaitlist = () => http<WaitlistEntry[]>("/waitlist");
export const joinWaitlist = (offeringId: number) =>
  http<WaitlistEntry>("/waitlist", "POST", { offeringId });
export const leaveWaitlist = (waitlistId: number) =>
  http<{ message: string }>(`/waitlist/${waitlistId}`, "DELETE");
