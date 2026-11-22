import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Lock } from "lucide-react";
import * as api from "../../api";
import type { StudyPlanResponse } from "../../types";

export default function StudyPlanView({
  notify,
}: {
  notify: (s: string) => void;
}) {
  const [plan, setPlan] = useState<StudyPlanResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [removingId, setRemovingId] = useState<number | null>(null);
  const nav = useNavigate();

  const handleRemove = async (planId: number, code: string, name: string) => {
    if (
      !window.confirm(
        `Bạn có chắc muốn xóa học phần ${code} — ${name} khỏi Kế hoạch học tập?`,
      )
    ) {
      return;
    }
    setRemovingId(planId);
    try {
      const updated = await api.removeFromStudyPlan(planId);
      setPlan(updated);
      notify(`Đã xóa ${code} khỏi Kế hoạch học tập.`);
    } catch (e) {
      notify((e as Error).message);
    } finally {
      setRemovingId(null);
    }
  };

  useEffect(() => {
    let active = true;
    setLoading(true);
    void api
      .getMyStudyPlan()
      .then((res) => {
        if (active) setPlan(res);
      })
      .catch((e) => {
        if (active) notify((e as Error).message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <div>
      <div className="page-heading">
        <div>
          <h1>Kế hoạch học tập (ĐKKHHT)</h1>
          <p className="muted">
            Danh sách các học phần bạn đã đăng ký dự kiến cho Học kỳ II,
            2026–2027 (cuối tháng 12/2026 – cuối tháng 05/2027) và kết quả xét
            mở lớp theo nhu cầu sinh viên.
          </p>
        </div>
        {plan && <span className="code-badge">Học kỳ {plan.term}</span>}
      </div>

      {loading ? (
        <div className="skeleton">Đang tải kế hoạch học tập…</div>
      ) : !plan ? (
        <div className="panel empty">
          Không thể tải dữ liệu kế hoạch học tập.
        </div>
      ) : (
        <>
          {!plan.isEditable && (
            <div
              className="panel"
              role="status"
              style={{
                display: "flex",
                alignItems: "center",
                gap: 12,
                padding: "13px 18px",
                marginBottom: 18,
                background: "var(--soft)",
                borderLeft: "4px solid var(--accent)",
              }}
            >
              <Lock
                size={18}
                aria-hidden="true"
                style={{ color: "var(--accent)", flexShrink: 0 }}
              />
              <div style={{ fontSize: 13.5, lineHeight: 1.5 }}>
                <b style={{ color: "var(--accent)" }}>
                  Đợt ĐKKHHT đã kết thúc — Chế độ chỉ xem.
                </b>{" "}
                <span className="muted">{plan.phaseMessage}</span>
              </div>
            </div>
          )}

          <div className="metric-strip" style={{ marginBottom: 20 }}>
            <div className="metric-cell">
              <span className="metric-label">Tổng tín chỉ kế hoạch</span>
              <strong className="metric-value">
                {plan.totalPlannedCredits}
                <span> / {plan.maxCredits} TC</span>
              </strong>
              <small>Học kỳ {plan.term}</small>
            </div>
            <div className="metric-cell">
              <span className="metric-label">Học phần trong KHHT</span>
              <strong className="metric-value">{plan.items.length}</strong>
              <small>môn đã đăng ký dự kiến</small>
            </div>
            <div className="metric-cell">
              <span className="metric-label">Đủ sĩ số mở lớp</span>
              <strong className="metric-value" style={{ color: "#047857" }}>
                {plan.openedCount}
              </strong>
              <small>sẵn sàng chọn lịch học</small>
            </div>
            <div className="metric-cell">
              <span className="metric-label">Không mở lớp</span>
              <strong
                className="metric-value"
                style={{
                  color: plan.notOpenedCount > 0 ? "#d71920" : undefined,
                }}
              >
                {plan.notOpenedCount}
              </strong>
              <small>do chưa đủ số SV ĐKKHHT</small>
            </div>
          </div>

          <section className="panel">
            <div className="section-title">
              <h3>Danh sách học phần kế hoạch kỳ {plan.term}</h3>
              <button
                type="button"
                className="primary"
                onClick={() => nav("/courses")}
              >
                Sang đăng ký môn học
              </button>
            </div>

            {!plan.items.length ? (
              <p className="empty">
                Bạn chưa có học phần nào trong Kế hoạch học tập kỳ {plan.term}.
              </p>
            ) : (
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Mã môn</th>
                      <th>Tên học phần</th>
                      <th>Tín chỉ</th>
                      <th>Nhu cầu ĐKKHHT</th>
                      <th>Trạng thái mở lớp</th>
                      <th>Trạng thái ĐKMH</th>
                      <th style={{ width: 150 }}>Thao tác</th>
                    </tr>
                  </thead>
                  <tbody>
                    {plan.items.map((item) => {
                      const pct = Math.min(
                        100,
                        Math.round(
                          (item.plannedCount / item.minRequired) * 100,
                        ),
                      );
                      const isOpened = item.openingStatus === "OPENED";
                      const isNotOpened = item.openingStatus === "NOT_OPENED";
                      return (
                        <tr key={item.id}>
                          <td>
                            <b className="mono-id">{item.code}</b>
                          </td>
                          <td>
                            <strong>{item.name}</strong>
                            <small
                              className="muted"
                              style={{ display: "block" }}
                            >
                              {item.minAccumulatedCredits === 0
                                ? "Mở năm 1 (0 TC tích lũy)"
                                : `Yêu cầu ≥ ${item.minAccumulatedCredits} TC tích lũy`}
                            </small>
                          </td>
                          <td>
                            <span className="credit">{item.credits}</span>
                          </td>
                          <td>
                            <div style={{ fontSize: 12.5, fontWeight: 600 }}>
                              {item.plannedCount} / {item.minRequired} SV
                            </div>
                            <div className="capacity" style={{ width: 110 }}>
                              <i
                                style={{
                                  width: `${pct}%`,
                                  background: isNotOpened
                                    ? "#d71920"
                                    : "#004b91",
                                }}
                              />
                            </div>
                          </td>
                          <td>
                            {isOpened ? (
                              <div>
                                <span
                                  style={{
                                    display: "inline-block",
                                    fontSize: 11,
                                    fontWeight: 700,
                                    padding: "3px 8px",
                                    background: "#ecfdf5",
                                    color: "#047857",
                                  }}
                                >
                                  Đã mở lớp ({item.offeringsCount} lớp)
                                </span>
                              </div>
                            ) : isNotOpened ? (
                              <div>
                                <span
                                  style={{
                                    display: "inline-block",
                                    fontSize: 11,
                                    fontWeight: 700,
                                    padding: "3px 8px",
                                    background: "#fdecee",
                                    color: "#d71920",
                                  }}
                                >
                                  Không mở lớp
                                </span>
                                <small
                                  className="muted"
                                  style={{
                                    display: "block",
                                    marginTop: 4,
                                    color: "#b91c1c",
                                  }}
                                >
                                  Thiếu sĩ số tối thiểu ({item.plannedCount}/
                                  {item.minRequired} SV)
                                </small>
                              </div>
                            ) : (
                              <span className="pill">Đang tổng hợp</span>
                            )}
                          </td>
                          <td>
                            {item.enrollmentStatus === "ENROLLED" ? (
                              <span
                                style={{
                                  fontSize: 11.5,
                                  fontWeight: 700,
                                  color: "#047857",
                                }}
                              >
                                Đã đăng ký lớp
                              </span>
                            ) : item.enrollmentStatus === "WAITLISTED" ? (
                              <span
                                style={{
                                  fontSize: 11.5,
                                  fontWeight: 700,
                                  color: "#b45309",
                                }}
                              >
                                Đang chờ (Waitlist)
                              </span>
                            ) : (
                              <span className="muted">Chưa chọn lớp</span>
                            )}
                          </td>
                          <td>
                            {plan.isEditable ? (
                              <button
                                type="button"
                                className="btn-danger-soft"
                                style={{ padding: "7px 12px", fontSize: 12 }}
                                disabled={removingId === item.id}
                                onClick={() =>
                                  void handleRemove(
                                    item.id,
                                    item.code,
                                    item.name,
                                  )
                                }
                              >
                                {removingId === item.id
                                  ? "Đang xóa…"
                                  : "Xóa khỏi KHHT"}
                              </button>
                            ) : isOpened ? (
                              <button
                                type="button"
                                className={
                                  item.enrollmentStatus === "WAITLISTED"
                                    ? "btn-outline"
                                    : "primary"
                                }
                                style={{ padding: "7px 12px", fontSize: 12 }}
                                onClick={() =>
                                  nav(
                                    item.enrollmentStatus === "WAITLISTED"
                                      ? "/waitlist"
                                      : `/courses?q=${encodeURIComponent(item.code)}`,
                                  )
                                }
                              >
                                {item.enrollmentStatus === "ENROLLED"
                                  ? "Xem lớp"
                                  : item.enrollmentStatus === "WAITLISTED"
                                    ? "Xem / Hủy chờ"
                                    : "Chọn lớp ngay"}
                              </button>
                            ) : (
                              <span className="muted" style={{ fontSize: 12 }}>
                                Không khả dụng
                              </span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}
