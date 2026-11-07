import { http } from "./http";

export interface EnrollmentResult {
  status: "ACTIVE" | "WAITLISTED" | string;
}

export function enroll(offeringId: number, idempotencyKey: string) {
  return http<EnrollmentResult>(
    "/enroll",
    "POST",
    { offeringId },
    undefined,
    true,
    { "Idempotency-Key": idempotencyKey },
  );
}

export const cancel = (enrollmentId: number) =>
  http<{ message?: string }>(`/enroll/${enrollmentId}`, "DELETE");
