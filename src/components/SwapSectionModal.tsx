import { useEffect, useState } from "react";
import { ArrowRightLeft, AlertTriangle, CheckCircle2 } from "lucide-react";
import * as api from "../api";
import type { Enrollment, Offering } from "../types";
import { findSlotConflicts, parseTime } from "../features/timetable/conflicts";

function getShiftLabel(start: string): string {
  const m = parseTime(start);
  if (m < 9 * 60 + 25) return "Ca 1";
  if (m < 12 * 60 + 15) return "Ca 2";
  if (m < 15 * 60 + 20) return "Ca 3";
  if (m < 18 * 60) return "Ca 4";
  return "Ca 5";
}

export function SwapSectionModal({
  current,
  regs,
  onClose,
  onSwapped,
  notify,
}: {
  current: Enrollment;
  regs: Enrollment[];
  onClose: () => void;
  onSwapped: () => Promise<void>;
  notify: (s: string) => void;
}) {
  const [candidates, setCandidates] = useState<Offering[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [swappingId, setSwappingId] = useState<number | null>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && swappingId === null) onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose, swappingId]);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    const params = new URLSearchParams({
      q: current.offering.code,
      page_size: "50",
    });
    api
      .courses(params.toString())
      .then((res) => {
        if (!active) return;
        const alts = res.items.filter(
          (o) =>
            o.courseId === current.offering.courseId &&
            o.id !== current.offering.id,
        );
        setCandidates(alts);
      })
      .catch((e) => {
        if (active) setError((e as Error).message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [current]);

  const otherEnrolled = regs
    .filter((r) => r.id !== current.id)
    .map((r) => r.offering);

  async function handleSwap(target: Offering) {
    if (swappingId !== null) return;
    setSwappingId(target.id);
    setError("");
    try {
      const key = `swap-${current.id}-${target.id}-${Date.now()}`;
      await api.swapSection(current.id, target.id, key);
      await onSwapped();
      notify(
        `Đã đổi thành công ${current.offering.code} từ Lớp ${current.offering.section} sang Lớp ${target.section}.`,
      );
      onClose();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSwappingId(null);
    }
  }

  return (
    <div
      className="modal-backdrop"
      onClick={(e) => {
        if (e.target === e.currentTarget && swappingId === null) onClose();
      }}
    >
      <section
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="swap-modal-title"
        style={{ width: "min(760px, 95vw)" }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 12,
            marginBottom: 12,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <ArrowRightLeft size={18} style={{ color: "var(--accent)" }} />
            <h2 id="swap-modal-title" style={{ margin: 0, fontSize: 19 }}>
              Đổi lớp học phần an toàn
            </h2>
          </div>
          <span className="code-badge">{current.offering.code}</span>
        </div>

        <div
          style={{
            padding: "12px 14px",
            background: "var(--soft)",
            borderLeft: "4px solid var(--accent)",
            marginBottom: 16,
          }}
        >
          <div style={{ fontSize: 12, color: "var(--muted)", marginBottom: 4 }}>
            Lớp hiện tại của bạn (được giữ nguyên nếu lớp đích hết chỗ hoặc
            trùng lịch)
          </div>
          <div style={{ fontWeight: 700, fontSize: 14.5 }}>
            {current.offering.code} — {current.offering.name} · Lớp{" "}
            {current.offering.section}
          </div>
          <div
            style={{
              fontSize: 12.5,
              color: "var(--muted)",
              marginTop: 4,
              display: "flex",
              gap: 10,
              flexWrap: "wrap",
            }}
          >
            <span>GV: {current.offering.instructor}</span>
            <span>·</span>
            <span>Phòng {current.offering.room}</span>
            {current.offering.schedule.map((s, idx) => (
              <span key={idx}>
                · {s.day === 7 ? "CN" : `T${s.day + 1}`}{" "}
                <b>{getShiftLabel(s.start)}</b> ({s.start}–{s.end})
              </span>
            ))}
          </div>
        </div>

        {error && (
          <div className="notice" role="alert" style={{ marginBottom: 14 }}>
            {error}
          </div>
        )}

        {loading ? (
          <div className="skeleton">Đang tải các lớp khác cùng học phần…</div>
        ) : !candidates.length ? (
          <div className="empty" style={{ padding: "24px 12px" }}>
            Học phần {current.offering.code} hiện không có lớp học phần nào khác
            để chuyển sang.
          </div>
        ) : (
          <div style={{ display: "grid", gap: 10 }}>
            {candidates.map((o) => {
              const isFull = o.enrolledCount >= o.capacity;
              const conflicts = o.schedule
                .flatMap((slot) => findSlotConflicts(o, slot, otherEnrolled))
                .map((c) => c.offering)
                .filter(
                  (item, idx, all) =>
                    all.findIndex((other) => other.id === item.id) === idx,
                );
              const blocked = isFull || conflicts.length > 0;
              return (
                <div
                  key={o.id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: 14,
                    flexWrap: "wrap",
                    padding: "13px 15px",
                    border: "1px solid var(--border)",
                    background: blocked ? "var(--soft)" : "var(--panel)",
                    opacity: blocked ? 0.78 : 1,
                  }}
                >
                  <div style={{ flex: 1, minWidth: 240 }}>
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                        flexWrap: "wrap",
                        marginBottom: 4,
                      }}
                    >
                      <b>Lớp {o.section}</b>
                      <span className="pill">
                        Sĩ số {o.enrolledCount}/{o.capacity}
                      </span>
                      {isFull ? (
                        <span
                          style={{
                            fontSize: 11,
                            fontWeight: 700,
                            padding: "2px 7px",
                            background: "#e2e8f0",
                            color: "#475569",
                          }}
                        >
                          Đã đầy
                        </span>
                      ) : conflicts.length > 0 ? (
                        <span
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: 4,
                            fontSize: 11,
                            fontWeight: 700,
                            padding: "2px 7px",
                            background: "#fdecee",
                            color: "#d71920",
                          }}
                        >
                          <AlertTriangle size={12} />
                          Trùng với {conflicts.map((c) => c.code).join(", ")}
                        </span>
                      ) : (
                        <span
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: 4,
                            fontSize: 11,
                            fontWeight: 700,
                            padding: "2px 7px",
                            background: "#ecfdf5",
                            color: "#047857",
                          }}
                        >
                          <CheckCircle2 size={12} />
                          Có thể đổi ngay
                        </span>
                      )}
                    </div>
                    <div
                      style={{
                        fontSize: 12.5,
                        color: "var(--muted)",
                        display: "flex",
                        gap: 10,
                        flexWrap: "wrap",
                      }}
                    >
                      <span>GV: {o.instructor}</span>
                      <span>·</span>
                      <span>Phòng {o.room}</span>
                      {o.schedule.map((s, idx) => (
                        <span key={idx}>
                          · {s.day === 7 ? "CN" : `T${s.day + 1}`}{" "}
                          <b>{getShiftLabel(s.start)}</b> ({s.start}–{s.end})
                        </span>
                      ))}
                    </div>
                  </div>
                  <button
                    type="button"
                    className="primary"
                    disabled={blocked || swappingId !== null}
                    onClick={() => void handleSwap(o)}
                  >
                    {swappingId === o.id ? "Đang đổi lớp…" : "Xác nhận đổi lớp"}
                  </button>
                </div>
              );
            })}
          </div>
        )}

        <div className="actions" style={{ marginTop: 18 }}>
          <button
            type="button"
            className="btn-outline"
            disabled={swappingId !== null}
            onClick={onClose}
          >
            Đóng
          </button>
        </div>
      </section>
    </div>
  );
}
