import { Suspense, lazy, memo, useEffect, useRef, useState } from "react";
import {
  NavLink,
  Routes,
  Route,
  Navigate,
  useLocation,
  useNavigate,
  useSearchParams,
} from "react-router-dom";
import {
  AlertTriangle,
  Award,
  BookOpen,
  LayoutDashboard,
  CalendarDays,
  ClipboardList,
  Clock,
  GitBranch,
  LogOut,
  Sun,
  Moon,
  Search,
  Sparkles,
  Download,
  ChevronRight,
  ShieldCheck,
  Menu,
} from "lucide-react";
import { UniFlowLogo } from "./components/UniFlowLogo";
import { PhaseBanner } from "./components/PhaseBanner";
import { SwapSectionModal } from "./components/SwapSectionModal";
import { AutoSchedulerModal } from "./components/AutoSchedulerModal";
import { TuitionPanel } from "./components/TuitionPanel";
import { NotificationBell } from "./components/NotificationBell";
import { downloadTimetableIcs } from "./features/timetable/icsExport";
import * as api from "./api";
import { getSession, setSession } from "./api/http";
import type { Offering, Enrollment, Session } from "./types";
import { findSlotConflicts, parseTime } from "./features/timetable/conflicts";
import {
  detectPromotedWaitlist,
  getCreditStatus,
  type WaitlistSummary,
} from "./features/registration/helpers";

