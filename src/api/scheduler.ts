import { http } from "./http";
import type { Offering } from "../types";

export interface SchedulerPreferences {
  avoidFirstShift: boolean;
  avoidNightShift: boolean;
  avoidSaturday: boolean;
  minimizeDays: boolean;
  timeOfDay: "ANY" | "MORNING" | "AFTERNOON";
}

export interface SchedulerSuggestRequest {
  courseIds?: number[] | null;
  term?: string;
  preferences: SchedulerPreferences;
  maxResults?: number;
}

export interface SchedulerTargetCourse {
  courseId: number;
  code: string;
  name: string;
  credits: number;
  inStudyPlan: boolean;
  selected: boolean;
}

export interface UnschedulableCourse {
  courseId: number;
  code: string;
  name: string;
  credits: number;
  reason: string;
  detail: string;
}

export interface SuggestedPlan {
  rank: number;
  score: number;
  totalCredits: number;
  addedCredits: number;
  studyDaysCount: number;
  tags: string[];
  offerings: Offering[];
}

export interface SchedulerSuggestResponse {
  term: string;
  currentCredits: number;
  maxCredits: number;
  creditLimitWarning: string | null;
  targetCourses: SchedulerTargetCourse[];
  plans: SuggestedPlan[];
  unschedulable: UnschedulableCourse[];
}

export const suggestSchedules = (req: SchedulerSuggestRequest) =>
  http<SchedulerSuggestResponse>("/scheduler/suggest", "POST", req);
