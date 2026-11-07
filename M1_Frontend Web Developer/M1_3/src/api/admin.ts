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

export const listAdminCourses = (query = "") =>
  http<AdminCoursePage>(`/admin/courses${query ? `?${query}` : ""}`);
export const createAdminCourse = (data: Omit<AdminCourse, "id">) =>
  http<AdminCourse>("/admin/courses", "POST", data);
export const updateAdminCourse = (id: number, data: Partial<Omit<AdminCourse, "id">>) =>
  http<AdminCourse>(`/admin/courses/${id}`, "PUT", data);
export const deleteAdminCourse = (id: number) =>
  http<{ message: string }>(`/admin/courses/${id}`, "DELETE");
