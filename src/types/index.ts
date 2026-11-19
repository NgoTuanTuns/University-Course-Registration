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
  minAccumulatedCredits?: number;
  section: string;
  instructor: string;
  room: string;
  schedule: Slot[];
  enrolledCount: number;
  capacity: number;
  eligibilityStatus?:
    "RECOMMENDED" | "ELIGIBLE" | "LOCKED" | "COMPLETED" | null;
}

export interface User {
  id: number;
  email: string;
  fullName: string;
  role: "student" | "admin";
  mssv?: string | null;
  faculty?: string | null;
  maxCredits: number;
  accumulatedCredits?: number;
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

export interface PrereqGraphNode {
  id: number;
  code: string;
  name: string;
  credits: number;
  minAccumulatedCredits: number;
  level: number;
  status: "COMPLETED" | "ELIGIBLE" | "LOCKED";
  missingCredits: number;
  missingCourses: string[];
  andPrereqs: string[];
  orGroups: Array<{ groupNo: number; options: string[] }>;
}

export interface PrereqGraphEdge {
  courseId: number;
  prereqCourseId: number;
  type: "AND" | "OR";
  groupNo: number;
}

export interface PrereqGraphResponse {
  studentAccumulatedCredits: number;
  nodes: PrereqGraphNode[];
  edges: PrereqGraphEdge[];
}

export interface CompletedCourseItem {
  courseId: number;
  code: string;
  name: string;
  credits: number;
  grade: number | null;
  term: string | null;
}

export interface AcademicRecordResponse {
  studentId: number;
  mssv: string | null;
  fullName: string;
  faculty?: string | null;
  program: string | null;
  accumulatedCredits: number;
  maxCredits: number;
  gpa: number;
  completedCount: number;
  completedCourses: CompletedCourseItem[];
}
