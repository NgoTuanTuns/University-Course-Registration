import { useEffect, useState } from "react";
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
  BookOpen,
  LayoutDashboard,
  CalendarDays,
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
import { getSession, setSession, mockMode } from "./api/http";
import type { Offering, Enrollment, Session } from "./types";
import { findSlotConflicts, parseTime } from "./features/timetable/conflicts";
const week = Number(import.meta.env.VITE_WEEK || 3);
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
    if (session && week >= 2) void load();
  }, [session]);
  useEffect(() => {
    const expire = () => {
      updateSession(null);
      notify("Phiên đã hết hạn. Vui lòng đăng nhập lại.");
    };
    window.addEventListener("session-expired", expire);
    return () => window.removeEventListener("session-expired", expire);
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
              defaultValue={mockMode ? "sv0001@uni.edu.vn" : ""}
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
            {mockMode
              ? "Bản mô phỏng: dùng email sinh viên hoặc admin@uni.edu.vn, mật khẩu bất kỳ."
              : "Kết nối hệ thống thật · Dùng tài khoản do trường cấp."}
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
            <small>Đại học · Học kỳ 2026-1</small>
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
            <NavLink to="/admin/courses">
              <ShieldCheck size={19} />
              Quản trị học phần
            </NavLink>
          )}
        </nav>
        <div className="sidebar-note">
          <GraduationCap />
          <b>Sẵn sàng cho học kỳ mới?</b>
          <p>Lên kế hoạch học tập để mỗi lựa chọn đều có ý nghĩa.</p>
        </div>
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
            <span className="mode">
              {mockMode
                ? "● Dữ liệu mô phỏng"
                : week >= 3
                  ? "● API xác thực · Danh mục tĩnh"
                  : "● API thật"}{" "}
              · Tuần {week}
            </span>
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
          {!mockMode && week >= 3 && (
            <div className="notice" role="status">
              Week 3: đăng nhập và kiểm tra tiên quyết sử dụng backend thật.
              Danh mục học phần và thời khóa biểu đang là dữ liệu tĩnh vì
              backend chưa có API GET /courses và GET /timetable. Đăng ký/hủy
              chưa được kích hoạt vì backend chưa có POST /enroll và DELETE
              /enroll/{"{id}"}.
            </div>
          )}
          <Routes>
            <Route path="/login" element={<Navigate to="/" replace />} />
            <Route
              path="/"
              element={
                <>
                  <div className="page-heading">
                    <div>
                      <div className="eyebrow">TỔNG QUAN HỌC TẬP</div>
                      <h1>
                        Chào {session.user.fullName.split(" ").at(-1)}, ngày mới
                        tốt lành <span>✦</span>
                      </h1>
                      <p className="muted">
                        Mọi kế hoạch cho một học kỳ thành công, bắt đầu từ đây.
                      </p>
                    </div>
                    <span className="pill">Học kỳ 2026-1</span>
                  </div>
                  <div className="hero">
                    <div>
                      <span className="eyebrow">HÀNH TRÌNH CỦA BẠN</span>
                      <h2>
                        Học kỳ mới.
                        <br />
                        Cơ hội mới.
                      </h2>
                      <p>
                        Khám phá học phần phù hợp và chủ động
                        <br />
                        sắp xếp lịch học theo cách của bạn.
                      </p>
                      <button onClick={() => nav("/courses")}>
                        Khám phá học phần <ArrowUpRight size={18} />
                      </button>
                    </div>
                    <div className="hero-art">
                      <GraduationCap size={110} />
                      <span className="floating">✦ Build your future</span>
                    </div>
                  </div>
                  <div className="stats">
                    {[
                      [
                        "Tín chỉ đã đăng ký",
                        credits,
                        "/ " + session.user.maxCredits + " tín chỉ",
                      ],
                      ["Lớp học phần", regs.length, "trong học kỳ này"],
                      [
                        "Buổi học mỗi tuần",
                        regs.reduce(
                          (n, e) => n + e.offering.schedule.length,
                          0,
                        ),
                        "đã được lên lịch",
                      ],
                      ["Học kỳ hiện tại", "2026-1", "Năm học 2026–2027"],
                    ].map(([label, value, note]) => (
                      <article key={label}>
                        <span>
                          {label}
                          <ArrowUpRight size={17} />
                        </span>
                        <strong>{value}</strong>
                        <small>{note}</small>
                      </article>
                    ))}
                  </div>
                  <div className="dashboard-bottom">
                    <section className="panel">
                      <div className="section-title">
                        <h3>Kế hoạch học kỳ</h3>
                        <span className="pill">
                          {credits} / {session.user.maxCredits} tín chỉ
                        </span>
                      </div>
                      <div className="chart">
                        {["T2", "T3", "T4", "T5", "T6", "T7", "CN"].map(
                          (d, i) => (
                            <div key={d}>
                              <div
                                style={{
                                  height: Math.max(
                                    5,
                                    regs.reduce(
                                      (n, e) =>
                                        n +
                                        e.offering.schedule.filter(
                                          (s) => s.day === i + 1,
                                        ).length,
                                      0,
                                    ) * 45,
                                  ),
                                }}
                              />
                              <span>{d}</span>
                            </div>
                          ),
                        )}
                      </div>
                      <p className="muted">
                        Số buổi học theo ngày · Học kỳ 2026-1
                      </p>
                    </section>
                    <section className="panel">
                      <h3>Đi từng bước, chọn đúng môn</h3>
                      {[
                        "Tra cứu học phần theo nhu cầu",
                        "Xem trước lịch học và kiểm tra trùng",
                        "Kiểm tra điều kiện trước khi đăng ký",
                      ].map((s, i) => (
                        <div className="step" key={s}>
                          <b>0{i + 1}</b>
                          <span>{s}</span>
                          <ChevronRight size={16} />
                        </div>
                      ))}
                      <button
                        className="text-button"
                        onClick={() => nav("/courses")}
                      >
                        Bắt đầu lên kế hoạch →
                      </button>
                    </section>
                  </div>
                </>
              }
            />
            <Route
              path="/courses"
              element={
                <Courses
                  week={week}
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
                        <div className="eyebrow">KẾ HOẠCH CÁ NHÂN</div>
                        <h1>Thời khóa biểu</h1>
                        <p className="muted">
                          Một góc nhìn rõ ràng cho tuần học của bạn.
                        </p>
                      </div>
                      <select aria-label="Học kỳ">
                        <option>2026-1</option>
                      </select>
                    </div>
                    {error && (
                      <div className="notice">
                        {error}
                        <button onClick={load}>Thử lại</button>
                      </div>
                    )}
                    <Timetable regs={regs} preview={preview} />
                    <section className="panel">
                      <div className="section-title">
                        <h3>Lớp đang đăng ký · {credits} tín chỉ</h3>
                        {preview && (
                          <button onClick={() => setPreview(null)}>
                            Bỏ xem trước
                          </button>
                        )}
                      </div>
                      {regs.map((e) => (
                        <div className="enrolled" key={e.id}>
                          <b>{e.offering.code}</b>
                          <span>{e.offering.name}</span>
                          {week >= 3 && (
                            <small className="muted">
                              Hủy đăng ký đang chờ API DELETE /enroll/{"{id}"}{" "}
                              từ M3.
                            </small>
                          )}
                        </div>
                      ))}
                    </section>
                  </>
                ) : (
                  <Navigate to="/courses" />
                )
              }
            />
            <Route
              path="/admin/*"
              element={
                session.user.role === "admin" ? (
                  <div className="panel">
                    <span className="eyebrow">KHÔNG GIAN QUẢN TRỊ</span>
                    <h1>Quản trị học phần</h1>
                    <p>
                      Khung quản trị đã sẵn sàng. Chức năng CRUD được triển khai
                      trong M1_4 theo kế hoạch.
                    </p>
                  </div>
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
  preview,
}: {
  week: number;
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
        setReason(
          "Bạn đã đáp ứng các điều kiện tiên quyết của học phần này. Tuy nhiên, chức năng đăng ký chưa được kích hoạt vì backend nhóm chưa cung cấp POST /api/v1/enroll. Không có đăng ký giả nào được tạo.",
        );
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
            Thứ học
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
          <label>
            Từ giờ
            <input
              type="time"
              value={params.get("start") || ""}
              onChange={(e) => filter("start", e.target.value)}
            />
          </label>
          <label>
            Đến giờ
            <input
              type="time"
              value={params.get("end") || ""}
              onChange={(e) => filter("end", e.target.value)}
            />
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
                      <b className="course-code">{o.code}</b>
                      <strong>{o.name}</strong>
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
                            Kiểm tra tiên quyết
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
              Hệ thống sẽ kiểm tra điều kiện tiên quyết bằng backend. Đăng ký
              thật sẽ được mở khi M3 bàn giao API.
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
                {busy ? "Đang kiểm tra…" : "Kiểm tra điều kiện"}
              </button>
            </div>
          </section>
        </div>
      )}
    </>
  );
}
function Timetable({
  regs,
  preview,
}: {
  regs: Enrollment[];
  preview: Offering | null;
}) {
  const list = [
    ...regs.map((e) => e.offering),
    ...(preview && !regs.some((e) => e.offering.id === preview.id)
      ? [preview]
      : []),
  ];
  return (
    <section className="panel">
      <div className="section-title">
        <h3>Lịch học trong tuần</h3>
        <span className="muted">● Đã đăng ký · ◌ Xem trước · ⚠ Trùng lịch</span>
      </div>
      {!list.length && (
        <p className="empty">Chưa đăng ký lớp nào trong kỳ này.</p>
      )}
      <div className="table-scroll">
        <div className="timetable">
          <div className="days">
            <span>Giờ</span>
            {[
              "Thứ Hai",
              "Thứ Ba",
              "Thứ Tư",
              "Thứ Năm",
              "Thứ Sáu",
              "Thứ Bảy",
              "Chủ nhật",
            ].map((d) => (
              <b key={d}>{d}</b>
            ))}
          </div>
          <div className="grid-body">
            {Array.from({ length: 15 }, (_, i) => (
              <div className="hour" style={{ top: i * 52 }} key={i}>
                <span>{i + 7}:00</span>
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
                    (item, index, all) =>
                      all.findIndex((other) => other.id === item.id) === index,
                  );
                return (
                  <div
                    key={o.id + "-" + i}
                    title={
                      conflict.length
                        ? "Trùng với " + conflict.map((c) => c.name).join(", ")
                        : o.name
                    }
                    className={
                      "lesson " +
                      (preview?.id === o.id ? "preview " : "") +
                      (conflict.length ? "conflict" : "")
                    }
                    style={{
                      top: ((parseTime(s.start) - 420) / 60) * 52,
                      left: `calc(52px + (100% - 52px) / 7 * ${s.day - 1} + (100% - 52px) / 7 * ${index / overlaps.length})`,
                      width: `calc((100% - 52px) / 7 / ${overlaps.length} - 5px)`,
                      height:
                        ((parseTime(s.end) - parseTime(s.start)) / 60) * 52 - 4,
                      background: ["#e7edff", "#e4f4ec", "#fff0d9", "#ede5fc"][
                        o.courseId % 4
                      ],
                    }}
                  >
                    <b>
                      {conflict.length ? "⚠ " : ""}
                      {o.code}
                    </b>
                    <span>{o.name}</span>
                    <small>
                      {s.start}–{s.end}
                    </small>
                    <small>
                      {o.room} · Lớp {o.section}
                    </small>
                  </div>
                );
              }),
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
