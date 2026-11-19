export interface CreditStatus {
  percent: number;
  level: "normal" | "warning" | "full";
  color?: string;
  warningText: string | null;
}

export function getCreditStatus(
  currentCredits: number,
  maxCredits: number,
): CreditStatus {
  const safeMax = maxCredits > 0 ? maxCredits : 25;
  const ratio = currentCredits / safeMax;
  const percent = Math.min(100, Math.max(0, ratio * 100));

  if (currentCredits >= safeMax) {
    return {
      percent,
      level: "full",
      color: "#ef4444",
      warningText: "Đã đạt giới hạn tín chỉ.",
    };
  }
  if (ratio >= 0.9) {
    return {
      percent,
      level: "warning",
      color: "#f59e0b",
      warningText: "Bạn đã sử dụng từ 90% hạn mức tín chỉ.",
    };
  }
  return {
    percent,
    level: "normal",
    warningText: null,
  };
}

export function willExceedCredits(
  currentCredits: number,
  addingCredits: number,
  maxCredits: number,
): boolean {
  const safeMax = maxCredits > 0 ? maxCredits : 25;
  return currentCredits + addingCredits > safeMax;
}

export interface WaitlistSummary {
  id: number;
  offeringId: number;
  code: string;
  name: string;
}

export function detectPromotedWaitlist(
  previous: WaitlistSummary[],
  current: WaitlistSummary[],
  activeOfferingIds: Set<number>,
  manuallyLeftIds: Set<number>,
): WaitlistSummary[] {
  const currentOfferingIds = new Set(current.map((item) => item.offeringId));
  return previous.filter(
    (entry) =>
      !currentOfferingIds.has(entry.offeringId) &&
      !manuallyLeftIds.has(entry.id) &&
      activeOfferingIds.has(entry.offeringId),
  );
}

export function formatPrereqCycleMessage(
  cyclePath: unknown,
  courseCodeById?: Map<number, string>,
): string {
  if (Array.isArray(cyclePath) && cyclePath.length > 0) {
    const labels = cyclePath.map((node) => {
      if (typeof node === "number" && courseCodeById?.has(node)) {
        return courseCodeById.get(node) as string;
      }
      return String(node);
    });
    return `Không thể thêm: quan hệ này tạo vòng lặp giữa các học phần (${labels.join(" → ")}).`;
  }
  return "Không thể thêm: quan hệ này tạo vòng lặp giữa các học phần.";
}
