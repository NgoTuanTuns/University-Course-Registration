import { useEffect, useState } from "react";
import {
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  CalendarDays,
} from "lucide-react";
import * as api from "../api";
import type { Enrollment, Offering } from "../types";
import { parseTime } from "../features/timetable/conflicts";

const DAYS = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"];
const SHIFTS = [
  { id: 1, label: "Ca 1", time: "06:50–09:20" },
  { id: 2, label: "Ca 2", time: "09:30–12:00" },
  { id: 3, label: "Ca 3", time: "12:45–15:15" },
  { id: 4, label: "Ca 4", time: "15:25–17:55" },
  { id: 5, label: "Ca 5", time: "18:05–20:35" },
];

function getShiftIndex(start: string): number {
  const m = parseTime(start);
  if (m < 9 * 60 + 25) return 1;
  if (m < 12 * 60 + 15) return 2;
  if (m < 15 * 60 + 20) return 3;
  if (m < 18 * 60) return 4;
  return 5;
}

export function AutoSchedulerModal({
  regs,
  canEnroll,
  onClose,
  onEnrolled,
  notify,
}: {
  regs: Enrollment[];
  canEnroll: boolean;
  onClose: () => void;
  onEnrolled: () => Promise<void>;
  notify: (s: string) => void;
}) {
  const [prefs, setPrefs] = useState<api.SchedulerPreferences>({
    avoidFirstShift: false,
    avoidNightShift: true,
    avoidSaturday: false,
    minimizeDays: true,
    timeOfDay: "ANY",
  });
  const [selectedCourseIds, setSelectedCourseIds] = useState<number[] | null>(
    null,
  );
  const [data, setData] = useState<api.SchedulerSuggestResponse | null>(null);
  const [activePlanIdx, setActivePlanIdx] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [batchBusy, setBatchBusy] = useState(false);
  const [batchResults, setBatchResults] = useState<
    { code: string; section: string; ok: boolean; text: string }[]
  >([]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !batchBusy) onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose, batchBusy]);

  async function runSuggest(
    courseIds: number[] | null,
    nextPrefs: api.SchedulerPreferences,
  ) {
    setLoading(true);
    setError("");
    setBatchResults([]);
    try {
      const res = await api.suggestSchedules({
        courseIds,
        preferences: nextPrefs,
        maxResults: 3,
      });
      setData(res);
      setActivePlanIdx(0);
      setSelectedCourseIds(
        res.targetCourses.filter((c) => c.selected).map((c) => c.courseId),
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void runSuggest(null, prefs);
  }, []);

  const toggleCourse = (cid: number) => {
    const list = selectedCourseIds || [];
    const nextIds = list.includes(cid)
      ? list.filter((x) => x !== cid)
      : [...list, cid];
    setSelectedCourseIds(nextIds);
    void runSuggest(nextIds, prefs);
  };

  const activePlan = data?.plans[activePlanIdx] || null;

  async function handleBatchEnroll() {
    if (!activePlan || batchBusy || !canEnroll) return;
    if (
      !window.confirm(
        `Đăng ký toàn bộ ${activePlan.offerings.length} lớp học phần (${activePlan.addedCredits} TC) trong Phương án ${activePlan.rank}?`,
      )
    ) {
      return;
    }
    setBatchBusy(true);
    const results: {
      code: string;
      section: string;
      ok: boolean;
      text: string;
    }[] = [];
    for (const off of activePlan.offerings) {
      try {
        const key = `auto-${off.id}-${Date.now()}`;
        const res = await api.enroll(off.id, key);
        if (res.status === "WAITLISTED") {
          results.push({
            code: off.code,
            section: off.section,
            ok: true,
            text: `Vào danh sách chờ (vị trí #${res.position || 1})`,
          });
        } else {
          results.push({
            code: off.code,
            section: off.section,
            ok: true,
            text: "Đăng ký thành công",
          });
        }
      } catch (e) {
        results.push({
          code: off.code,
          section: off.section,
          ok: false,
          text: (e as Error).message,
        });
      }
    }
    setBatchResults(results);
    await onEnrolled();
    try {
      const refreshed = await api.suggestSchedules({
        courseIds: null,
        preferences: prefs,
        maxResults: 3,
      });
      setData(refreshed);
      setActivePlanIdx(0);
      setSelectedCourseIds(
        refreshed.targetCourses
          .filter((c) => c.selected)
          .map((c) => c.courseId),
      );
    } catch {
      /* giữ kết quả batch nếu không tải lại được gợi ý */
    }
    const okCount = results.filter((r) => r.ok).length;
    notify(
      `Đã đăng ký xong ${okCount}/${results.length} lớp từ Phương án ${activePlan.rank}.`,
    );
    setBatchBusy(false);
  }

  // Xây bảng 5 ca × 7 ngày kết hợp lớp đã ĐK và lớp gợi ý
  const cellMap = new Map<
    string,
    { offering: Offering; kind: "enrolled" | "suggested" }[]
  >();
  for (const e of regs) {
    for (const s of e.offering.schedule) {
      const key = `${getShiftIndex(s.start)}-${s.day}`;
      const arr = cellMap.get(key) || [];
      arr.push({ offering: e.offering, kind: "enrolled" });
      cellMap.set(key, arr);
    }
  }
  if (activePlan) {
    for (const off of activePlan.offerings) {
      for (const s of off.schedule) {
        const key = `${getShiftIndex(s.start)}-${s.day}`;
        const arr = cellMap.get(key) || [];
        arr.push({ offering: off, kind: "suggested" });
        cellMap.set(key, arr);
      }
    }
  }

  return (
    <div
      className="modal-backdrop"
      onClick={(e) => {
        if (e.target === e.currentTarget && !batchBusy) onClose();
      }}
    >
      <section
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="auto-sched-title"
        style={{
          width: "min(1220px, 96vw)",
          maxHeight: "93vh",
          padding: 0,
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            padding: "16px 22px",
            borderBottom: "1px solid var(--border)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 12,
            background: "var(--panel)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <Sparkles size={20} style={{ color: "var(--red)" }} />
            <div>
              <h2 id="auto-sched-title" style={{ margin: 0, fontSize: 19 }}>
                Gợi ý xếp lịch tự động (Smart Auto-Scheduler)
              </h2>
              <small className="muted">
                Tự động tìm phương án thời khóa biểu không trùng ca từ Kế hoạch
                học tập kỳ 2026-2 của bạn.
              </small>
            </div>
          </div>
          <button
            type="button"
            className="btn-outline"
            disabled={batchBusy}
            onClick={onClose}
          >
            Đóng (Esc)
          </button>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "320px minmax(0, 1fr)",
            overflow: "auto",
            flex: 1,
          }}
        >
          {/* Cột trái: chọn môn & ưu tiên */}
          <div
            style={{
              padding: "18px 20px",
              borderRight: "1px solid var(--border)",
              background: "var(--soft)",
              display: "flex",
              flexDirection: "column",
              gap: 16,
            }}
          >
            <div>
              <h4 style={{ margin: "0 0 8px", fontSize: 13.5 }}>
                1. Học phần mục tiêu (từ KHHT đã mở lớp)
              </h4>
              {!data?.targetCourses.length ? (
                <p className="muted" style={{ fontSize: 12.5, margin: 0 }}>
                  Bạn đã đăng ký hết các môn mở lớp trong KHHT hoặc chưa có môn
                  nào khả dụng.
                </p>
              ) : (
                <div
                  style={{
                    display: "grid",
                    gap: 6,
                    maxHeight: 230,
                    overflowY: "auto",
                    paddingRight: 4,
                  }}
                >
                  {data.targetCourses.map((c) => {
                    const checked = (selectedCourseIds || []).includes(
                      c.courseId,
                    );
                    return (
                      <label
                        key={c.courseId}
                        style={{
                          display: "flex",
                          alignItems: "flex-start",
                          gap: 8,
                          padding: "8px 10px",
                          background: "var(--panel)",
                          border: "1px solid var(--border)",
                          cursor: "pointer",
                          fontWeight: 500,
                        }}
                      >
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() => toggleCourse(c.courseId)}
                          style={{ width: "auto", marginTop: 3 }}
                        />
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div
                            style={{
                              display: "flex",
                              justifyContent: "space-between",
                              gap: 6,
                            }}
                          >
                            <b className="mono-id" style={{ fontSize: 12 }}>
                              {c.code}
                            </b>
                            <span className="muted" style={{ fontSize: 11.5 }}>
                              {c.credits} TC
                            </span>
                          </div>
                          <div
                            style={{
                              fontSize: 12.5,
                              color: "var(--text)",
                              lineHeight: 1.35,
                            }}
                          >
                            {c.name}
                          </div>
                        </div>
                      </label>
                    );
                  })}
                </div>
              )}
            </div>

            <div>
              <h4 style={{ margin: "0 0 8px", fontSize: 13.5 }}>
                2. Tiêu chí ưu tiên
              </h4>
              <div style={{ display: "grid", gap: 7 }}>
                {[
                  ["avoidFirstShift", "Tránh Ca 1 sáng sớm (06:50)"],
                  ["avoidNightShift", "Tránh Ca 5 buổi tối (18:05)"],
                  ["avoidSaturday", "Ưu tiên nghỉ Thứ 7"],
                  ["minimizeDays", "Dồn ít ngày đi học nhất"],
                ].map(([key, label]) => (
                  <label
                    key={key}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 8,
                      fontSize: 13,
                      fontWeight: 500,
                      cursor: "pointer",
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={Boolean(
                        prefs[key as keyof api.SchedulerPreferences],
                      )}
                      onChange={(e) => {
                        const nextPrefs: api.SchedulerPreferences = {
                          ...prefs,
                          [key]: e.target.checked,
                        };
                        setPrefs(nextPrefs);
                        void runSuggest(selectedCourseIds, nextPrefs);
                      }}
                      style={{ width: "auto", margin: 0 }}
                    />
                    {label}
                  </label>
                ))}
                <label style={{ marginTop: 4 }}>
                  Buổi học ưu tiên
                  <select
                    value={prefs.timeOfDay}
                    onChange={(e) => {
                      const nextPrefs: api.SchedulerPreferences = {
                        ...prefs,
                        timeOfDay: e.target
                          .value as api.SchedulerPreferences["timeOfDay"],
                      };
                      setPrefs(nextPrefs);
                      void runSuggest(selectedCourseIds, nextPrefs);
                    }}
                  >
                    <option value="ANY">Linh hoạt cả ngày</option>
                    <option value="MORNING">Ưu tiên buổi sáng (Ca 1–2)</option>
                    <option value="AFTERNOON">
                      Ưu tiên buổi chiều (Ca 3–4)
                    </option>
                  </select>
                </label>
              </div>
            </div>

            <button
              type="button"
              className="primary"
              disabled={loading || batchBusy}
              onClick={() => void runSuggest(selectedCourseIds || [], prefs)}
            >
              {loading ? "Đang tìm lịch tối ưu…" : "Tìm lịch tối ưu"}
            </button>
          </div>

          {/* Cột phải: kết quả 3 phương án + lưới TKB 5 ca */}
          <div
            style={{
              padding: "18px 22px",
              display: "flex",
              flexDirection: "column",
              gap: 14,
              background: "var(--panel)",
            }}
          >
            {error && (
              <div className="notice" role="alert">
                {error}
              </div>
            )}
            {data?.creditLimitWarning && (
              <div className="notice" role="status">
                <AlertTriangle size={15} /> {data.creditLimitWarning}
              </div>
            )}
            {data && data.unschedulable.length > 0 && (
              <div
                style={{
                  padding: "10px 14px",
                  background: "#fef3c7",
                  borderLeft: "4px solid #d97706",
                  color: "#78350f",
                  fontSize: 12.5,
                }}
              >
                <b>Một số môn không thể đưa vào lịch:</b>{" "}
                {data.unschedulable
                  .map((u) => `${u.code} (${u.detail})`)
                  .join(" · ")}
              </div>
            )}

            {loading ? (
              <div className="skeleton">
                Đang phân tích các tổ hợp lớp không trùng ca…
              </div>
            ) : !data?.plans.length ? (
              <div className="empty" style={{ padding: "36px 16px" }}>
                Không tìm thấy tổ hợp lớp nào hoàn toàn không trùng ca cho các
                môn đã chọn. Hãy thử bỏ bớt 1 môn ở cột bên trái rồi bấm{" "}
                <b>Tìm lịch tối ưu</b> lại.
              </div>
            ) : (
              <>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: 10,
                    flexWrap: "wrap",
                  }}
                >
                  <div className="actions" style={{ marginTop: 0, gap: 8 }}>
                    {data.plans.map((p, idx) => (
                      <button
                        key={p.rank}
                        type="button"
                        className={
                          idx === activePlanIdx ? "primary" : "btn-outline"
                        }
                        onClick={() => {
                          setActivePlanIdx(idx);
                          setBatchResults([]);
                        }}
                      >
                        Phương án {p.rank} ({p.studyDaysCount} ngày · +
                        {p.addedCredits} TC)
                      </button>
                    ))}
                  </div>
                  <button
                    type="button"
                    className="btn-tdtu-red"
                    disabled={!canEnroll || batchBusy || !activePlan}
                    title={
                      !canEnroll
                        ? "Cổng đăng ký học phần hiện đang đóng"
                        : undefined
                    }
                    onClick={() => void handleBatchEnroll()}
                  >
                    {batchBusy
                      ? "Đang đăng ký hàng loạt…"
                      : `Đăng ký toàn bộ Phương án ${activePlan?.rank}`}
                  </button>
                </div>

                {activePlan && (
                  <>
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                        flexWrap: "wrap",
                        fontSize: 12,
                      }}
                    >
                      <span
                        className="pill"
                        style={{ background: "#004b91", color: "#fff" }}
                      >
                        Điểm phù hợp: {activePlan.score}
                      </span>
                      <span className="pill">
                        Tổng tín chỉ sau ĐK: {activePlan.totalCredits} /{" "}
                        {data.maxCredits} TC
                      </span>
                      {activePlan.tags.map((t) => (
                        <span key={t} className="pill">
                          {t}
                        </span>
                      ))}
                    </div>

                    {batchResults.length > 0 && (
                      <div
                        style={{
                          padding: "12px 14px",
                          background: "var(--soft)",
                          border: "1px solid var(--border)",
                          display: "grid",
                          gap: 6,
                          fontSize: 12.5,
                        }}
                      >
                        <b>Kết quả đăng ký hàng loạt:</b>
                        {batchResults.map((r) => (
                          <div
                            key={`${r.code}-${r.section}`}
                            style={{
                              display: "flex",
                              alignItems: "center",
                              gap: 8,
                              color: r.ok ? "#047857" : "#d71920",
                            }}
                          >
                            {r.ok ? (
                              <CheckCircle2 size={14} />
                            ) : (
                              <AlertTriangle size={14} />
                            )}
                            <b>
                              {r.code} (Lớp {r.section}):
                            </b>{" "}
                            <span>{r.text}</span>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Lưới TKB 5 ca TDTU trực quan */}
                    <div>
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          marginBottom: 8,
                          fontSize: 12,
                        }}
                      >
                        <b
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: 6,
                          }}
                        >
                          <CalendarDays size={15} /> Xem trước phân bổ 5 ca TDTU
                        </b>
                        <div style={{ display: "flex", gap: 14 }}>
                          <span style={{ color: "#004b91", fontWeight: 700 }}>
                            ■ Đã đăng ký
                          </span>
                          <span style={{ color: "#b45309", fontWeight: 700 }}>
                            ▤ Gợi ý mới
                          </span>
                        </div>
                      </div>
                      <div className="table-scroll">
                        <table style={{ fontSize: 12 }}>
                          <thead>
                            <tr>
                              <th style={{ width: 92 }}>Ca học</th>
                              {DAYS.map((d) => (
                                <th key={d}>{d}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {SHIFTS.map((sh) => (
                              <tr key={sh.id}>
                                <td>
                                  <b>{sh.label}</b>
                                  <small
                                    className="muted"
                                    style={{ display: "block", fontSize: 10.5 }}
                                  >
                                    {sh.time}
                                  </small>
                                </td>
                                {DAYS.map((_, idx) => {
                                  const entries =
                                    cellMap.get(`${sh.id}-${idx + 1}`) || [];
                                  return (
                                    <td
                                      key={idx}
                                      style={{
                                        verticalAlign: "top",
                                        padding: 6,
                                        minWidth: 100,
                                      }}
                                    >
                                      {entries.map((item) => (
                                        <div
                                          key={`${item.kind}-${item.offering.id}`}
                                          style={{
                                            padding: "5px 7px",
                                            marginBottom: 4,
                                            background:
                                              item.kind === "enrolled"
                                                ? "#004b91"
                                                : "#fef3c7",
                                            color:
                                              item.kind === "enrolled"
                                                ? "#ffffff"
                                                : "#78350f",
                                            border:
                                              item.kind === "enrolled"
                                                ? "1px solid #003366"
                                                : "2px dashed #d97706",
                                            fontSize: 11.5,
                                            lineHeight: 1.3,
                                          }}
                                        >
                                          <b>{item.offering.code}</b> · L
                                          {item.offering.section}
                                          <div
                                            style={{
                                              fontSize: 10.5,
                                              opacity: 0.9,
                                            }}
                                          >
                                            {item.offering.room}
                                          </div>
                                        </div>
                                      ))}
                                    </td>
                                  );
                                })}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>

                    {/* Danh sách lớp đề xuất */}
                    <div
                      style={{
                        display: "grid",
                        gridTemplateColumns:
                          "repeat(auto-fill, minmax(240px, 1fr))",
                        gap: 8,
                      }}
                    >
                      {activePlan.offerings.map((o) => (
                        <div
                          key={o.id}
                          style={{
                            padding: "9px 11px",
                            border: "1px solid var(--border)",
                            borderLeft: "3px solid #d97706",
                            fontSize: 12,
                          }}
                        >
                          <div>
                            <b className="mono-id">{o.code}</b> · Lớp{" "}
                            <b>{o.section}</b> ({o.credits} TC)
                          </div>
                          <div style={{ fontWeight: 600, margin: "2px 0" }}>
                            {o.name}
                          </div>
                          <div className="muted">
                            {o.schedule
                              .map(
                                (s) =>
                                  `${s.day === 7 ? "CN" : `T${s.day + 1}`} Ca ${getShiftIndex(s.start)} (${s.start}–${s.end})`,
                              )
                              .join(", ")}{" "}
                            · {o.room} · {o.enrolledCount}/{o.capacity}
                          </div>
                        </div>
                      ))}
                    </div>
                  </>
                )}
              </>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