const AdminPanel = lazy(() => import("./features/admin/AdminPanel"));
const PrerequisiteGraphView = lazy(
  () => import("./features/prerequisites/PrerequisiteGraphView"),
);
const AcademicRecordView = lazy(
  () => import("./features/academic/AcademicRecordView"),
);
const StudyPlanView = lazy(() => import("./features/studyplan/StudyPlanView"));
const week = Number(import.meta.env.VITE_WEEK || 5);
export default function App() {
  const [session, updateSession] = useState<Session | null>(getSession());
  const [dark, setDark] = useState(localStorage.getItem("theme") === "dark");
  const [menu, setMenu] = useState(false);
  const [toast, setToast] = useState("");
  const [regs, setRegs] = useState<Enrollment[]>([]);
  const [waitlistItems, setWaitlistItems] = useState<api.WaitlistEntry[]>([]);
  const [tuition, setTuition] = useState<api.TuitionEstimate | null>(null);
  const [notifications, setNotifications] = useState<api.StudentNotification[]>(
    [],
  );
  const prevWaitlistRef = useRef<api.WaitlistEntry[]>([]);
  const [preview, setPreview] = useState<Offering | null>(null);
  const [swapTarget, setSwapTarget] = useState<Enrollment | null>(null);
  const [showAutoScheduler, setShowAutoScheduler] = useState(false);
  const [coursesRefreshTick, setCoursesRefreshTick] = useState(0);
  const [phaseInfo, setPhaseInfo] = useState<api.RegistrationPhaseInfo | null>(
    null,
  );
  const [error, setError] = useState("");
  const location = useLocation();
  const nav = useNavigate();
  const notify = (s: string) => {
    setToast(s);
    window.setTimeout(() => setToast(""), 5000);
  };
  async function load() {
    try {
      const [nextRegs, nextWaitlist, nextTuition, nextNotifRes] =
        await Promise.all([
          api.timetable(),
          api
            .getWaitlist()
            .then((w) => w.items)
            .catch(() => [] as api.WaitlistEntry[]),
          api.getMyTuition().catch(() => null),
          api
            .getMyNotifications()
            .then((n) => n.items)
            .catch(() => [] as api.StudentNotification[]),
        ]);
      // Phát hiện sinh viên vừa được đôn từ danh sách chờ lên lớp chính thức
      const activeOffIds = new Set(nextRegs.map((e) => e.offering.id));
      const nextWlIds = new Set(nextWaitlist.map((w) => w.offeringId));
      const promotedNow = prevWaitlistRef.current.filter(
        (prev) =>
          !nextWlIds.has(prev.offeringId) && activeOffIds.has(prev.offeringId),
      );
      const promoAlerts: api.StudentNotification[] = promotedNow.map((p) => ({
        id: `waitlist-promoted-${p.offeringId}-${p.id}`,
        kind: "WAITLIST_PROMOTED",
        title: `Đã được đôn vào lớp ${p.offering.code} (Lớp ${p.offering.section})`,
        message: `Chúc mừng! Bạn đã được tự động chuyển từ Danh sách chờ sang đăng ký chính thức học phần ${p.offering.name}.`,
        link: "/timetable",
        createdAt: new Date().toISOString(),
      }));
      prevWaitlistRef.current = nextWaitlist;

      setRegs(nextRegs);
      setWaitlistItems(nextWaitlist);
      setTuition(nextTuition);
      setNotifications((cur) => {
        const existingPromos = cur.filter(
          (n) =>
            n.kind === "WAITLIST_PROMOTED" &&
            !promoAlerts.some((p) => p.id === n.id),
        );
        return [...promoAlerts, ...existingPromos, ...nextNotifRes];
      });
      setPreview((cur) =>
        cur && nextRegs.some((e) => e.offering.id === cur.id) ? null : cur,
      );
      setError("");
    } catch (e) {
      setError((e as Error).message);
    }
  }
  useEffect(() => {
    document.documentElement.dataset.theme = dark ? "dark" : "light";
    localStorage.setItem("theme", dark ? "dark" : "light");
  }, [dark]);
  useEffect(() => {
    // Always reset previous user's timetable/preview state on account switch or logout
    setRegs([]);
    setWaitlistItems([]);
    setTuition(null);
    setNotifications([]);
    prevWaitlistRef.current = [];
    setPreview(null);
    setSwapTarget(null);
    setShowAutoScheduler(false);
    setPhaseInfo(null);
    setError("");
    if (session) {
      api
        .getRegistrationPhase()
        .then(setPhaseInfo)
        .catch(() => {
          /* phase banner is non-blocking */
        });
    }
    if (session?.user.role === "student" && week >= 2) void load();
  }, [session]);
  useEffect(() => {
    if (!session) return;
    const syncPhase = () => {
      api
        .getRegistrationPhase()
        .then(setPhaseInfo)
        .catch(() => {
          /* non-blocking */
        });
    };
    const onFocus = () => {
      syncPhase();
      if (session.user.role === "student" && week >= 2) {
        void load();
      }
    };
    syncPhase();
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, [session, location.pathname]);
  useEffect(() => {
    const expire = () => {
      setRegs([]);
      setWaitlistItems([]);
      setPreview(null);
      setPhaseInfo(null);
      setError("");
      updateSession(null);
      notify("Phiên đã hết hạn. Vui lòng đăng nhập lại.");
    };
    const onRateLimited = (event: Event) => {
      const sec = (event as CustomEvent<{ retryAfter?: number }>).detail
        ?.retryAfter;
      notify(
        sec
          ? `Hệ thống đang đông, tự động thử lại sau ${sec} giây…`
          : "Hệ thống đang đông, đang tự động thử lại…",
      );
    };
    window.addEventListener("session-expired", expire);
    window.addEventListener("rate-limited", onRateLimited);
    return () => {
      window.removeEventListener("session-expired", expire);
      window.removeEventListener("rate-limited", onRateLimited);
    };
  }, []);
  if (!session)
    return (
      <div className="login">
        <div className="login-art">
          <div className="login-brand">
            <UniFlowLogo size={38} />
            <span>UniFlow</span>
          </div>
          <div className="login-art-body">
            <h1>Cổng đăng ký học phần</h1>
            <p>
              Hệ thống đăng ký môn học trực tuyến dành cho sinh viên cho Học kỳ
              2026-2 (cuối 12/2026 – cuối 05/2027).
            </p>
            <blockquote className="login-quote">
              <p>
                “Mỗi học kỳ là một chặng đường mới — chủ động chọn đúng lộ trình
                hôm nay để vững vàng bước tới mục tiêu ngày mai.”
              </p>
              <footer>
                Chúc bạn một học kỳ 2026-2 nhiều năng lượng và kết quả rực rỡ.
              </footer>
            </blockquote>
          </div>
          <small>
            Trường Đại học Tôn Đức Thắng — Học kỳ 2026-2 (12/2026 – 05/2027)
          </small>
        </div>
        <div className="login-pane">
          <div className="login-uni-logo">
            <img src="/tdtu-logo.png" alt="Trường Đại học Tôn Đức Thắng" />
          </div>
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              const f = new FormData(e.currentTarget);
              try {
                const s = await api.login(
                  String(f.get("email")),
                  String(f.get("password")),
                );
                setSession(s);
                updateSession(s);
                const nextPath =
                  s.user.role === "admin"
                    ? "/admin/study-plans"
                    : location.pathname === "/login" ||
                        location.pathname.startsWith("/admin")
                      ? "/"
                      : location.pathname;
                nav(nextPath, {
                  replace: true,
                });
              } catch (e) {
                notify((e as Error).message);
              }
            }}
          >
            <h2>Đăng nhập hệ thống</h2>
            <p className="muted">
              Sử dụng tài khoản email do nhà trường cấp để tiếp tục.
            </p>
            <label>
              Email sinh viên hoặc quản trị
              <input
                name="email"
                type="email"
                required
                placeholder="sv0587@uni.edu.vn"
              />
            </label>
            <label>
              Mật khẩu
              <input name="password" type="password" required />
            </label>
            <button className="primary">Đăng nhập</button>
            {toast && <p role="alert">{toast}</p>}
          </form>
        </div>
      </div>
    );
  const credits = regs.reduce((n, e) => n + e.offering.credits, 0);
  const admin =
    session.user.role === "admin" || location.pathname.startsWith("/admin");
  return (
    <div className="shell">
      <aside className={menu ? "open" : ""}>
        <div className="brand">
          <UniFlowLogo size={30} />
          <span>UniFlow</span>
        </div>
        <div className="workspace">
          <div className="avatar">{admin ? "QT" : "SV"}</div>
          <div>
            <b>{session.user.fullName}</b>
            <small>
              {admin
                ? "Quản trị đào tạo"
                : session.user.faculty || "Cổng sinh viên"}
            </small>
          </div>
        </div>
        <div className="nav-label">
          {session.user.role === "admin" ? "Quản trị" : "Học tập"}
        </div>
        <nav>
          {session.user.role === "student" &&
            [
              ["/", "Tổng quan", LayoutDashboard],
              ["/study-plan", "Kế hoạch học tập", ClipboardList],
              ["/courses", "Tra cứu học phần", BookOpen],
              ...(week >= 2
                ? [["/timetable", "Thời khóa biểu", CalendarDays]]
                : []),
              [
                "/waitlist",
                waitlistItems.length > 0
                  ? `Danh sách chờ (${waitlistItems.length})`
                  : "Danh sách chờ",
                Clock,
              ],
              ["/prerequisites", "Sơ đồ tiên quyết", GitBranch],
              ["/academic-record", "Hồ sơ học tập", Award],
            ].map(([path, label, Icon]) => (
              <NavLink
                key={String(path)}
                to={String(path)}
                onClick={() => setMenu(false)}
              >
                <Icon size={19} />
                {String(label)}
              </NavLink>
            ))}
          {session.user.role === "admin" && (
            <>
              <NavLink to="/admin/phases" onClick={() => setMenu(false)}>
                <Clock size={19} /> Điều hành đợt ĐK
              </NavLink>
              <NavLink to="/admin/study-plans" onClick={() => setMenu(false)}>
                <ShieldCheck size={19} /> Nhu cầu mở lớp
              </NavLink>
              <NavLink to="/admin/courses" onClick={() => setMenu(false)}>
                <ShieldCheck size={19} />
                Quản trị học phần
              </NavLink>
              <NavLink to="/admin/prereqs" onClick={() => setMenu(false)}>
                <ShieldCheck size={19} /> Điều kiện tiên quyết
              </NavLink>
              <NavLink to="/prerequisites" onClick={() => setMenu(false)}>
                <GitBranch size={19} /> Sơ đồ tiên quyết
              </NavLink>
              <NavLink to="/courses" onClick={() => setMenu(false)}>
                <BookOpen size={19} /> Danh mục lớp mở
              </NavLink>
            </>
          )}
        </nav>
        <button
          className="logout"
          onClick={async () => {
            try {
              await api.logout(session.refreshToken);
            } finally {
              setRegs([]);
              setWaitlistItems([]);
              setPreview(null);
              setPhaseInfo(null);
              setError("");
              setSession(null);
              updateSession(null);
              nav("/login", { replace: true });
            }
          }}
        >
          <LogOut size={18} />
          Đăng xuất
        </button>
      </aside>
      <section className="main">
        <header>
          <button className="mobile" onClick={() => setMenu(!menu)}>
            <Menu />
          </button>
          <span>
            Không gian {admin ? "quản trị" : "sinh viên"}{" "}
            <ChevronRight size={14} /> <b>Học kỳ II, 2026–2027 (2026-2)</b>
          </span>
          <div className="header-right">
            {!admin && (
              <NotificationBell
                userId={session.user.id}
                notifications={notifications}
              />
            )}
            <button
              aria-label="Đổi giao diện sáng tối"
              onClick={() => setDark(!dark)}
            >
              {dark ? <Sun size={20} /> : <Moon size={20} />}
            </button>
            <div className="avatar">
              {session.user.fullName.split(" ").slice(-1)[0].slice(0, 2)}
            </div>
            <b>{session.user.fullName}</b>
          </div>
        </header>
        <main>
          {!admin && <PhaseBanner phase={phaseInfo} />}
          {!admin &&
            location.pathname !== "/" &&
            (() => {
              const cs = getCreditStatus(credits, session.user.maxCredits);
              return (
                <div className="panel credit-bar" style={{ marginBottom: 24 }}>
                  <div className="section-title">
                    <b>Tiến độ tín chỉ</b>
                    <span>
                      Kỳ này: {credits} / {session.user.maxCredits} TC · Tích
                      lũy: <b>{session.user.accumulatedCredits ?? 0} TC</b>
                    </span>
                  </div>
                  <div className="capacity">
                    <i
                      style={{
                        width: `${cs.percent}%`,
                        background: cs.color,
                      }}
                    />
                  </div>
                  {cs.warningText && (
                    <small className="warning">{cs.warningText}</small>
                  )}
                </div>
              );
            })()}
          <Routes>
            <Route path="/login" element={<Navigate to="/" replace />} />
            <Route
              path="/"
              element={
                session.user.role === "admin" ? (
                  <Navigate to="/admin/study-plans" replace />
                ) : (
                  (() => {
                    const accCredits = session.user.accumulatedCredits ?? 0;
                    const gradTarget = 120;
                    const gradPct = Math.min(
                      100,
                      Math.round((accCredits / gradTarget) * 100),
                    );
                    const studentYear =
                      accCredits < 20
                        ? 1
                        : accCredits < 40
                          ? 2
                          : accCredits < 60
                            ? 3
                            : 4;
                    const weeklySessions = regs.reduce(
                      (n, e) => n + e.offering.schedule.length,
                      0,
                    );
                    const cs = getCreditStatus(
                      credits,
                      session.user.maxCredits,
                    );

                    return (
                      <>
                        <section className="dash-header">
                          <div className="dash-header-main">
                            <div className="dash-meta-row">
                              <span className="term-tag">Học kỳ 2026-2</span>
                              {session.user.role === "student" && (
                                <span>Sinh viên Năm {studentYear}</span>
                              )}
                              {session.user.mssv && (
                                <span className="mono-id">
                                  {session.user.mssv}
                                </span>
                              )}
                            </div>
                            <h1>{session.user.fullName}</h1>
                            <p className="muted">
                              {session.user.faculty ||
                                "Cổng đăng ký học phần Đại học"}
                              . Theo dõi tiến độ tín chỉ, kiểm tra điều kiện
                              tiên quyết và hoàn tất lịch học kỳ này.
                            </p>
                            <div className="dash-actions">
                              <button
                                className="btn-tdtu-red"
                                onClick={() => nav("/courses")}
                              >
                                Đăng ký học phần
                              </button>
                              <button
                                className="btn-outline"
                                onClick={() => nav("/prerequisites")}
                              >
                                Xem sơ đồ tiên quyết
                              </button>
                            </div>
                          </div>

                          <div className="dash-progress-box">
                            <div className="dash-progress-head">
                              <span>Tiến độ tích lũy toàn khóa</span>
                              <strong className="mono-id">{gradPct}%</strong>
                            </div>
                            <div className="dash-progress-track">
                              <i style={{ width: `${gradPct}%` }} />
                            </div>
                            <div className="dash-progress-foot">
                              <span>
                                Đã hoàn thành <b>{accCredits}</b> / {gradTarget}{" "}
                                tín chỉ
                              </span>
                              <button
                                type="button"
                                className="text-button"
                                onClick={() => nav("/academic-record")}
                              >
                                Mở hồ sơ học tập
                              </button>
                            </div>
                          </div>
                        </section>

                        <div className="metric-strip">
                          <button
                            type="button"
                            className="metric-cell"
                            onClick={() => nav("/academic-record")}
                          >
                            <span className="metric-label">
                              Tín chỉ tích lũy
                            </span>
                            <strong className="metric-value">
                              {accCredits}
                            </strong>
                            <small>Mức tiến độ Năm {studentYear}</small>
                          </button>

                          <button
                            type="button"
                            className="metric-cell"
                            onClick={() => nav("/courses")}
                          >
                            <span className="metric-label">
                              Tín chỉ đăng ký kỳ này
                            </span>
                            <strong className="metric-value">
                              {credits}
                              <span> / {session.user.maxCredits}</span>
                            </strong>
                            <div className="capacity" style={{ width: "100%" }}>
                              <i
                                style={{
                                  width: `${cs.percent}%`,
                                  background: cs.color,
                                }}
                              />
                            </div>
                          </button>

                          <button
                            type="button"
                            className="metric-cell"
                            onClick={() => nav("/timetable")}
                          >
                            <span className="metric-label">
                              Lớp học phần đã chọn
                            </span>
                            <strong className="metric-value">
                              {regs.length}
                            </strong>
                            <small>{weeklySessions} ca học / tuần</small>
                          </button>

                          <button
                            type="button"
                            className="metric-cell"
                            onClick={() => nav("/timetable")}
                          >
                            <span className="metric-label">
                              Học phí tạm tính
                            </span>
                            <strong
                              className="metric-value"
                              style={{ fontSize: 21, color: "var(--red)" }}
                            >
                              {api.formatVnd(tuition?.totalAmount ?? 0)}
                            </strong>
                            <small>Bảng kê chi tiết kỳ 2026-2</small>
                          </button>
                        </div>

                        <div className="workbench-grid">
                          <section className="panel">
                            <div className="section-title">
                              <h3>
                                <Clock size={16} /> Phân bổ lịch học trong tuần
                              </h3>
                              <span className="muted">
                                {weeklySessions} buổi, {credits} tín chỉ
                              </span>
                            </div>
                            <div className="chart">
                              {["T2", "T3", "T4", "T5", "T6", "T7", "CN"].map(
                                (d, i) => {
                                  const count = regs.reduce(
                                    (n, e) =>
                                      n +
                                      e.offering.schedule.filter(
                                        (s) => s.day === i + 1,
                                      ).length,
                                    0,
                                  );
                                  return (
                                    <div key={d}>
                                      <small className="chart-val">
                                        {count > 0 ? count : ""}
                                      </small>
                                      <div
                                        style={{
                                          height: Math.max(6, count * 42),
                                          opacity: count > 0 ? 1 : 0.2,
                                        }}
                                      />
                                      <span>{d}</span>
                                    </div>
                                  );
                                },
                              )}
                            </div>
                            {regs.length > 0 ? (
                              <div className="mini-enrolled-list">
                                {regs.slice(0, 4).map((e) => (
                                  <div
                                    className="mini-enrolled-item"
                                    key={e.id}
                                  >
                                    <b className="mono-id">{e.offering.code}</b>
                                    <span>{e.offering.name}</span>
                                    <small>{e.offering.credits} TC</small>
                                  </div>
                                ))}
                                {regs.length > 4 && (
                                  <button
                                    className="text-button"
                                    onClick={() => nav("/timetable")}
                                  >
                                    Xem toàn bộ {regs.length} lớp trong thời
                                    khóa biểu
                                  </button>
                                )}
                              </div>
                            ) : (
                              <div className="dash-empty-cta">
                                <span>
                                  Bạn chưa đăng ký học phần nào trong học kỳ
                                  2026-2.
                                </span>
                                <button
                                  className="text-button"
                                  onClick={() => nav("/courses")}
                                >
                                  Chọn môn đúng tiến độ Năm {studentYear}
                                </button>
                              </div>
                            )}
                          </section>

                          <section className="panel">
                            <div className="section-title">
                              <h3>Lối tắt học vụ</h3>
                            </div>
                            <div className="task-list">
                              {[
                                {
                                  title: "Tra cứu và đăng ký học phần",
                                  desc: `Ưu tiên các môn đúng tiến độ Năm ${studentYear} và đủ điều kiện`,
                                  to: "/courses",
                                  icon: BookOpen,
                                },
                                {
                                  title: "Xem sơ đồ tiên quyết",
                                  desc: "Theo dõi môn bắt buộc (AND), môn thay thế (OR) và nhánh mở khóa",
                                  to: "/prerequisites",
                                  icon: GitBranch,
                                },
                                {
                                  title: "Mở thời khóa biểu tuần",
                                  desc: "Kiểm tra phân bổ ca học và phát hiện trùng giờ trước khi đăng ký",
                                  to: "/timetable",
                                  icon: CalendarDays,
                                },
                                {
                                  title: "Xem hồ sơ học tập",
                                  desc: `Tra cứu GPA và danh sách ${accCredits} tín chỉ đã hoàn thành`,
                                  to: "/academic-record",
                                  icon: Award,
                                },
                              ].map((item) => {
                                const Icon = item.icon;
                                return (
                                  <button
                                    key={item.to}
                                    type="button"
                                    className="task-row"
                                    onClick={() => nav(item.to)}
                                  >
                                    <Icon size={18} className="task-row-icon" />
                                    <div className="task-row-body">
                                      <b>{item.title}</b>
                                      <small>{item.desc}</small>
                                    </div>
                                    <ChevronRight
                                      size={16}
                                      className="quick-arrow"
                                    />
                                  </button>
                                );
                              })}
                            </div>
                          </section>
                        </div>
                      </>
                    );
                  })()
                )
              }
            />
            <Route
              path="/courses"
              element={
                <Courses
                  week={week}
                  regs={regs}
                  waitlistItems={waitlistItems}
                  regsCredits={credits}
                  maxCredits={session.user.maxCredits}
                  canEnroll={phaseInfo?.canEnroll ?? true}
                  isAdmin={session.user.role === "admin"}
                  refreshTick={coursesRefreshTick}
                  onSwap={(enr) => setSwapTarget(enr)}
                  onOpenAutoScheduler={() => setShowAutoScheduler(true)}
                  notify={notify}
                  changed={load}
                />
              }
            />
            <Route
              path="/timetable"
              element={
                week >= 2 ? (
                  <>
                    <div className="page-heading">
                      <div>
                        <h1>Thời khóa biểu tuần</h1>
                        <p className="muted">
                          Theo dõi lịch học khung giờ 07:00 – 21:00, xem trước
                          lớp dự kiến và kiểm tra trùng giờ.
                        </p>
                      </div>
                      <div
                        className="actions"
                        style={{ alignItems: "center", flexWrap: "wrap" }}
                      >
                        <select
                          aria-label="Học kỳ"
                          style={{ width: "auto", marginTop: 0 }}
                        >
                          <option>Học kỳ 2026-2</option>
                        </select>
                        <button
                          type="button"
                          className="btn-outline"
                          disabled={!regs.length}
                          title={
                            !regs.length
                              ? "Bạn chưa đăng ký lớp học phần nào để xuất lịch"
                              : "Tải file .ics nhập vào Google Calendar / Apple Calendar"
                          }
                          onClick={() => {
                            downloadTimetableIcs(regs, "2026-2");
                            notify(
                              "Đã tải file UniFlow-TKB-2026-2.ics — có thể nhập thẳng vào Google Calendar / Apple Calendar.",
                            );
                          }}
                        >
                          <Download size={14} /> Xuất lịch (.ics)
                        </button>
                        <button
                          type="button"
                          className="btn-outline"
                          onClick={() => window.print()}
                        >
                          In thời khóa biểu
                        </button>
                        <button
                          type="button"
                          className="btn-tdtu-red"
                          onClick={() => setShowAutoScheduler(true)}
                        >
                          <Sparkles size={15} /> Gợi ý xếp lịch tự động
                        </button>
                        <button
                          type="button"
                          className="primary"
                          onClick={() => nav("/courses")}
                        >
                          Thêm học phần
                        </button>
                      </div>
                    </div>
                    {error && (
                      <div className="notice">
                        {error}
                        <button onClick={load}>Thử lại</button>
                      </div>
                    )}
                    {preview && (
                      <div className="tt-preview-banner">
                        <div>
                          <span className="tt-preview-tag">ĐANG XEM TRƯỚC</span>
                          <b>
                            {preview.code} — {preview.name}
                          </b>
                          <small>
                            Lớp {preview.section} · {preview.credits} TC ·{" "}
                            {preview.instructor}
                          </small>
                        </div>
                        <button
                          type="button"
                          className="btn-outline"
                          onClick={() => setPreview(null)}
                        >
                          Bỏ xem trước
                        </button>
                      </div>
                    )}
                    <Timetable regs={regs} preview={preview} />
                    <section className="panel">
                      <div className="section-title">
                        <h3>
                          Lớp đang đăng ký ({regs.length} lớp · {credits} tín
                          chỉ)
                        </h3>
                        {preview && (
                          <button onClick={() => setPreview(null)}>
                            Bỏ xem trước
                          </button>
                        )}
                      </div>
                      {!regs.length ? (
                        <div className="dash-empty-cta">
                          <span>
                            Bạn chưa đăng ký lớp học phần nào trong học kỳ
                            2026-2 (cuối 12/2026 – cuối 05/2027).
                          </span>
                          <button
                            className="text-button"
                            onClick={() => nav("/courses")}
                          >
                            Tra cứu & đăng ký học phần →
                          </button>
                        </div>
                      ) : (
                        <div className="tt-enrolled-list">
                          {regs.map((e) => {
                            const palette =
                              TIMETABLE_PALETTES[
                                e.offering.courseId % TIMETABLE_PALETTES.length
                              ];
                            return (
                              <div className="tt-enrolled-card" key={e.id}>
                                <span
                                  className="tt-color-dot"
                                  style={{ background: palette.accent }}
                                />
                                <div className="tt-enrolled-main">
                                  <div className="tt-enrolled-top">
                                    <b>{e.offering.code}</b>
                                    <span className="pill">
                                      Lớp {e.offering.section}
                                    </span>
                                    <span className="pill">
                                      {e.offering.credits} TC
                                    </span>
                                  </div>
                                  <div className="tt-enrolled-name">
                                    {e.offering.name}
                                  </div>
                                  <div className="tt-enrolled-meta">
                                    <span>GV: {e.offering.instructor}</span>
                                    <span>·</span>
                                    <span>Phòng {e.offering.room}</span>
                                    {e.offering.schedule.map((s, idx) => (
                                      <span key={idx} className="tt-slot-chip">
                                        {s.day === 7 ? "CN" : `T${s.day + 1}`} ·{" "}
                                        {s.start}–{s.end}
                                      </span>
                                    ))}
                                  </div>
                                </div>
                                <div
                                  className="actions"
                                  style={{ marginTop: 0, flexShrink: 0 }}
                                >
                                  <button
                                    type="button"
                                    className="btn-outline"
                                    disabled={
                                      phaseInfo !== null && !phaseInfo.canEnroll
                                    }
                                    title={
                                      phaseInfo !== null && !phaseInfo.canEnroll
                                        ? `Cổng ĐKMH đang đóng (${phaseInfo.phaseLabel})`
                                        : "Đổi sang lớp học phần khác cùng môn"
                                    }
                                    onClick={() => setSwapTarget(e)}
                                  >
                                    Đổi lớp
                                  </button>
                                  <button
                                    type="button"
                                    className="btn-danger-soft"
                                    disabled={
                                      phaseInfo !== null && !phaseInfo.canEnroll
                                    }
                                    title={
                                      phaseInfo !== null && !phaseInfo.canEnroll
                                        ? `Cổng ĐKMH đang đóng (${phaseInfo.phaseLabel})`
                                        : undefined
                                    }
                                    onClick={async () => {
                                      if (
                                        !window.confirm(
                                          `Bạn có chắc muốn hủy đăng ký môn ${e.offering.code} - ${e.offering.name}?`,
                                        )
                                      )
                                        return;
                                      try {
                                        await api.cancel(e.id);
                                        await load();
                                        notify(
                                          `Đã hủy đăng ký môn ${e.offering.name}`,
                                        );
                                      } catch (err: unknown) {
                                        const msg =
                                          err instanceof Error
                                            ? err.message
                                            : "Không thể hủy môn";
                                        notify(msg);
                                      }
                                    }}
                                  >
                                    Hủy đăng ký
                                  </button>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </section>
                    {waitlistItems.length > 0 && (
                      <section className="panel" style={{ marginTop: 18 }}>
                        <div className="section-title">
                          <h3>
                            Lớp đang trong danh sách chờ ({waitlistItems.length}{" "}
                            lớp)
                          </h3>
                          <button
                            type="button"
                            className="text-button"
                            onClick={() => nav("/waitlist")}
                          >
                            Mở trang Danh sách chờ →
                          </button>
                        </div>
                        <div className="tt-enrolled-list">
                          {waitlistItems.map((w) => (
                            <div className="tt-enrolled-card" key={w.id}>
                              <span
                                className="tt-color-dot"
                                style={{ background: "#d97706" }}
                              />
                              <div className="tt-enrolled-main">
                                <div className="tt-enrolled-top">
                                  <b>{w.offering.code}</b>
                                  <span className="pill">
                                    Lớp {w.offering.section}
                                  </span>
                                  <span
                                    className="pill"
                                    style={{
                                      background: "#fef3c7",
                                      color: "#92400e",
                                    }}
                                  >
                                    Chờ vị trí #{w.position}
                                  </span>
                                </div>
                                <div className="tt-enrolled-name">
                                  {w.offering.name}
                                </div>
                                <div className="tt-enrolled-meta">
                                  <span>GV: {w.offering.instructor}</span>
                                  <span>·</span>
                                  <span>Phòng {w.offering.room}</span>
                                  {w.offering.schedule.map((s, idx) => (
                                    <span key={idx} className="tt-slot-chip">
                                      {s.day === 7 ? "CN" : `T${s.day + 1}`} ·{" "}
                                      {s.start}–{s.end}
                                    </span>
                                  ))}
                                </div>
                              </div>
                              <button
                                type="button"
                                className="btn-danger-soft"
                                disabled={
                                  phaseInfo !== null && !phaseInfo.canEnroll
                                }
                                onClick={async () => {
                                  if (
                                    !window.confirm(
                                      `Bạn có chắc muốn hủy danh sách chờ môn ${w.offering.code} — ${w.offering.name} (Lớp ${w.offering.section})?`,
                                    )
                                  )
                                    return;
                                  try {
                                    await api.leaveWaitlist(w.id);
                                    await load();
                                    notify(
                                      `Đã hủy danh sách chờ môn ${w.offering.name}`,
                                    );
                                  } catch (err: unknown) {
                                    notify(
                                      err instanceof Error
                                        ? err.message
                                        : "Không thể hủy danh sách chờ",
                                    );
                                  }
                                }}
                              >
                                Hủy danh sách chờ
                              </button>
                            </div>
                          ))}
                        </div>
                      </section>
                    )}
                    <TuitionPanel tuition={tuition} id="tuition" />
                  </>
                ) : (
                  <Navigate to="/courses" />
                )
              }
            />
            <Route
              path="/waitlist"
              element={
                <Waitlist
                  canEnroll={phaseInfo?.canEnroll ?? true}
                  notify={notify}
                  changed={load}
                />
              }
            />
            <Route
              path="/prerequisites"
              element={
                <Suspense
                  fallback={
                    <div className="skeleton">Đang tải sơ đồ tiên quyết…</div>
                  }
                >
                  <PrerequisiteGraphView notify={notify} />
                </Suspense>
              }
            />
            <Route
              path="/study-plan"
              element={
                <Suspense
                  fallback={
                    <div className="skeleton">Đang tải kế hoạch học tập…</div>
                  }
                >
                  <StudyPlanView notify={notify} />
                </Suspense>
              }
            />
            <Route
              path="/academic-record"
              element={
                <Suspense
                  fallback={
                    <div className="skeleton">Đang tải hồ sơ học tập…</div>
                  }
                >
                  <AcademicRecordView notify={notify} />
                </Suspense>
              }
            />
            <Route
              path="/admin/*"
              element={
                session.user.role === "admin" ? (
                  <Suspense
                    fallback={
                      <div className="skeleton">
                        Đang tải không gian quản trị…
                      </div>
                    }
                  >
                    <AdminPanel notify={notify} onPhaseUpdated={setPhaseInfo} />
                  </Suspense>
                ) : (
                  <Navigate to="/" replace />
                )
              }
            />
            <Route
              path="*"
              element={
                <div className="panel">
                  <h1>404 · Không tìm thấy trang</h1>
                  <NavLink to="/">Về tổng quan</NavLink>
                </div>
              }
            />
          </Routes>
        </main>
        <footer>
          UniFlow · Cổng đăng ký học phần{" "}
          <span>Thiết kế cho hành trình học tập của bạn.</span>
        </footer>
      </section>
      {swapTarget && (
        <SwapSectionModal
          current={swapTarget}
          regs={regs}
          onClose={() => setSwapTarget(null)}
          onSwapped={async () => {
            await load();
            setCoursesRefreshTick((n) => n + 1);
          }}
          notify={notify}
        />
      )}
      {showAutoScheduler && session.user.role === "student" && (
        <AutoSchedulerModal
          regs={regs}
          canEnroll={phaseInfo?.canEnroll ?? true}
          onClose={() => setShowAutoScheduler(false)}
          onEnrolled={async () => {
            await load();
            setCoursesRefreshTick((n) => n + 1);
          }}
          notify={notify}
        />
      )}
      {toast && (
        <div className="toast" role="status" aria-live="polite">
          {toast}
          <button aria-label="Đóng thông báo" onClick={() => setToast("")}>
            ×
          </button>
        </div>
      )}
    </div>
  );
}
function Courses({
  week,
  regs,
  waitlistItems,
  regsCredits,
  maxCredits,
  canEnroll,
  isAdmin,
  refreshTick,
  onSwap,
  onOpenAutoScheduler,
  notify,
  changed,
}: {
  week: number;
  regs: Enrollment[];
  waitlistItems: api.WaitlistEntry[];
  regsCredits: number;
  maxCredits: number;
  canEnroll: boolean;
  isAdmin: boolean;
  refreshTick: number;
  onSwap: (enr: Enrollment) => void;
  onOpenAutoScheduler: () => void;
  notify: (s: string) => void;
  changed: () => Promise<void>;
}) {
  const [params, setParams] = useSearchParams();
  const [items, setItems] = useState<Offering[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  const [previewOffering, setPreviewOffering] = useState<Offering | null>(null);
  const [selected, setSelected] = useState<Offering | null>(null);
  const [busy, setBusy] = useState(false);
  const [adminBusyId, setAdminBusyId] = useState<number | null>(null);
  const [waitlistBusyId, setWaitlistBusyId] = useState<number | null>(null);
  const [reason, setReason] = useState("");
  const [quickFilters, setQuickFilters] = useState({
    onlyStudyPlan: false,
    hideConflicts: false,
    onlyAvailable: false,
    onlyEligible: false,
  });
  const enrolledByOfferingId = new Map(regs.map((e) => [e.offering.id, e]));
  const enrolledOfferingsList = regs.map((e) => e.offering);
  const waitlistByOfferingId = new Map(
    waitlistItems.map((w) => [w.offeringId, w]),
  );
  const hasQuickFilter =
    quickFilters.onlyStudyPlan ||
    quickFilters.hideConflicts ||
    quickFilters.onlyAvailable ||
    quickFilters.onlyEligible;
  const visibleItems = items.filter((o) => {
    if (quickFilters.onlyStudyPlan && !o.inStudyPlan) return false;
    if (quickFilters.onlyAvailable && o.enrolledCount >= o.capacity)
      return false;
    if (
      quickFilters.onlyEligible &&
      o.eligibilityStatus !== "RECOMMENDED" &&
      o.eligibilityStatus !== "ELIGIBLE"
    )
      return false;
    if (quickFilters.hideConflicts && !enrolledByOfferingId.has(o.id)) {
      const hasConflict = o.schedule.some(
        (slot) => findSlotConflicts(o, slot, enrolledOfferingsList).length > 0,
      );
      if (hasConflict) return false;
    }
    return true;
  });

  async function handleLeaveWaitlist(entry: api.WaitlistEntry) {
    if (waitlistBusyId !== null) return;
    if (
      !window.confirm(
        `Bạn có chắc muốn hủy danh sách chờ môn ${entry.offering.code} — ${entry.offering.name} (Lớp ${entry.offering.section})?`,
      )
    ) {
      return;
    }
    setWaitlistBusyId(entry.id);
    try {
      await api.leaveWaitlist(entry.id);
      await changed();
      notify(`Đã hủy danh sách chờ môn ${entry.offering.name}`);
    } catch (e) {
      notify((e as Error).message);
    } finally {
      setWaitlistBusyId(null);
    }
  }

  async function handleAdminFill(o: Offering) {
    if (adminBusyId !== null) return;
    if (
      !window.confirm(
        `Làm đầy sĩ số lớp ${o.code} - Lớp ${o.section} lên ${o.capacity}/${o.capacity} để kiểm thử hàng chờ (Waitlist)?`,
      )
    ) {
      return;
    }
    setAdminBusyId(o.id);
    try {
      const res = await api.fillAdminOffering(o.id);
      notify(res.message);
      setRetry((n) => n + 1);
    } catch (e) {
      notify((e as Error).message);
    } finally {
      setAdminBusyId(null);
    }
  }

  async function handleAdminRelease(o: Offering) {
    if (adminBusyId !== null) return;
    setAdminBusyId(o.id);
    try {
      const res = await api.releaseAdminOfferingSeat(o.id);
      notify(res.message);
      setRetry((n) => n + 1);
    } catch (e) {
      notify((e as Error).message);
    } finally {
      setAdminBusyId(null);
    }
  }
  useEffect(() => {
    if (!previewOffering) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setPreviewOffering(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [previewOffering]);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    const timer = setTimeout(() => {
      api
        .courses(params.toString(), controller.signal)
        .then((d) => {
          setItems(d.items);
          setTotal(d.total);
          setError("");
        })
        .catch((e) => {
          if (e.name !== "AbortError") setError(e.message);
        })
        .finally(() => {
          if (!controller.signal.aborted) setLoading(false);
        });
    }, 300);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [params, retry, refreshTick]);
  function filter(k: string, v: string) {
    const p = new URLSearchParams(params);
    if (v) p.set(k, v);
    else p.delete(k);
    p.delete("page");
    setParams(p, { replace: true });
  }
  async function register() {
    if (!selected || busy) return;
    setBusy(true);
    setReason("");
    try {
      const check = await api.check(selected.courseId);
      if (check.eligible) {
        if (regsCredits + selected.credits > maxCredits) {
          setReason(
            `Cảnh báo: đăng ký lớp này sẽ vượt hạn mức ${maxCredits} tín chỉ. Hệ thống vẫn gửi yêu cầu để máy chủ quyết định.`,
          );
        }
        try {
          const key = `web-${selected.id}-${Date.now()}`;
          const res = await api.enroll(selected.id, key);
          if (res.status === "WAITLISTED") {
            setReason(
              `Lớp học phần đã hết chỗ (${selected.enrolledCount}/${selected.capacity}). Bạn đã được ghi danh vào Danh sách chờ (Waitlist) ở vị trí thứ ${res.position || 1}.`,
            );
            notify(`Đã đưa vào danh sách chờ môn ${selected.name}`);
            await changed();
          } else {
            setReason(
              "🎉 Đăng ký học phần thành công! Môn học đã được ghi nhận vào thời khóa biểu.",
            );
            notify(`Đăng ký thành công môn ${selected.name}`);
            await changed();
            setRetry((n) => n + 1);
          }
        } catch (enrollErr: unknown) {
          const msg =
            enrollErr instanceof Error
              ? enrollErr.message
              : "Lỗi khi gửi yêu cầu đăng ký.";
          setReason(msg);
        }
        return;
      }

      const explanation = await api.explain(selected.courseId);
      const lines: string[] = [];
      for (const missing of explanation.missing) {
        const relation =
          missing.kind === "TRANSITIVE" ? "gián tiếp" : "trực tiếp";
        lines.push(
          `Còn thiếu ${missing.courseCode} — ${missing.courseName} (điều kiện ${relation}, được yêu cầu bởi ${missing.requiredBy}).`,
        );
        if (missing.path.length > 1) {
          lines.push(`Lộ trình: ${missing.path.join(" → ")}.`);
        }
      }
      for (const group of explanation.unmetOrGroups) {
        const options = group.options
          .map(
            (option) =>
              `${option.courseCode}${option.canTakeNow ? " (có thể học ngay)" : " (còn thiếu: " + option.missingCourses.join(", ") + ")"}`,
          )
          .join(" hoặc ");
        lines.push(
          `Nhóm lựa chọn ${group.groupNo}: cần hoàn thành ít nhất một môn — ${options}.`,
        );
      }
      if (explanation.suggestedOrder.length) {
        lines.push(
          `Thứ tự học gợi ý: ${explanation.suggestedOrder.join(" → ")}.`,
        );
      }
      if (explanation.truncated) {
        lines.push(
          "Danh sách giải thích đã được rút gọn theo giới hạn của máy chủ.",
        );
      }
      setReason(
        lines.length
          ? lines.join("\n")
          : "Bạn chưa đáp ứng điều kiện tiên quyết. Vui lòng liên hệ cố vấn học tập.",
      );
    } catch (error) {
      const code =
        error && typeof error === "object" && "code" in error
          ? String((error as { code: unknown }).code)
          : "";
      setReason(
        code === "NOT_FOUND"
          ? "Không tìm thấy học phần này trong học kỳ hiện tại."
          : `Không thể kiểm tra điều kiện tiên quyết: ${(error as Error).message}`,
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className="page-heading">
        <div>
          <h1>
            {isAdmin ? "Danh mục lớp mở (Quản trị sĩ số)" : "Tra cứu học phần"}
          </h1>
          <p className="muted">
            {isAdmin
              ? "Tìm kiếm lớp học phần để làm đầy sĩ số hoặc giải phóng 1 chỗ nhằm kiểm thử kịch bản đầy lớp và hàng chờ (Waitlist)."
              : "Danh sách tự động ưu tiên các môn đúng tiến độ và đủ điều kiện đăng ký của bạn."}
          </p>
        </div>
        <div className="actions" style={{ marginTop: 0, alignItems: "center" }}>
          {!isAdmin && (
            <button
              type="button"
              className="btn-tdtu-red"
              onClick={onOpenAutoScheduler}
            >
              <Sparkles size={15} /> Gợi ý xếp lịch tự động
            </button>
          )}
          <span className="pill">Học kỳ 2026-2</span>
        </div>
      </div>
      <section className="panel filters">
        <div className="section-title">
          <h3>
            <Search size={18} /> Bộ lọc học phần
          </h3>
          <button
            className="text-button"
            onClick={() => {
              setParams({});
              setQuickFilters({
                onlyStudyPlan: false,
                hideConflicts: false,
                onlyAvailable: false,
                onlyEligible: false,
              });
            }}
          >
            Xóa bộ lọc
          </button>
        </div>
        <div className="filter-grid">
          {[
            ["q", "Từ khóa", "Tên hoặc mã học phần"],
            ["section", "Mã lớp", "Ví dụ: 01"],
            ["credits", "Tín chỉ", "Tất cả tín chỉ"],
            ["instructor", "Giảng viên", "Tên giảng viên"],
          ].map(([key, label, hint]) => (
            <label key={key}>
              {label}
              <input
                type={key === "credits" ? "number" : "text"}
                min="1"
                max="10"
                placeholder={hint}
                value={params.get(key) || ""}
                onChange={(e) => filter(key, e.target.value)}
              />
            </label>
          ))}
          <label>
            Ngày học
            <select
              value={params.get("day") || ""}
              onChange={(e) => filter("day", e.target.value)}
            >
              <option value="">Tất cả các ngày</option>
              {Array.from({ length: 7 }, (_, i) => (
                <option value={i + 1} key={i}>
                  {i === 6 ? "Chủ nhật" : "Thứ " + (i + 2)}
                </option>
              ))}
            </select>
          </label>
        </div>
        {!isAdmin && (
          <div className="quick-filters" aria-label="Bộ lọc nhanh">
            <span className="quick-filters-label">Lọc nhanh:</span>
            {[
              ["onlyStudyPlan", "Chỉ môn trong KHHT"],
              ["hideConflicts", "Ẩn lớp trùng lịch hiện tại"],
              ["onlyAvailable", "Chỉ lớp còn chỗ"],
              ["onlyEligible", "Đủ điều kiện"],
            ].map(([key, label]) => {
              const active = quickFilters[key as keyof typeof quickFilters];
              return (
                <button
                  key={key}
                  type="button"
                  className={`filter-chip ${active ? "is-active" : ""}`}
                  aria-pressed={active}
                  onClick={() =>
                    setQuickFilters((cur) => ({
                      ...cur,
                      [key]: !cur[key as keyof typeof cur],
                    }))
                  }
                >
                  {label}
                </button>
              );
            })}
          </div>
        )}
      </section>
      <section className="panel results">
        <div className="section-title">
          <h3>
            Danh sách học phần{" "}
            <span className="count">
              {hasQuickFilter
                ? `${visibleItems.length}/${items.length}`
                : total}
            </span>
          </h3>
          <span className="muted">
            {hasQuickFilter
              ? `Đang lọc nhanh trên trang (${visibleItems.length} lớp khớp)`
              : "20 kết quả / trang"}
          </span>
        </div>
        {loading ? (
          <div className="skeleton">Đang tải học phần…</div>
        ) : error ? (
          <div className="notice" role="alert">
            {error}
            <button onClick={() => setRetry((n) => n + 1)}>Thử lại</button>
          </div>
        ) : !visibleItems.length ? (
          <div className="empty">
            <div>Không tìm thấy học phần phù hợp với bộ lọc hiện tại.</div>
            {hasQuickFilter && (
              <button
                type="button"
                className="btn-outline"
                style={{ marginTop: 10 }}
                onClick={() =>
                  setQuickFilters({
                    onlyStudyPlan: false,
                    hideConflicts: false,
                    onlyAvailable: false,
                    onlyEligible: false,
                  })
                }
              >
                Bỏ bộ lọc nhanh
              </button>
            )}
          </div>
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  {[
                    "Học phần",
                    "Tín chỉ",
                    "Lớp / Giảng viên",
                    "Lịch học",
                    "Sĩ số",
                    "Thao tác",
                  ].map((s) => (
                    <th key={s}>{s}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {visibleItems.map((o) => {
                  const enrolledEntry = enrolledByOfferingId.get(o.id);
                  const isEnrolled = Boolean(enrolledEntry);
                  const waitlistEntry = waitlistByOfferingId.get(o.id);
                  return (
                    <tr
                      key={o.id}
                      className={isEnrolled ? "row-enrolled" : undefined}
                    >
                      <td>
                        <div
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: 6,
                            flexWrap: "wrap",
                            marginBottom: 4,
                          }}
                        >
                          <b
                            className="course-code"
                            style={{ marginBottom: 0 }}
                          >
                            {o.code}
                          </b>
                          {isEnrolled && (
                            <span className="enrolled-badge">Đã đăng ký</span>
                          )}
                          {!isEnrolled && waitlistEntry && (
                            <span
                              style={{
                                fontSize: 10,
                                fontWeight: 700,
                                padding: "2px 6px",
                                background: "#fef3c7",
                                color: "#92400e",
                              }}
                            >
                              Đang chờ (#{waitlistEntry.position})
                            </span>
                          )}
                          {o.inStudyPlan && (
                            <span
                              style={{
                                fontSize: 10,
                                fontWeight: 700,
                                padding: "2px 6px",
                                background: isEnrolled ? "#64748b" : "#004b91",
                                color: "#ffffff",
                              }}
                            >
                              Trong KHHT
                            </span>
                          )}
                          {o.eligibilityStatus === "RECOMMENDED" && (
                            <span
                              style={{
                                fontSize: 10,
                                fontWeight: 700,
                                padding: "2px 6px",
                                borderRadius: 999,
                                background: isEnrolled ? "#e2e8f0" : "#e8f1fb",
                                color: isEnrolled ? "#475569" : "#00529c",
                              }}
                            >
                              Đúng tiến độ
                            </span>
                          )}
                          {o.eligibilityStatus === "ELIGIBLE" && (
                            <span
                              style={{
                                fontSize: 10,
                                fontWeight: 700,
                                padding: "2px 6px",
                                borderRadius: 999,
                                background: isEnrolled ? "#e2e8f0" : "#ecfdf5",
                                color: isEnrolled ? "#475569" : "#047857",
                              }}
                            >
                              Đủ điều kiện
                            </span>
                          )}
                          {o.eligibilityStatus === "LOCKED" && (
                            <span
                              style={{
                                fontSize: 10,
                                fontWeight: 700,
                                padding: "2px 6px",
                                borderRadius: 999,
                                background: "#fdecee",
                                color: "#d71920",
                              }}
                            >
                              Chưa đủ ĐK
                            </span>
                          )}
                          {o.eligibilityStatus === "COMPLETED" && (
                            <span
                              style={{
                                fontSize: 10,
                                fontWeight: 700,
                                padding: "2px 6px",
                                borderRadius: 999,
                                background: "#f1f5f9",
                                color: "#475569",
                              }}
                            >
                              Đã hoàn thành
                            </span>
                          )}
                        </div>
                        <strong>{o.name}</strong>
                        <small className="muted" style={{ display: "block" }}>
                          {(o.minAccumulatedCredits ?? 0) === 0
                            ? "Mở năm 1 (0 TC tích lũy)"
                            : `Yêu cầu ≥ ${o.minAccumulatedCredits} TC tích lũy`}
                        </small>
                      </td>
                      <td>
                        <span className="credit">{o.credits}</span>
                      </td>
                      <td>
                        <b>Lớp {o.section}</b>
                        <small>{o.instructor}</small>
                      </td>
                      <td>
                        {o.schedule.map((s, i) => (
                          <small key={i}>
                            {s.day === 7 ? "CN" : "T" + (s.day + 1)} ·{" "}
                            <b>{getTdtuShiftLabel(s.start)}</b> ({s.start}–
                            {s.end})
                          </small>
                        ))}
                        <small className="muted">Phòng {o.room}</small>
                      </td>
                      <td>
                        <b>
                          {o.enrolledCount}
                          <span className="muted"> / {o.capacity}</span>
                        </b>
                        <div className="capacity">
                          <i
                            style={{
                              width: (100 * o.enrolledCount) / o.capacity + "%",
                            }}
                          />
                        </div>
                        {o.enrolledCount >= o.capacity - 3 && (
                          <small className="warning">
                            {o.enrolledCount === o.capacity
                              ? "Đã đầy"
                              : "Sắp đầy"}
                          </small>
                        )}
                      </td>
                      <td>
                        <div className="actions">
                          {isAdmin ? (
                            <>
                              <button
                                type="button"
                                className="btn-tdtu-red"
                                disabled={
                                  adminBusyId !== null ||
                                  o.enrolledCount >= o.capacity
                                }
                                onClick={() => void handleAdminFill(o)}
                              >
                                {adminBusyId === o.id
                                  ? "Đang xử lý…"
                                  : o.enrolledCount >= o.capacity
                                    ? "Đã đầy"
                                    : "Làm đầy sĩ số"}
                              </button>
                              <button
                                type="button"
                                className="btn-outline"
                                disabled={
                                  adminBusyId !== null || o.enrolledCount <= 0
                                }
                                title="Hủy 1 sinh viên nền để nhả 1 chỗ và tự động đôn sinh viên đầu hàng chờ (Waitlist)"
                                onClick={() => void handleAdminRelease(o)}
                              >
                                Giải phóng 1 chỗ
                              </button>
                            </>
                          ) : isEnrolled && enrolledEntry ? (
                            <>
                              <button
                                type="button"
                                className="btn-outline"
                                disabled={!canEnroll}
                                title={
                                  !canEnroll
                                    ? "Cổng đăng ký học phần hiện đang đóng"
                                    : "Đổi sang lớp khác cùng học phần"
                                }
                                onClick={() => onSwap(enrolledEntry)}
                              >
                                Đổi lớp
                              </button>
                              <button
                                type="button"
                                className="btn-enrolled-disabled"
                                disabled
                              >
                                Đã đăng ký
                              </button>
                            </>
                          ) : waitlistEntry ? (
                            <button
                              type="button"
                              className="btn-danger-soft"
                              disabled={
                                !canEnroll ||
                                waitlistBusyId === waitlistEntry.id
                              }
                              title={
                                !canEnroll
                                  ? "Cổng đăng ký học phần hiện đang đóng"
                                  : undefined
                              }
                              onClick={() =>
                                void handleLeaveWaitlist(waitlistEntry)
                              }
                            >
                              {waitlistBusyId === waitlistEntry.id
                                ? "Đang hủy…"
                                : "Hủy danh sách chờ"}
                            </button>
                          ) : (
                            <>
                              {week >= 2 && (
                                <button
                                  type="button"
                                  className="btn-outline"
                                  onClick={() => setPreviewOffering(o)}
                                >
                                  Xem trước
                                </button>
                              )}
                              {week >= 3 && (
                                <button
                                  className="primary"
                                  disabled={!canEnroll}
                                  title={
                                    !canEnroll
                                      ? "Cổng đăng ký học phần hiện đang đóng"
                                      : undefined
                                  }
                                  onClick={() => {
                                    setSelected(o);
                                    setReason("");
                                  }}
                                >
                                  {!canEnroll
                                    ? "Cổng ĐKMH đóng"
                                    : o.enrolledCount >= o.capacity
                                      ? "Vào danh sách chờ"
                                      : "Đăng ký học phần"}
                                </button>
                              )}
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        <div className="pagination">
          <span className="muted">Tổng {total} lớp học phần</span>
          <button
            disabled={Number(params.get("page") || 1) <= 1}
            onClick={() => {
              const p = new URLSearchParams(params);
              p.set("page", String(Number(p.get("page") || 1) - 1));
              setParams(p);
            }}
          >
            ← Trước
          </button>
          <b>{params.get("page") || 1}</b>
          <button
            disabled={Number(params.get("page") || 1) * 20 >= total}
            onClick={() => {
              const p = new URLSearchParams(params);
              p.set("page", String(Number(p.get("page") || 1) + 1));
              setParams(p);
            }}
          >
            Sau →
          </button>
        </div>
      </section>
      {previewOffering &&
        (() => {
          const enrolledOfferings = regs.map((e) => e.offering);
          const alreadyEnrolled = enrolledOfferings.some(
            (x) => x.id === previewOffering.id,
          );
          const conflicts = previewOffering.schedule
            .flatMap((slot) =>
              findSlotConflicts(previewOffering, slot, enrolledOfferings),
            )
            .map((c) => c.offering)
            .filter(
              (item, idx, all) =>
                all.findIndex((other) => other.id === item.id) === idx,
            );
          return (
            <div
              className="modal-backdrop"
              onClick={(e) => {
                if (e.target === e.currentTarget) setPreviewOffering(null);
              }}
              onKeyDown={(e) => {
                if (e.key === "Escape") setPreviewOffering(null);
              }}
            >
              <section
                className="modal"
                role="dialog"
                aria-modal="true"
                aria-labelledby="preview-tt-title"
                style={{
                  width: "min(1180px, 96vw)",
                  maxHeight: "92vh",
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
                    gap: 14,
                    flexWrap: "wrap",
                    background: "var(--panel)",
                  }}
                >
                  <div>
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                        flexWrap: "wrap",
                        marginBottom: 4,
                      }}
                    >
                      <span className="code-badge">{previewOffering.code}</span>
                      <span className="pill">
                        Lớp {previewOffering.section} ·{" "}
                        {previewOffering.credits} TC
                      </span>
                      {conflicts.length > 0 ? (
                        <span
                          style={{
                            fontSize: 11.5,
                            fontWeight: 700,
                            padding: "3px 8px",
                            background: "#fdecee",
                            color: "#d71920",
                          }}
                        >
                          Trùng lịch với{" "}
                          {conflicts.map((c) => c.code).join(", ")}
                        </span>
                      ) : (
                        <span
                          style={{
                            fontSize: 11.5,
                            fontWeight: 700,
                            padding: "3px 8px",
                            background: "#ecfdf5",
                            color: "#047857",
                          }}
                        >
                          Không trùng lịch học
                        </span>
                      )}
                    </div>
                    <h2
                      id="preview-tt-title"
                      style={{ margin: 0, fontSize: 18 }}
                    >
                      Xem trước thời khóa biểu: {previewOffering.name}
                    </h2>
                    <small className="muted">
                      GV: {previewOffering.instructor} · Phòng{" "}
                      {previewOffering.room} · Sĩ số{" "}
                      {previewOffering.enrolledCount}/{previewOffering.capacity}
                    </small>
                  </div>
                  <div className="actions" style={{ marginTop: 0 }}>
                    {week >= 3 && !alreadyEnrolled && canEnroll && (
                      <button
                        type="button"
                        className="btn-tdtu-red"
                        onClick={() => {
                          const target = previewOffering;
                          setPreviewOffering(null);
                          setSelected(target);
                          setReason("");
                        }}
                      >
                        {previewOffering.enrolledCount >=
                        previewOffering.capacity
                          ? "Vào danh sách chờ"
                          : "Đăng ký lớp này"}
                      </button>
                    )}
                    <button
                      type="button"
                      className="btn-outline"
                      onClick={() => setPreviewOffering(null)}
                    >
                      Đóng
                    </button>
                  </div>
                </div>
                <div
                  style={{
                    flex: 1,
                    overflowY: "auto",
                    padding: 16,
                    background: "var(--soft)",
                  }}
                >
                  <Timetable regs={regs} preview={previewOffering} />
                </div>
              </section>
            </div>
          );
        })()}
      {selected && (
        <div
          className="modal-backdrop"
          onClick={(e) => {
            if (e.target === e.currentTarget && !busy) setSelected(null);
          }}
          onKeyDown={(e) => {
            if (e.key === "Escape" && !busy) setSelected(null);
          }}
        >
          <section
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="confirm-title"
          >
            <h2 id="confirm-title">Xác nhận đăng ký học phần</h2>
            <h3>{selected.name}</h3>
            <p>
              <span className="mono-id">{selected.code}</span> · Lớp{" "}
              {selected.section} · {selected.credits} tín chỉ
            </p>
            <p className="muted">
              Hệ thống sẽ tự động kiểm tra điều kiện tiên quyết, tín chỉ tích
              lũy và lịch học trước khi xác nhận đăng ký.
            </p>
            {reason && (
              <div role="alert" className="notice">
                {reason}
              </div>
            )}
            <div className="actions">
              <button
                type="button"
                className="btn-outline"
                disabled={busy}
                onClick={() => setSelected(null)}
              >
                Đóng
              </button>
              <button
                type="button"
                autoFocus
                disabled={busy}
                className="primary"
                onClick={register}
              >
                {busy ? "Đang xử lý…" : "Đăng ký học phần"}
              </button>
            </div>
          </section>
        </div>
      )}
    </>
  );
}
function Waitlist({
  canEnroll,
  notify,
  changed,
}: {
  canEnroll: boolean;
  notify: (s: string) => void;
  changed: () => Promise<void>;
}) {
  const [items, setItems] = useState<
    Awaited<ReturnType<typeof api.getWaitlist>>["items"]
  >([]);
  const prevRef = useRef<WaitlistSummary[]>([]);
  const leftRef = useRef<Set<number>>(new Set());

  const load = async () => {
    try {
      const nextItems = (await api.getWaitlist()).items;
      const nextSummaries: WaitlistSummary[] = nextItems.map((it) => ({
        id: it.id,
        offeringId: it.offeringId,
        code: it.offering.code,
        name: it.offering.name,
      }));
      if (prevRef.current.length > 0) {
        const missing = prevRef.current.filter(
          (p) =>
            !nextSummaries.some((n) => n.offeringId === p.offeringId) &&
            !leftRef.current.has(p.id),
        );
        if (missing.length > 0) {
          const activeRegs = await api.timetable();
          const activeIds = new Set(activeRegs.map((r) => r.offering.id));
          const promoted = detectPromotedWaitlist(
            prevRef.current,
            nextSummaries,
            activeIds,
            leftRef.current,
          );
          if (promoted.length > 0) {
            await changed();
            for (const p of promoted) {
              notify(`Bạn đã được đôn vào lớp ${p.code} — ${p.name}`);
            }
          }
        }
      }
      prevRef.current = nextSummaries;
      setItems(nextItems);
    } catch (e) {
      notify((e as Error).message);
    }
  };
  useEffect(() => {
    void load();
    const timer = window.setInterval(load, 30000);
    const focus = () => void load();
    window.addEventListener("focus", focus);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener("focus", focus);
    };
  }, []);
  return (
    <div>
      <div className="page-heading">
        <div>
          <h1>Danh sách chờ</h1>
          <p className="muted">
            Xếp hàng theo thứ tự thời gian đăng ký. Khi có chỗ trống, người đứng
            đầu hàng sẽ được tự động nhận vào lớp.
          </p>
        </div>
      </div>
      <section className="panel">
        {!items.length ? (
          <p className="empty">Bạn chưa ở trong danh sách chờ nào.</p>
        ) : (
          items.map((item) => (
            <div className="enrolled" key={item.id}>
              <b>{item.offering.code}</b>
              <span>
                {item.offering.name} · Lớp {item.offering.section}
              </span>
              <span className="pill">Vị trí {item.position}</span>
              <small>
                Tham gia: {new Date(item.enqueuedAt).toLocaleString("vi-VN")}
              </small>
              {item.blockedReason && (
                <small className="warning">
                  Chưa thể đôn:{" "}
                  {item.blockedReason === "SCHEDULE_CONFLICT"
                    ? "trùng lịch học"
                    : item.blockedReason === "CREDIT_LIMIT_EXCEEDED"
                      ? "vượt hạn mức tín chỉ"
                      : item.blockedReason}
                </small>
              )}
              <button
                type="button"
                className="btn-danger-soft"
                style={{ marginLeft: "auto" }}
                disabled={!canEnroll}
                title={
                  !canEnroll
                    ? "Cổng đăng ký học phần hiện đang đóng"
                    : undefined
                }
                onClick={async () => {
                  if (
                    !window.confirm(
                      `Bạn có chắc muốn hủy danh sách chờ môn ${item.offering.code} — ${item.offering.name} (Lớp ${item.offering.section})?`,
                    )
                  )
                    return;
                  try {
                    leftRef.current.add(item.id);
                    await api.leaveWaitlist(item.id);
                    await load();
                    await changed();
                    notify(`Đã hủy danh sách chờ môn ${item.offering.name}`);
                  } catch (e) {
                    leftRef.current.delete(item.id);
                    notify((e as Error).message);
                  }
                }}
              >
                Hủy danh sách chờ
              </button>
            </div>
          ))
        )}
      </section>
    </div>
  );
}

const TIMETABLE_PALETTES = [
  { bg: "#e8f1fb", border: "#b3d1f2", accent: "#00529c", text: "#00356b" },
  { bg: "#ecfdf5", border: "#a7f3d0", accent: "#059669", text: "#065f46" },
  { bg: "#fff7ed", border: "#fed7aa", accent: "#ea580c", text: "#9a3412" },
  { bg: "#f3e8ff", border: "#d8b4fe", accent: "#7c3aed", text: "#5b21b6" },
  { bg: "#ecfeff", border: "#a5f3fc", accent: "#0891b2", text: "#155e75" },
  { bg: "#fdf2f8", border: "#fbcfe8", accent: "#db2777", text: "#9d174d" },
];

function getTdtuShiftLabel(start: string): string {
  const m = parseTime(start);
  if (m < 9 * 60 + 25) return "Ca 1";
  if (m < 12 * 60 + 15) return "Ca 2";
  if (m < 15 * 60 + 20) return "Ca 3";
  if (m < 18 * 60) return "Ca 4";
  return "Ca 5";
}

const Timetable = memo(function Timetable({
  regs,
  preview,
}: {
  regs: Enrollment[];
  preview: Offering | null;
}) {
  const [focused, setFocused] = useState<Offering | null>(null);
  const list = [
    ...regs.map((e) => e.offering),
    ...(preview && !regs.some((e) => e.offering.id === preview.id)
      ? [preview]
      : []),
  ];
  const isPreviewMode = Boolean(preview);
  const totalSessions = regs.reduce(
    (n, e) => n + e.offering.schedule.length,
    0,
  );
  const dayNames = [
    { short: "T2", full: "Thứ Hai", day: 1 },
    { short: "T3", full: "Thứ Ba", day: 2 },
    { short: "T4", full: "Thứ Tư", day: 3 },
    { short: "T5", full: "Thứ Năm", day: 4 },
    { short: "T6", full: "Thứ Sáu", day: 5 },
    { short: "T7", full: "Thứ Bảy", day: 6 },
    { short: "CN", full: "Chủ nhật", day: 7 },
  ];

  return (
    <section className="panel tt-panel">
      <div className="section-title" style={{ flexWrap: "wrap" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <h3>
            <CalendarDays size={16} /> Thời khóa biểu tuần (Ca chuẩn TDTU)
          </h3>
          <span className="pill">{totalSessions} ca / tuần</span>
        </div>
        <div className="tt-legend">
          <span>
            <i
              style={{
                background: "#e6f0fa",
                border: "2px solid #004b91",
              }}
            />{" "}
            Đã đăng ký
          </span>
          <span>
            <i
              style={{
                background: "#fef3c7",
                border: "2px dashed #d97706",
              }}
            />{" "}
            Đang xem trước
          </span>
          <span>
            <i
              style={{
                background:
                  "repeating-linear-gradient(-45deg, #fee2e2, #fee2e2 3px, #ef4444 3px, #ef4444 5px)",
                border: "2px solid #d71920",
              }}
            />{" "}
            Trùng lịch
          </span>
        </div>
      </div>

      {focused && (
        <div className="tt-focus-bar">
          <div>
            <b>
              {focused.code} — {focused.name}
            </b>
            <small>
              Lớp {focused.section} · {focused.credits} TC · GV:{" "}
              {focused.instructor} · Phòng {focused.room}
            </small>
          </div>
          <button
            type="button"
            className="text-button"
            onClick={() => setFocused(null)}
          >
            Đóng chi tiết
          </button>
        </div>
      )}

      {!list.length && (
        <p className="empty" style={{ padding: "18px 0 10px" }}>
          Chưa đăng ký lớp nào trong kỳ này. Các khung giờ trống sẵn sàng để bạn
          xếp lịch.
        </p>
      )}

      <div className="table-scroll">
        <div className="timetable">
          <div className="days">
            <span className="tt-corner">Giờ</span>
            {dayNames.map((d) => {
              const dayCount = list.reduce(
                (n, o) => n + o.schedule.filter((s) => s.day === d.day).length,
                0,
              );
              return (
                <div
                  key={d.full}
                  className={`tt-day-head ${d.day >= 6 ? "is-weekend" : ""}`}
                >
                  <b>{d.full}</b>
                  <span className="tt-day-sub">
                    {dayCount > 0 ? `${dayCount} buổi` : "Trống"}
                  </span>
                </div>
              );
            })}
          </div>
          <div className="grid-body">
            {/* Vertical column guides */}
            <div className="tt-cols" aria-hidden="true">
              <div />
              {dayNames.map((d) => (
                <div
                  key={d.day}
                  className={`tt-col ${d.day >= 6 ? "is-weekend" : ""}`}
                />
              ))}
            </div>

            {Array.from({ length: 16 }, (_, i) => (
              <div className="hour" style={{ top: i * 52 }} key={i}>
                <span>{String(i + 6).padStart(2, "0")}:00</span>
              </div>
            ))}

            {list.flatMap((o) =>
              o.schedule.map((s, i) => {
                const overlaps = list
                  .flatMap((x) => x.schedule.map((slot, j) => ({ x, slot, j })))
                  .filter(
                    (v) =>
                      v.slot.day === s.day &&
                      parseTime(v.slot.start) < parseTime(s.end) &&
                      parseTime(s.start) < parseTime(v.slot.end),
                  );
                const index = overlaps.findIndex(
                  (v) => v.x.id === o.id && v.j === i,
                );
                const conflict = findSlotConflicts(o, s, list)
                  .map((item) => item.offering)
                  .filter(
                    (item, idx, all) =>
                      all.findIndex((other) => other.id === item.id) === idx,
                  );
                const isPreviewCard = preview?.id === o.id;
                const isConflict = conflict.length > 0;
                const palette =
                  TIMETABLE_PALETTES[o.courseId % TIMETABLE_PALETTES.length];
                const isSelected = focused?.id === o.id;
                const heightPx = Math.max(
                  52,
                  ((parseTime(s.end) - parseTime(s.start)) / 60) * 52 - 5,
                );
                const shiftLabel = getTdtuShiftLabel(s.start);

                // Trong chế độ Xem trước, dùng 3 tông màu tương phản cực cao:
                // 1. Đã đăng ký (không trùng): Xanh dương TDTU đồng nhất
                // 2. Đang xem trước (không trùng): Vàng cam nổi bật + viền nét đứt
                // 3. Trùng lịch: Đỏ TDTU + sọc chéo cảnh báo
                const cardStyle = isConflict
                  ? {}
                  : isPreviewCard
                    ? {
                        background: "#fef3c7",
                        borderColor: "#d97706",
                        borderLeftColor: "#d97706",
                        color: "#78350f",
                      }
                    : isPreviewMode
                      ? {
                          background: "#e6f0fa",
                          borderColor: "#004b91",
                          borderLeftColor: "#004b91",
                          color: "#002b56",
                        }
                      : {
                          background: palette.bg,
                          borderColor: palette.border,
                          borderLeftColor: palette.accent,
                          color: palette.text,
                        };

                return (
                  <button
                    type="button"
                    key={o.id + "-" + i}
                    onClick={() => setFocused(isSelected ? null : o)}
                    title={
                      isConflict
                        ? "Trùng lịch với " +
                          conflict.map((c) => c.name).join(", ")
                        : `${o.code} — ${o.name} (${shiftLabel}: ${s.start}–${s.end}, Phòng ${o.room})`
                    }
                    className={
                      "lesson " +
                      (isPreviewCard ? "preview " : "") +
                      (isConflict ? "conflict " : "") +
                      (isSelected ? "selected" : "")
                    }
                    style={{
                      top: ((parseTime(s.start) - 360) / 60) * 52 + 2,
                      left: `calc(58px + (100% - 58px) / 7 * ${s.day - 1} + (100% - 58px) / 7 * ${index / overlaps.length} + 3px)`,
                      width: `calc((100% - 58px) / 7 / ${overlaps.length} - 6px)`,
                      height: heightPx,
                      ...cardStyle,
                    }}
                  >
                    <div className="lesson-head">
                      <b
                        style={{
                          display: "inline-flex",
                          alignItems: "center",
                          gap: 3,
                        }}
                      >
                        {isConflict && (
                          <AlertTriangle size={12} aria-hidden="true" />
                        )}
                        {o.code}
                      </b>
                      {isConflict ? (
                        <span className="lesson-badge-conflict">TRÙNG</span>
                      ) : isPreviewCard ? (
                        <span className="lesson-badge-preview">XEM TRƯỚC</span>
                      ) : isPreviewMode ? (
                        <span className="lesson-badge-enrolled">ĐÃ ĐK</span>
                      ) : (
                        <span className="lesson-sec">{o.section}</span>
                      )}
                    </div>
                    <span className="lesson-name">{o.name}</span>
                    <small className="lesson-meta">
                      {shiftLabel} ({s.start}–{s.end}) · {o.room}
                    </small>
                  </button>
                );
              }),
            )}
          </div>
        </div>
      </div>
    </section>
  );
});
