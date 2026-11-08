import { ApiError } from "./http";

export interface WaitlistEntry {
  id: number;
  offeringId: number;
  position: number;
  enqueuedAt: string;
}

// Backend chưa công bố contract waitlist. Các thao tác bị khóa có chủ đích.
function pending(): never {
  throw new ApiError(
    "FEATURE_PENDING",
    "Chức năng danh sách chờ đang chờ API từ M3.",
    501,
  );
}

export const getWaitlist = (): never => pending();
export const joinWaitlist = (_offeringId: number): never => {
  void _offeringId;
  return pending();
};
export const leaveWaitlist = (_waitlistId: number): never => {
  void _waitlistId;
  return pending();
};
