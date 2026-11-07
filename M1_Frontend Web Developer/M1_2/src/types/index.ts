export interface Slot {
  day: number;
  start: string;
  end: string;
}

export interface Offering {
  id: number;
  courseId: number;
  code: string;
  name: string;
  credits: number;
  section: string;
  instructor: string;
  room: string;
  schedule: Slot[];
  enrolledCount: number;
  capacity: number;
}

export interface User {
  id: number;
  email: string;
  fullName: string;
  role: "student" | "admin";
  mssv?: string | null;
  maxCredits: number;
}

export interface Session {
  accessToken: string;
  refreshToken: string;
  expiresIn?: number;
  user: User;
}

export interface Enrollment {
  id: number;
  offering: Offering;
  status: "ACTIVE" | "CANCELLED" | string;
}

export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}

export interface PrerequisiteCheck {
  courseId: number;
  courseCode: string;
  eligible: boolean;
  missingCourses: string[];
  unmetOrGroups: Array<{ groupNo: number; options: string[] }>;
}

export interface MissingCourse {
  courseCode: string;
  courseName: string;
  kind: "DIRECT" | "TRANSITIVE";
  requiredBy: string;
  path: string[];
}

export interface PrerequisiteExplain {
  courseId: number;
  courseCode: string;
  courseName: string;
  eligible: boolean;
  missing: MissingCourse[];
  unmetOrGroups: Array<{
    groupNo: number;
    requiredBy: string;
    options: Array<{
      courseCode: string;
      courseName: string;
      canTakeNow: boolean;
      missingCourses: string[];
    }>;
  }>;
  suggestedOrder: string[];
  totalMissing: number;
  truncated: boolean;
}

export interface ApiErrorBody {
  code: string;
  message: string;
  [key: string]: unknown;
}
