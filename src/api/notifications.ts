import { http } from "./http";

export type NotificationKind =
  | "WAITLIST_PROMOTED"
  | "COURSE_NOT_OPENED"
  | "NEW_SECTIONS_OPENED"
  | "PHASE_UPDATE";

export interface StudentNotification {
  id: string;
  kind: NotificationKind;
  title: string;
  message: string;
  link: string | null;
  createdAt: string | null;
}

export interface StudentNotificationList {
  items: StudentNotification[];
}

export const getMyNotifications = (term?: string) =>
  http<StudentNotificationList>(
    term
      ? `/students/me/notifications?term=${encodeURIComponent(term)}`
      : "/students/me/notifications",
  );
