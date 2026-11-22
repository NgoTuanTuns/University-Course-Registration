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
  prereqCourseId: number;
  prereqCode: string;
  prereqName: string;
  credits: number;
  type: "AND" | "OR";
  groupNo: number;
}

export interface AdminOrGroup {
  groupNo: number;
  options: AdminPrereqItem[];
}

export interface AdminCoursePrereqsResponse {
  courseId: number;
  courseCode: string;
  courseName: string;
  andPrerequisites: AdminPrereqItem[];
  orGroups: AdminOrGroup[];
  items: AdminPrereqItem[];
}

export interface AdminPrereqEdge {
  courseId: number;
  courseCode: string;
  courseName: string;
  prereqCourseId: number;
  prereqCode: string;
  prereqName: string;
  type: "AND" | "OR";
  groupNo: number;
}

export interface AdminPrereqListPage {
  items: AdminPrereqEdge[];
  total: number;
}

export interface AdminPrereqCreate {
  courseId: number;
  prereqCourseId: number;
  type: "AND" | "OR";
  groupNo?: number;
}

export interface AdminPrereqUpdate {
  type: "AND" | "OR";
  groupNo?: number;
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

// ---------------------------------------------------------------------------
// 3. Quản trị sĩ số lớp học phần phục vụ test đầy lớp / Waitlist
// ---------------------------------------------------------------------------
export interface AdminOfferingCapacityActionResponse {
  offeringId: number;
  enrolledCount: number;
  capacity: number;
  addedCount?: number;
  promotedStudentId?: number | null;
  message: string;
}

export const fillAdminOffering = (offeringId: number) =>
  http<AdminOfferingCapacityActionResponse>(
    `/admin/offerings/${offeringId}/fill`,
    "POST",
  );

export const releaseAdminOfferingSeat = (offeringId: number) =>
  http<AdminOfferingCapacityActionResponse>(
    `/admin/offerings/${offeringId}/release-seat`,
    "POST",
  );
