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
