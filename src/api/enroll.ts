import { http } from "./http";

export interface EnrollResult {
  id: number;
  offeringId: number;
  status: "ACTIVE" | "WAITLISTED" | "CANCELLED";
  version?: number | null;
  position?: number | null;
}

export async function enroll(
  offeringId: number,
  idempotencyKey?: string,
): Promise<EnrollResult> {
  const headers: Record<string, string> = {};
  if (idempotencyKey) {
    headers["Idempotency-Key"] = idempotencyKey;
  }
  return http<EnrollResult>(
    "/enroll",
    "POST",
    { offeringId },
    undefined,
    true,
    headers,
  );
}

export async function cancel(enrollmentId: number): Promise<EnrollResult> {
  return http<EnrollResult>(`/enroll/${enrollmentId}`, "DELETE");
}

export interface SwapResult {
  fromEnrollmentId: number;
  newEnrollmentId: number;
  fromOfferingId: number;
  toOfferingId: number;
  status: "SWAPPED";
  version: number;
  promotedStudentId?: number | null;
}

export async function swapSection(
  fromEnrollmentId: number,
  toOfferingId: number,
  idempotencyKey?: string,
): Promise<SwapResult> {
  const headers: Record<string, string> = {};
  if (idempotencyKey) {
    headers["Idempotency-Key"] = idempotencyKey;
  }
  return http<SwapResult>(
    "/enroll/swap",
    "POST",
    { fromEnrollmentId, toOfferingId },
    undefined,
    true,
    headers,
  );
}
