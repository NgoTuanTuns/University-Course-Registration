import type {
  AcademicRecordResponse,
  PrereqGraphResponse,
  PrerequisiteCheck,
  PrerequisiteExplain,
} from "../types";
import { http } from "./http";

export const check = (courseId: number) =>
  http<PrerequisiteCheck>(`/prerequisites/check?course_id=${courseId}`);

export const explain = (courseId: number) =>
  http<PrerequisiteExplain>("/prerequisites/explain", "POST", { courseId });

export const getPrerequisiteGraph = () =>
  http<PrereqGraphResponse>("/prerequisites/graph");

export const getAcademicRecord = () =>
  http<AcademicRecordResponse>("/students/me/academic-record");
