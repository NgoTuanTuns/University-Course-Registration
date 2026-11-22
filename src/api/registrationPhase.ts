import { http } from "./http";

export type RegistrationPhaseCode =
  "STUDY_PLAN_OPEN" | "CLASS_OPENING_REVIEW" | "ENROLLMENT_OPEN" | "LOCKED";

export interface RegistrationPhaseInfo {
  term: string;
  phase: RegistrationPhaseCode;
  phaseLabel: string;
  phaseDescription: string;
  phaseEndsAt: string | null;
  note: string | null;
  canEditStudyPlan: boolean;
  canEnroll: boolean;
  updatedAt: string | null;
}

export interface UpdateRegistrationPhaseInput {
  term: string;
  phase: RegistrationPhaseCode;
  phaseEndsAt: string | null;
  note: string | null;
}

export const getRegistrationPhase = (term?: string) =>
  http<RegistrationPhaseInfo>(
    term
      ? `/registration-phase?term=${encodeURIComponent(term)}`
      : "/registration-phase",
  );

export const updateRegistrationPhase = (input: UpdateRegistrationPhaseInput) =>
  http<RegistrationPhaseInfo>("/admin/registration-phase", "PATCH", input);
