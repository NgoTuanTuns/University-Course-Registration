import type { PrerequisiteCheck, PrerequisiteExplain } from "../types";
import { http } from "./http";

export const check = (courseId: number) =>
  http<PrerequisiteCheck>(`/prerequisites/check?course_id=${courseId}`);

export const explain = (courseId: number) =>
  http<PrerequisiteExplain>("/prerequisites/explain", "POST", { courseId });
