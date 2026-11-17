import { http } from "./http";

export interface AdminCourse {
  id: number;
  code: string;
  name: string;
  credits: number;
  description?: string | null;
}

export interface AdminCoursePage {
  items: AdminCourse[];
  total: number;
  page: number;
  pageSize: number;
}

export interface AdminPrereqItem {
  prereq_course_id: number;
  prereq_code: string;
  prereq_name: string;
  credits: number;
  type: "AND" | "OR";
  group_no: number;
}

export interface AdminOrGroup {
  group_no: number;
  options: AdminPrereqItem[];
}

export interface AdminCoursePrereqsResponse {
  course_id: number;
  course_code: string;
  course_name: string;
  and_prerequisites: AdminPrereqItem[];
  or_groups: AdminOrGroup[];
  items: AdminPrereqItem[];
}

export interface AdminPrereqEdge {
  course_id: number;
  course_code: string;
  course_name: string;
  prereq_course_id: number;
  prereq_code: string;
  prereq_name: string;
  type: "AND" | "OR";
  group_no: number;
}

export interface AdminPrereqListPage {
  items: AdminPrereqEdge[];
  total: number;
}

export interface AdminPrereqCreate {
  course_id: number;
  prereq_course_id: number;
  type: "AND" | "OR";
  group_no?: number;
}

export interface AdminPrereqUpdate {
  type: "AND" | "OR";
  group_no?: number;
}

// ---------------------------------------------------------------------------
// 1. Quản trị học phần (/admin/courses)
// ---------------------------------------------------------------------------
export const listAdminCourses = (query = "") =>
  http<AdminCoursePage>(`/admin/courses${query ? `?${query}` : ""}`);

export const createAdminCourse = (data: Omit<AdminCourse, "id">) =>
  http<AdminCourse>("/admin/courses", "POST", data);

export const updateAdminCourse = (
  id: number,
  data: Partial<Omit<AdminCourse, "id">>,
) => http<AdminCourse>(`/admin/courses/${id}`, "PUT", data);

export const deleteAdminCourse = (id: number) =>
  http<{ message: string }>(`/admin/courses/${id}`, "DELETE");

// ---------------------------------------------------------------------------
// 2. Quản trị điều kiện tiên quyết (/admin/prereqs)
// ---------------------------------------------------------------------------
export const getAdminCoursePrerequisites = (courseId: number) =>
  http<AdminCoursePrereqsResponse>(`/admin/prereqs/${courseId}`);

export const listAdminPrerequisites = (courseId?: number) => {
  const query = courseId ? `?course_id=${courseId}` : "";
  return http<AdminPrereqListPage>(`/admin/prereqs${query}`);
};

export const createAdminPrerequisite = (data: AdminPrereqCreate) =>
  http<AdminPrereqEdge>("/admin/prereqs", "POST", data);

export const updateAdminPrerequisite = (
  courseId: number,
  prereqCourseId: number,
  data: AdminPrereqUpdate,
) =>
  http<AdminPrereqEdge>(
    `/admin/prereqs/${courseId}/${prereqCourseId}`,
    "PUT",
    data,
  );

export const deleteAdminPrerequisite = (
  courseId: number,
  prereqCourseId: number,
) =>
  http<{ message: string }>(
    `/admin/prereqs/${courseId}/${prereqCourseId}`,
    "DELETE",
  );
