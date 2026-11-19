import { describe, expect, it } from "vitest";
import {
  detectPromotedWaitlist,
  formatPrereqCycleMessage,
  getCreditStatus,
  willExceedCredits,
} from "./helpers";

describe("getCreditStatus & willExceedCredits", () => {
  it("trả trạng thái bình thường dưới 90%", () => {
    const status = getCreditStatus(15, 25);
    expect(status.level).toBe("normal");
    expect(status.percent).toBe(60);
    expect(status.warningText).toBeNull();
  });

  it("cảnh báo vàng khi đạt từ 90% đến dưới 100%", () => {
    const status = getCreditStatus(23, 25);
    expect(status.level).toBe("warning");
    expect(status.color).toBe("#f59e0b");
    expect(status.warningText).toContain("90%");
  });

  it("cảnh báo đỏ khi đạt hoặc vượt 100%", () => {
    const status = getCreditStatus(25, 25);
    expect(status.level).toBe("full");
    expect(status.color).toBe("#ef4444");
    expect(status.percent).toBe(100);
    expect(status.warningText).toContain("giới hạn");
  });

  it("kiểm tra vượt hạn mức tín chỉ khi đăng ký thêm môn", () => {
    expect(willExceedCredits(24, 3, 25)).toBe(true);
    expect(willExceedCredits(22, 3, 25)).toBe(false);
  });
});

describe("detectPromotedWaitlist", () => {
  const prev = [
    { id: 10, offeringId: 101, code: "INT331", name: "PTTKHT" },
    { id: 11, offeringId: 102, code: "INT341", name: "Học máy" },
  ];

  it("phát hiện đúng môn được đôn tự động vào TKB ACTIVE", () => {
    const next = [{ id: 11, offeringId: 102, code: "INT341", name: "Học máy" }];
    const promoted = detectPromotedWaitlist(
      prev,
      next,
      new Set([101]),
      new Set(),
    );
    expect(promoted).toHaveLength(1);
    expect(promoted[0].code).toBe("INT331");
  });

  it("không báo nhầm khi sinh viên tự bấm rời hàng chờ", () => {
    const next = [{ id: 11, offeringId: 102, code: "INT341", name: "Học máy" }];
    const promoted = detectPromotedWaitlist(
      prev,
      next,
      new Set([101]),
      new Set([10]),
    );
    expect(promoted).toHaveLength(0);
  });
});

describe("formatPrereqCycleMessage", () => {
  it("hiển thị rõ đường đi chu trình với mã môn", () => {
    const msg = formatPrereqCycleMessage(["INT101", "INT131", "INT101"]);
    expect(msg).toContain("INT101 → INT131 → INT101");
  });

  it("ánh xạ ID sang mã môn khi backend trả về ID số", () => {
    const map = new Map([
      [1, "INT101"],
      [2, "INT131"],
    ]);
    const msg = formatPrereqCycleMessage([1, 2, 1], map);
    expect(msg).toContain("INT101 → INT131 → INT101");
  });
});
