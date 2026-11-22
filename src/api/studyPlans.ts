import type {
  AdminFinalizeStudyPlansResponse,
  AdminStudyPlanSummaryResponse,
  StudyPlanResponse,
} from "../types";
import { http } from "./http";

export const getMyStudyPlan = (term?: string) =>
  http<StudyPlanResponse>(
    term ? `/study-plans?term=${encodeURIComponent(term)}` : "/study-plans",
  );

export const addToStudyPlan = (courseId: number, term?: string) =>
  http<StudyPlanResponse>("/study-plans", "POST", { courseId, term });

export const removeFromStudyPlan = (planId: number) =>
  http<StudyPlanResponse>(`/study-plans/${planId}`, "DELETE");

export const getAdminStudyPlanSummary = (term?: string, status?: string) => {
  const params = new URLSearchParams();
  if (term) params.set("term", term);
  if (status && status !== "ALL") params.set("status", status);
  const qs = params.toString();
  return http<AdminStudyPlanSummaryResponse>(
    qs ? `/admin/study-plans/summary?${qs}` : "/admin/study-plans/summary",
  );
};

export const finalizeAdminStudyPlans = (
  minStudentsToOpen: number,
  term?: string,
) =>
  http<AdminFinalizeStudyPlansResponse>("/admin/study-plans/finalize", "POST", {
    minStudentsToOpen,
    term,
  });
