import { http } from "./http";

export interface TuitionItem {
  enrollmentId: number;
  courseCode: string;
  courseName: string;
  section: string;
  credits: number;
  category: string;
  unitPrice: number;
  labFee: number;
  subtotal: number;
}

export interface TuitionEstimate {
  term: string;
  currency: string;
  status: string;
  paymentDeadline: string;
  totalCourses: number;
  totalCredits: number;
  tuitionSubtotal: number;
  labFeeTotal: number;
  totalAmount: number;
  items: TuitionItem[];
}

export const getMyTuition = (term?: string) =>
  http<TuitionEstimate>(
    term
      ? `/students/me/tuition?term=${encodeURIComponent(term)}`
      : "/students/me/tuition",
  );

export function formatVnd(amount: number): string {
  return `${new Intl.NumberFormat("vi-VN").format(amount)} ₫`;
}
