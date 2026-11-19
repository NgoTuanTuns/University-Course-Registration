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
  Award,
  BookOpen,
  LayoutDashboard,
  CalendarDays,
  Clock,
  GitBranch,
  GraduationCap,
  LogOut,
  Sun,
  Moon,
  ArrowUpRight,
  Search,
  ChevronRight,
  ShieldCheck,
  Menu,
} from "lucide-react";
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
const week = Number(import.meta.env.VITE_WEEK || 5);
export default function App() {
  const [session, updateSession] = useState<Session | null>(getSession());
  const [dark, setDark] = useState(localStorage.getItem("theme") === "dark");
  const [menu, setMenu] = useState(false);
  const [toast, setToast] = useState("");
  const [regs, setRegs] = useState<Enrollment[]>([]);
  const [preview, setPreview] = useState<Offering | null>(null);
  const [error, setError] = useState("");
  const location = useLocation();
  const nav = useNavigate();
  const notify = (s: string) => {
    setToast(s);
    window.setTimeout(() => setToast(""), 5000);
  };
  async function load() {
    try {
      setRegs(await api.timetable());
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
    // Timetable is a student resource. Calling it with an admin token can
    // produce a 403/401 response and incorrectly look like an expired session.
    if (session?.user.role === "student" && week >= 2) void load();
  }, [session]);
  useEffect(() => {
    const expire = () => {
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
          <div className="brand">
            <GraduationCap /> UniFlow
          </div>
          <span className="eyebrow">YOUR NEXT CHAPTER</span>
          <h1>
            Chủ động hôm nay.
            <br />
            Vững bước tương lai.
          </h1>
          <p>
            Một không gian để lên kế hoạch, khám phá học phần
            <br />
            và xây dựng hành trình học tập của riêng bạn.
          </p>
          <div className="orbit">
            ✦<span>Học tập có định hướng</span>
          </div>
          <small>UNIVERSITY COURSE REGISTRATION · 2026</small>
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
              nav(location.pathname === "/login" ? "/" : location.pathname, {
                replace: true,
              });
            } catch (e) {
              notify((e as Error).message);
            }
          }}
        >
          <div className="eyebrow">CHÀO MỪNG TRỞ LẠI</div>
          <h2>Đăng nhập UniFlow</h2>
          <p className="muted">Tiếp tục hành trình học tập của bạn.</p>
          <label>
            Email
            <input
              name="email"
              type="email"
              required
              placeholder="sv0001@uni.edu.vn"
            />
          </label>
          <label>
            Mật khẩu
            <input name="password" type="password" required />
          </label>
          <button className="primary">
            Đăng nhập <ArrowUpRight size={17} />
          </button>
          <p className="muted">
            Sử dụng tài khoản email do nhà trường cấp để đăng nhập.
          </p>
          {toast && <p role="alert">{toast}</p>}
        </form>
      </div>
    );
  const credits = regs.reduce((n, e) => n + e.offering.credits, 0);
  const admin = location.pathname.startsWith("/admin");
  return (
    <div className="shell">
      <aside className={menu ? "open" : ""}>
        <div className="brand">
          <GraduationCap /> UniFlow<span>PORTAL</span>
        </div>
        <div className="workspace">
          <div className="avatar">{admin ? "QT" : "SV"}</div>
          <div>
            <b>{admin ? "Không gian quản trị" : "Cổng sinh viên"}</b>
            <small>
              {admin
                ? "Đại học · Học kỳ 2026-1"
                : session.user.faculty || "Đại học · Học kỳ 2026-1"}
            </small>
          </div>
        </div>
        <div className="nav-label">KHÔNG GIAN HỌC TẬP</div>
        <nav>
          {[
            ["/", "Tổng quan", LayoutDashboard],
            ["/courses", "Tra cứu học phần", BookOpen],
            ...(week >= 2
              ? [["/timetable", "Thời khóa biểu", CalendarDays]]
              : []),
            ...(week >= 4
              ? [["/waitlist", "Danh sách chờ", LayoutDashboard]]
              : []),
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
              <NavLink to="/admin/courses">
                <ShieldCheck size={19} />
                Quản trị học phần
              </NavLink>
              <NavLink to="/admin/prereqs">
                <ShieldCheck size={19} /> Điều kiện tiên quyết
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
              setSession(null);
              updateSession(null);
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
            <ChevronRight size={14} /> <b>Học kỳ I, 2026–2027</b>
          </span>
          <div className="header-right">
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
              element={(() => {
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
                const cs = getCreditStatus(credits, session.user.maxCredits);
                const ringR = 46;
                const ringC = 2 * Math.PI * ringR;
                const ringOffset = ringC * (1 - gradPct / 100);

                return (
                  <>
                    <div className="hero-tdtu">
                      <div className="hero-tdtu-left">
                        <div className="hero-tdtu-badges">
                          <span className="hero-badge-red">HỌC KỲ 2026-1</span>
                          {session.user.role === "student" && (
                            <span className="hero-badge-glass">
                              Sinh viên Năm {studentYear}
                            </span>
                          )}
                          {session.user.mssv && (
                            <span className="hero-badge-glass">
                              MSSV: {session.user.mssv}
                            </span>
                          )}
                        </div>
                        <h1>{session.user.fullName}</h1>
                        <p>
                          {session.user.faculty ||
                            "Cổng đăng ký học phần Đại học"}{" "}
                          · Quản lý kế hoạch học tập, kiểm tra điều kiện tiên
                          quyết và xếp thời khóa biểu theo đúng tiến độ đào tạo.
                        </p>
                        <div className="hero-tdtu-actions">
                          <button
                            className="btn-tdtu-red"
                            onClick={() => nav("/courses")}
                          >
                            Đăng ký học phần ngay <ArrowUpRight size={17} />
                          </button>
                          <button
                            className="btn-tdtu-glass"
                            onClick={() => nav("/prerequisites")}
                          >
                            <GitBranch size={16} /> Xem sơ đồ tiên quyết
                          </button>
                        </div>
                      </div>

                      <div
                        className="hero-tdtu-ring"
                        onClick={() => nav("/academic-record")}
                        role="button"
                        tabIndex={0}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" || e.key === " ")
                            nav("/academic-record");
                        }}
                        title="Xem chi tiết hồ sơ học tập"
                      >
                        <svg width="118" height="118" viewBox="0 0 118 118">
                          <circle
                            cx="59"
                            cy="59"
                            r={ringR}
                            fill="none"
                            stroke="rgba(255,255,255,0.16)"
                            strokeWidth="9"
                          />
                          <circle
                            cx="59"
                            cy="59"
                            r={ringR}
                            fill="none"
                            stroke="#ff4d54"
                            strokeWidth="9"
                            strokeLinecap="round"
                            strokeDasharray={ringC}
                            strokeDashoffset={ringOffset}
                            transform="rotate(-90 59 59)"
                          />
                        </svg>
                        <div className="hero-ring-center">
                          <strong>{gradPct}%</strong>
                          <span>
                            {accCredits}/{gradTarget} TC
                          </span>
                        </div>
                        <small>Tiến độ tích lũy</small>
                      </div>
                    </div>

                    <div className="stats stats-pro">
                      <article
                        className="kpi-card"
                        onClick={() => nav("/academic-record")}
                      >
                        <div className="kpi-top">
                          <span className="kpi-icon kpi-blue">
                            <Award size={19} />
                          </span>
                          <span className="kpi-tag">Năm {studentYear}</span>
                        </div>
                        <span className="kpi-label">Tín chỉ tích lũy</span>
                        <strong>{accCredits} TC</strong>
                        <small>Cơ sở mở khóa học phần nâng cao</small>
                      </article>

                      <article
                        className="kpi-card"
                        onClick={() => nav("/courses")}
                      >
                        <div className="kpi-top">
                          <span className="kpi-icon kpi-red">
                            <BookOpen size={19} />
                          </span>
                          <span className="kpi-tag">{cs.percent}%</span>
                        </div>
                        <span className="kpi-label">Tín chỉ học kỳ này</span>
                        <strong>
                          {credits}{" "}
                          <span className="kpi-sub">
                            / {session.user.maxCredits} TC
                          </span>
                        </strong>
                        <div className="capacity" style={{ width: "100%" }}>
                          <i
                            style={{
                              width: `${cs.percent}%`,
                              background: cs.color,
                            }}
                          />
                        </div>
                      </article>

                      <article
                        className="kpi-card"
                        onClick={() => nav("/timetable")}
                      >
                        <div className="kpi-top">
                          <span className="kpi-icon kpi-navy">
                            <CalendarDays size={19} />
                          </span>
                          <span className="kpi-tag">HK 2026-1</span>
                        </div>
                        <span className="kpi-label">Lớp học phần đã chọn</span>
                        <strong>{regs.length} lớp</strong>
                        <small>{weeklySessions} buổi học mỗi tuần</small>
                      </article>

                      <article
                        className="kpi-card"
                        onClick={() => nav("/prerequisites")}
                      >
                        <div className="kpi-top">
                          <span className="kpi-icon kpi-emerald">
                            <GitBranch size={19} />
                          </span>
                          <span className="kpi-tag">DAG</span>
                        </div>
                        <span className="kpi-label">Lộ trình tiên quyết</span>
                        <strong style={{ fontSize: 20 }}>Trực quan hóa</strong>
                        <small>Xem chuỗi môn AND / OR & mở khóa</small>
                      </article>
                    </div>

                    <div className="dashboard-bottom">
                      <section className="panel">
                        <div className="section-title">
                          <h3>
                            <Clock size={16} /> Phân bổ buổi học trong tuần
                          </h3>
                          <span className="pill">
                            {weeklySessions} buổi · {credits} TC
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
                                      height: Math.max(8, count * 42),
                                      opacity: count > 0 ? 1 : 0.25,
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
                            {regs.slice(0, 3).map((e) => (
                              <div className="mini-enrolled-item" key={e.id}>
                                <b>{e.offering.code}</b>
                                <span>{e.offering.name}</span>
                                <small>{e.offering.credits} TC</small>
                              </div>
                            ))}
                            {regs.length > 3 && (
                              <button
                                className="text-button"
                                onClick={() => nav("/timetable")}
                              >
                                Xem toàn bộ {regs.length} lớp trong thời khóa
                                biểu →
                              </button>
                            )}
                          </div>
                        ) : (
                          <div className="dash-empty-cta">
                            <span>
                              Chưa có học phần nào được đăng ký trong kỳ 2026-1.
                            </span>
                            <button
                              className="text-button"
                              onClick={() => nav("/courses")}
                            >
                              Chọn môn đúng tiến độ Năm {studentYear} →
                            </button>
                          </div>
                        )}
                      </section>

                      <section className="panel">
                        <div className="section-title">
                          <h3>Thao tác nhanh</h3>
                          <span className="muted">Dành cho sinh viên</span>
                        </div>
                        <div className="quick-grid">
                          {[
                            {
                              title: "Tra cứu & Đăng ký học phần",
                              desc: `Ưu tiên hiển thị các môn đúng tiến độ Năm ${studentYear} và đủ điều kiện`,
                              to: "/courses",
                              icon: BookOpen,
                              tone: "kpi-red",
                            },
                            {
                              title: "Sơ đồ tiên quyết (DAG)",
                              desc: "Theo dõi môn bắt buộc (AND), môn thay thế (OR) và nhánh mở khóa",
                              to: "/prerequisites",
                              icon: GitBranch,
                              tone: "kpi-blue",
                            },
                            {
                              title: "Thời khóa biểu cá nhân",
                              desc: "Kiểm tra trực quan lịch học theo ngày và phát hiện trùng giờ",
                              to: "/timetable",
                              icon: CalendarDays,
                              tone: "kpi-navy",
                            },
                            {
                              title: "Hồ sơ học tập & GPA",
                              desc: `Xem điểm trung bình và danh sách ${accCredits} tín chỉ đã tích lũy`,
                              to: "/academic-record",
                              icon: Award,
                              tone: "kpi-emerald",
                            },
                          ].map((item) => {
                            const Icon = item.icon;
                            return (
                              <button
                                key={item.to}
                                type="button"
                                className="quick-tile"
                                onClick={() => nav(item.to)}
                              >
                                <span className={`kpi-icon ${item.tone}`}>
                                  <Icon size={18} />
                                </span>
                                <div className="quick-tile-body">
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
              })()}
            />
            <Route
              path="/courses"
              element={
                <Courses
                  week={week}
                  regsCredits={credits}
                  maxCredits={session.user.maxCredits}
                  notify={notify}
                  changed={load}
                  preview={(o) => {
                    setPreview(o);
                    nav("/timetable");
                  }}
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
                        <div className="eyebrow">THỜI KHÓA BIỂU CÁ NHÂN</div>
                        <h1>Lịch học trong tuần</h1>
                        <p className="muted">
                          Theo dõi lịch học theo khung giờ 07:00 – 21:00, xem
                          trước lớp mới và phát hiện xung đột tự động.
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
                          <option>Học kỳ 2026-1</option>
                        </select>
                        <button
                          type="button"
                          className="btn-outline"
                          onClick={() => window.print()}
                        >
                          In thời khóa biểu
                        </button>
                        <button
                          type="button"
                          className="primary"
                          onClick={() => nav("/courses")}
                        >
                          Thêm học phần <ArrowUpRight size={15} />
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
                            2026-1.
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
                                <button
                                  type="button"
                                  className="btn-danger-soft"
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
                            );
                          })}
                        </div>
                      )}
                    </section>
                  </>
                ) : (
                  <Navigate to="/courses" />
                )
              }
            />
            <Route
              path="/waitlist"
              element={
                week >= 4 ? (
                  <Waitlist notify={notify} changed={load} />
                ) : (
                  <Navigate to="/" />
                )
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
                    <AdminPanel notify={notify} />
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
      {toast && (
        <div className="toast" role="status">
          {toast}
          <button onClick={() => setToast("")}>×</button>
        </div>
      )}
    </div>
  );
}
function Courses({
  week,
  regsCredits,
  maxCredits,
  notify,
  changed,
  preview,
}: {
  week: number;
  regsCredits: number;
  maxCredits: number;
  notify: (s: string) => void;
  changed: () => Promise<void>;
  preview: (o: Offering) => void;
}) {
  const [params, setParams] = useSearchParams();
  const [items, setItems] = useState<Offering[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  const [selected, setSelected] = useState<Offering | null>(null);
  const [busy, setBusy] = useState(false);
  const [reason, setReason] = useState("");
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
  }, [params, retry]);
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
          } else {
            setReason(
              "🎉 Đăng ký học phần thành công! Môn học đã được ghi nhận vào thời khóa biểu.",
            );
            notify(`Đăng ký thành công môn ${selected.name}`);
            await changed();
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
          ? "Không tìm thấy học phần tương ứng trong cơ sở dữ liệu backend. Danh mục đang hiển thị là dữ liệu tĩnh; hãy kiểm tra lại seed của nhóm."
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
          <div className="eyebrow">KHÁM PHÁ & LỰA CHỌN</div>
          <h1>Tra cứu học phần</h1>
          <p className="muted">Tìm học phần phù hợp với lộ trình của bạn.</p>
        </div>
        <span className="pill">Học kỳ 2026-1</span>
      </div>
      <section className="panel filters">
        <div className="section-title">
          <h3>
            <Search size={18} /> Bộ lọc học phần
          </h3>
          <button className="text-button" onClick={() => setParams({})}>
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
      </section>
      <section className="panel results">
        <div className="section-title">
          <h3>
            Danh sách học phần <span className="count">{total}</span>
          </h3>
          <span className="muted">20 kết quả / trang</span>
        </div>
        {loading ? (
          <div className="skeleton">Đang tải học phần…</div>
        ) : error ? (
          <div className="notice" role="alert">
            {error}
            <button onClick={() => setRetry((n) => n + 1)}>Thử lại</button>
          </div>
        ) : !items.length ? (
          <div className="empty">Không tìm thấy học phần phù hợp.</div>
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
                {items.map((o) => (
                  <tr key={o.id}>
                    <td>
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 6,
                          marginBottom: 4,
                        }}
                      >
                        <b className="course-code" style={{ marginBottom: 0 }}>
                          {o.code}
                        </b>
                        {o.eligibilityStatus === "RECOMMENDED" && (
                          <span
                            style={{
                              fontSize: 10,
                              fontWeight: 700,
                              padding: "2px 6px",
                              borderRadius: 999,
                              background: "#e8f1fb",
                              color: "#00529c",
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
                              background: "#ecfdf5",
                              color: "#047857",
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
                          {s.day === 7 ? "CN" : "T" + (s.day + 1)} · {s.start}–
                          {s.end}
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
                        {week >= 2 && (
                          <button onClick={() => preview(o)}>Xem trước</button>
                        )}
                        {week >= 3 && (
                          <button
                            className="primary"
                            onClick={() => {
                              setSelected(o);
                              setReason("");
                            }}
                          >
                            {o.enrolledCount >= o.capacity
                              ? "Vào danh sách chờ"
                              : "Đăng ký học phần"}
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
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
      {selected && (
        <div className="modal-backdrop">
          <section
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="confirm-title"
          >
            <span className="eyebrow">XÁC NHẬN LỰA CHỌN</span>
            <h2 id="confirm-title">Kiểm tra điều kiện tiên quyết</h2>
            <h3>{selected.name}</h3>
            <p>
              {selected.code} · Lớp {selected.section} · {selected.credits} tín
              chỉ
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
              <button disabled={busy} onClick={() => setSelected(null)}>
                Đóng
              </button>
              <button disabled={busy} className="primary" onClick={register}>
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
  notify,
  changed,
}: {
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
              notify(`🎉 Bạn đã được đăng ký vào lớp ${p.code} — ${p.name}!`);
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
          <div className="eyebrow">XẾP HÀNG HỌC PHẦN</div>
          <h1>Danh sách chờ</h1>
          <p className="muted">
            Vào trước, ra trước — khi có người hủy, bạn ở đầu hàng sẽ được tự
            động đăng ký.
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
                className="text-button"
                style={{ color: "#ef4444", marginLeft: "auto" }}
                onClick={async () => {
                  try {
                    leftRef.current.add(item.id);
                    await api.leaveWaitlist(item.id);
                    await load();
                    await changed();
                    notify("Đã rời danh sách chờ");
                  } catch (e) {
                    leftRef.current.delete(item.id);
                    notify((e as Error).message);
                  }
                }}
              >
                Rời hàng chờ
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
            <CalendarDays size={16} /> Thời khóa biểu tuần
          </h3>
          <span className="pill">{totalSessions} buổi / tuần</span>
        </div>
        <div className="tt-legend">
          <span>
            <i style={{ background: "#00529c" }} /> Đã đăng ký
          </span>
          <span>
            <i
              style={{
                background: "transparent",
                border: "1.5px dashed #00529c",
              }}
            />{" "}
            Xem trước
          </span>
          <span>
            <i style={{ background: "#d71920" }} /> Trùng lịch
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

            {Array.from({ length: 15 }, (_, i) => (
              <div className="hour" style={{ top: i * 52 }} key={i}>
                <span>{String(i + 7).padStart(2, "0")}:00</span>
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
                const palette =
                  TIMETABLE_PALETTES[o.courseId % TIMETABLE_PALETTES.length];
                const isSelected = focused?.id === o.id;
                const heightPx = Math.max(
                  46,
                  ((parseTime(s.end) - parseTime(s.start)) / 60) * 52 - 5,
                );
                return (
                  <button
                    type="button"
                    key={o.id + "-" + i}
                    onClick={() => setFocused(isSelected ? null : o)}
                    title={
                      conflict.length
                        ? "Trùng lịch với " +
                          conflict.map((c) => c.name).join(", ")
                        : `${o.code} — ${o.name} (${s.start}–${s.end}, Phòng ${o.room})`
                    }
                    className={
                      "lesson " +
                      (preview?.id === o.id ? "preview " : "") +
                      (conflict.length ? "conflict " : "") +
                      (isSelected ? "selected" : "")
                    }
                    style={{
                      top: ((parseTime(s.start) - 420) / 60) * 52 + 2,
                      left: `calc(58px + (100% - 58px) / 7 * ${s.day - 1} + (100% - 58px) / 7 * ${index / overlaps.length} + 3px)`,
                      width: `calc((100% - 58px) / 7 / ${overlaps.length} - 6px)`,
                      height: heightPx,
                      background: conflict.length ? undefined : palette.bg,
                      borderColor: conflict.length ? undefined : palette.border,
                      borderLeftColor: conflict.length
                        ? "#d71920"
                        : palette.accent,
                      color: conflict.length ? undefined : palette.text,
                    }}
                  >
                    <div className="lesson-head">
                      <b>
                        {conflict.length ? "⚠ " : ""}
                        {o.code}
                      </b>
                      <span className="lesson-sec">{o.section}</span>
                    </div>
                    <span className="lesson-name">{o.name}</span>
                    <small className="lesson-meta">
                      {s.start}–{s.end} · {o.room}
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
