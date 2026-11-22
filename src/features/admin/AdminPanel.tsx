import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import * as api from "../../api";
import type { AdminStudyPlanSummaryResponse } from "../../types";
import { formatPrereqCycleMessage } from "../registration/helpers";

export default function AdminPanel({
  notify,
}: {
  notify: (s: string) => void;
}) {
  return (
    <div>
      <Routes>
        <Route path="courses" element={<AdminCourses notify={notify} />} />
        <Route path="prereqs" element={<AdminPrereqs notify={notify} />} />
        <Route
          path="study-plans"
          element={<AdminStudyPlans notify={notify} />}
        />
        <Route path="*" element={<Navigate to="/admin/courses" replace />} />
      </Routes>
    </div>
  );
}

function AdminCourses({ notify }: { notify: (s: string) => void }) {
  const [items, setItems] = useState<api.AdminCourse[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [editing, setEditing] = useState<api.AdminCourse | null>(null);
  const [q, setQ] = useState("");
  const pageSize = 20;

  const load = async (targetPage = page, query = q) => {
    try {
      const params = new URLSearchParams({
        page: String(targetPage),
        page_size: String(pageSize),
      });
      if (query.trim()) params.set("q", query.trim());
      const res = await api.listAdminCourses(params.toString());
      setItems(res.items);
      setTotal(res.total);
    } catch (e) {
      notify((e as Error).message);
    }
  };

  useEffect(() => {
    void load(page, q);
  }, [page, q]);

  return (
    <div>
      <div className="page-heading">
        <div>
          <h1>Quản trị học phần</h1>
          <p className="muted">
            Thêm mới, cập nhật hoặc xóa học phần trong danh mục đào tạo.
          </p>
        </div>
        <button
          className="primary"
          onClick={() =>
            setEditing({
              id: 0,
              code: "",
              name: "",
              credits: 3,
              description: "",
            })
          }
        >
          Thêm học phần
        </button>
      </div>

      <section className="panel">
        <div
          className="actions"
          style={{ marginBottom: 16, alignItems: "center" }}
        >
          <input
            aria-label="Tìm học phần quản trị"
            placeholder="Tìm theo mã hoặc tên học phần…"
            value={q}
            style={{ marginTop: 0, maxWidth: 420 }}
            onChange={(e) => {
              setQ(e.target.value);
              setPage(1);
            }}
          />
          <span className="muted" style={{ marginLeft: "auto" }}>
            Tổng {total} học phần
          </span>
        </div>

        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Mã môn</th>
                <th>Tên học phần</th>
                <th>Tín chỉ</th>
                <th style={{ width: 160 }}>Thao tác</th>
              </tr>
            </thead>
            <tbody>
              {items.map((c) => (
                <tr key={c.id}>
                  <td>
                    <b className="mono-id">{c.code}</b>
                  </td>
                  <td>{c.name}</td>
                  <td>{c.credits}</td>
                  <td>
                    <div className="actions">
                      <button
                        type="button"
                        className="btn-outline"
                        onClick={() => setEditing(c)}
                      >
                        Sửa
                      </button>
                      <button
                        type="button"
                        className="btn-danger-soft"
                        onClick={async () => {
                          if (
                            window.confirm(`Bạn có chắc muốn xóa ${c.code}?`)
                          ) {
                            try {
                              await api.deleteAdminCourse(c.id);
                              await load(page, q);
                              notify("Đã xóa học phần");
                            } catch (e) {
                              notify((e as Error).message);
                            }
                          }
                        }}
                      >
                        Xóa
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="pagination">
          <span className="muted">
            Trang {page} / {Math.max(1, Math.ceil(total / pageSize))}
          </span>
          <button
            type="button"
            className="btn-outline"
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
          >
            Trước
          </button>
          <b>{page}</b>
          <button
            type="button"
            className="btn-outline"
            disabled={page * pageSize >= total}
            onClick={() => setPage((p) => p + 1)}
          >
            Sau
          </button>
        </div>
      </section>

      {editing && (
        <CourseForm
          value={editing}
          close={() => setEditing(null)}
          save={async (data) => {
            try {
              if (editing.id) await api.updateAdminCourse(editing.id, data);
              else await api.createAdminCourse(data);
              setEditing(null);
              await load(page, q);
              notify("Đã lưu học phần");
            } catch (e) {
              notify((e as Error).message);
            }
          }}
        />
      )}
    </div>
  );
}

function AdminPrereqs({ notify }: { notify: (s: string) => void }) {
  const [courses, setCourses] = useState<api.AdminCourse[]>([]);
  const [courseId, setCourseId] = useState(0);
  const [data, setData] = useState<api.AdminCoursePrereqsResponse | null>(null);
  const [busy, setBusy] = useState(false);

  const courseCodeById = useMemo(
    () => new Map(courses.map((c) => [c.id, c.code])),
    [courses],
  );

  const load = async (id: number) => {
    setCourseId(id);
    if (!id) return setData(null);
    try {
      setData(await api.getAdminCoursePrerequisites(id));
    } catch (e) {
      notify((e as Error).message);
    }
  };

  useEffect(() => {
    let active = true;
    async function loadAllCourses() {
      try {
        const all: api.AdminCourse[] = [];
        let page = 1;
        let total = 1;
        while (all.length < total && page <= 10) {
          const res = await api.listAdminCourses(`page=${page}&page_size=100`);
          all.push(...res.items);
          total = res.total;
          if (!res.items.length) break;
          page += 1;
        }
        if (active) setCourses(all);
      } catch (e) {
        if (active) notify((e as Error).message);
      }
    }
    void loadAllCourses();
    return () => {
      active = false;
    };
  }, []);

  async function add(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const prereq = Number(f.get("prereq"));
    const type = String(f.get("type")) as "AND" | "OR";
    const groupNo = type === "OR" ? Number(f.get("groupNo") || 1) : 0;
    if (!courseId || !prereq || courseId === prereq) {
      return notify("Hãy chọn hai học phần khác nhau.");
    }
    setBusy(true);
    try {
      await api.createAdminPrerequisite({
        courseId,
        prereqCourseId: prereq,
        type,
        groupNo,
      });
      await load(courseId);
      notify("Đã thêm điều kiện tiên quyết");
    } catch (e) {
      const err = e as {
        code?: string;
        message?: string;
        details?: { cyclePath?: unknown };
      };
      notify(
        err.code === "PREREQ_CYCLE"
          ? formatPrereqCycleMessage(err.details?.cyclePath, courseCodeById)
          : err.message || "Không thể lưu điều kiện tiên quyết",
      );
    } finally {
      setBusy(false);
    }
  }

  const remove = async (prereq: number) => {
    try {
      await api.deleteAdminPrerequisite(courseId, prereq);
      await load(courseId);
      notify("Đã xóa điều kiện tiên quyết");
    } catch (e) {
      notify((e as Error).message);
    }
  };

  return (
    <div>
      <div className="page-heading">
        <div>
          <h1>Cấu hình điều kiện tiên quyết</h1>
          <p className="muted">
            Thiết lập môn bắt buộc (AND) hoặc nhóm môn thay thế (OR) cho từng
            học phần. Hệ thống tự động chặn chu trình trên đồ thị DAG.
          </p>
        </div>
        <span className="pill">{courses.length} học phần</span>
      </div>

      <section className="panel" style={{ marginBottom: 20 }}>
        <label style={{ maxWidth: 520 }}>
          Chọn học phần cần cấu hình
          <select
            value={courseId}
            onChange={(e) => void load(Number(e.target.value))}
          >
            <option value={0}>-- Chọn học phần --</option>
            {courses.map((c) => (
              <option key={c.id} value={c.id}>
                {c.code} — {c.name}
              </option>
            ))}
          </select>
        </label>
      </section>

      {data && (
        <>
          <section className="panel" style={{ marginBottom: 20 }}>
            <div className="section-title">
              <h3>
                <span className="mono-id">{data.courseCode}</span> — Điều kiện
                tiên quyết hiện tại
              </h3>
            </div>

            <div style={{ marginBottom: 20 }}>
              <h4 style={{ marginBottom: 10 }}>Môn bắt buộc (AND)</h4>
              {data.andPrerequisites.length ? (
                data.andPrerequisites.map((p) => (
                  <div className="enrolled" key={p.prereqCourseId}>
                    <div>
                      <b className="mono-id" style={{ marginRight: 10 }}>
                        {p.prereqCode}
                      </b>
                      <span>{p.prereqName}</span>
                    </div>
                    <button
                      type="button"
                      className="btn-danger-soft"
                      onClick={() => void remove(p.prereqCourseId)}
                    >
                      Xóa
                    </button>
                  </div>
                ))
              ) : (
                <p className="muted">Chưa có môn tiên quyết bắt buộc.</p>
              )}
            </div>

            {data.orGroups.map((g) => (
              <div key={g.groupNo} style={{ marginTop: 18 }}>
                <h4 style={{ marginBottom: 10 }}>
                  Nhóm lựa chọn thay thế (OR nhóm {g.groupNo})
                </h4>
                {g.options.map((p) => (
                  <div className="enrolled" key={p.prereqCourseId}>
                    <div>
                      <b className="mono-id" style={{ marginRight: 10 }}>
                        {p.prereqCode}
                      </b>
                      <span>{p.prereqName}</span>
                    </div>
                    <button
                      type="button"
                      className="btn-danger-soft"
                      onClick={() => void remove(p.prereqCourseId)}
                    >
                      Xóa
                    </button>
                  </div>
                ))}
              </div>
            ))}
          </section>

          <section className="panel">
            <h3 style={{ marginBottom: 14 }}>Thêm điều kiện tiên quyết mới</h3>
            <form
              onSubmit={add}
              style={{
                display: "grid",
                gridTemplateColumns:
                  "minmax(240px, 2fr) minmax(110px, 140px) minmax(110px, 140px) auto",
                gap: 12,
                alignItems: "end",
              }}
            >
              <label>
                Học phần tiên quyết
                <select name="prereq" required defaultValue="">
                  <option value="">-- Chọn học phần --</option>
                  {courses
                    .filter((c) => c.id !== courseId)
                    .map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.code} — {c.name}
                      </option>
                    ))}
                </select>
              </label>
              <label>
                Loại ràng buộc
                <select name="type" defaultValue="AND">
                  <option value="AND">AND (bắt buộc)</option>
                  <option value="OR">OR (thay thế)</option>
                </select>
              </label>
              <label>
                Số nhóm OR
                <input
                  name="groupNo"
                  type="number"
                  min="1"
                  defaultValue="1"
                  placeholder="1"
                />
              </label>
              <button
                className="primary"
                disabled={busy}
                style={{ height: 42, padding: "0 20px" }}
              >
                {busy ? "Đang lưu…" : "Thêm điều kiện"}
              </button>
            </form>
          </section>
        </>
      )}
    </div>
  );
}

function CourseForm({
  value,
  close,
  save,
}: {
  value: api.AdminCourse;
  close: () => void;
  save: (data: Omit<api.AdminCourse, "id">) => Promise<void>;
}) {
  const [form, setForm] = useState({
    code: value.code,
    name: value.name,
    credits: value.credits,
    description: value.description || "",
  });
  return (
    <div
      className="modal-backdrop"
      onClick={(e) => {
        if (e.target === e.currentTarget) close();
      }}
    >
      <form
        className="modal"
        role="dialog"
        aria-modal="true"
        onSubmit={(e) => {
          e.preventDefault();
          void save(form);
        }}
      >
        <h2>{value.id ? "Cập nhật học phần" : "Thêm học phần mới"}</h2>
        <div style={{ display: "grid", gap: 14, marginTop: 14 }}>
          <label>
            Mã học phần
            <input
              required
              placeholder="Ví dụ: INT321"
              value={form.code}
              onChange={(e) => setForm({ ...form, code: e.target.value })}
            />
          </label>
          <label>
            Tên học phần
            <input
              required
              placeholder="Nhập tên học phần"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
          </label>
          <label>
            Số tín chỉ
            <input
              required
              type="number"
              min="1"
              max="10"
              value={form.credits}
              onChange={(e) =>
                setForm({ ...form, credits: Number(e.target.value) })
              }
            />
          </label>
          <label>
            Mô tả học phần
            <textarea
              placeholder="Mô tả ngắn gọn nội dung học phần"
              value={form.description}
              onChange={(e) =>
                setForm({ ...form, description: e.target.value })
              }
            />
          </label>
        </div>
        <div className="actions">
          <button type="button" className="btn-outline" onClick={close}>
            Đóng
          </button>
          <button className="primary">Lưu học phần</button>
        </div>
      </form>
    </div>
  );
}

function AdminStudyPlans({ notify }: { notify: (s: string) => void }) {
  const [summary, setSummary] = useState<AdminStudyPlanSummaryResponse | null>(
    null,
  );
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [q, setQ] = useState("");
  const [minThreshold, setMinThreshold] = useState(15);
  const [busy, setBusy] = useState(false);

  const load = async (st = statusFilter) => {
    setLoading(true);
    try {
      const res = await api.getAdminStudyPlanSummary(undefined, st);
      setSummary(res);
      setMinThreshold(res.minRequired);
    } catch (e) {
      notify((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load(statusFilter);
  }, [statusFilter]);

  const filtered = useMemo(() => {
    if (!summary) return [];
    const kw = q.trim().toLowerCase();
    if (!kw) return summary.items;
    return summary.items.filter(
      (i) =>
        i.code.toLowerCase().includes(kw) ||
        i.name.toLowerCase().includes(kw) ||
        (i.faculty || "").toLowerCase().includes(kw),
    );
  }, [summary, q]);

  const handleFinalize = async () => {
    if (
      !window.confirm(
        `Chốt quyết định mở lớp kỳ ${summary?.term || "2026-2"} với ngưỡng tối thiểu ${minThreshold} sinh viên ĐKKHHT?`,
      )
    ) {
      return;
    }
    setBusy(true);
    try {
      const res = await api.finalizeAdminStudyPlans(
        minThreshold,
        summary?.term,
      );
      notify(
        `Đã chốt mở lớp kỳ ${res.term}: ${res.openedCourses} môn mở lớp, ${res.notOpenedCourses} môn không mở lớp, tạo mới ${res.createdOfferings} lớp.`,
      );
      await load(statusFilter);
    } catch (e) {
      notify((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <div className="page-heading">
        <div>
          <h1>Nhu cầu ĐKKHHT & Chốt mở lớp</h1>
          <p className="muted">
            Thống kê số lượng sinh viên đã đăng ký Kế hoạch học tập từng môn để
            quyết định mở lớp hoặc hủy mở lớp khi không đủ sĩ số tối thiểu.
          </p>
        </div>
        {summary && <span className="code-badge">Học kỳ {summary.term}</span>}
      </div>

      {summary && (
        <div className="metric-strip" style={{ marginBottom: 20 }}>
          <div className="metric-cell">
            <span className="metric-label">Tổng lượt ĐKKHHT</span>
            <strong className="metric-value">{summary.totalPlans}</strong>
            <small>nguyện vọng học phần</small>
          </div>
          <div className="metric-cell">
            <span className="metric-label">Môn đủ sĩ số mở lớp</span>
            <strong className="metric-value" style={{ color: "#047857" }}>
              {summary.openedCourses}
            </strong>
            <small>đạt ≥ {summary.minRequired} sinh viên</small>
          </div>
          <div className="metric-cell">
            <span className="metric-label">Môn không mở lớp</span>
            <strong className="metric-value" style={{ color: "#d71920" }}>
              {summary.notOpenedCourses}
            </strong>
            <small>thiếu sĩ số tối thiểu</small>
          </div>
          <div className="metric-cell">
            <span className="metric-label">Tổng lớp học phần đang mở</span>
            <strong className="metric-value">{summary.totalOfferings}</strong>
            <small>kỳ {summary.term}</small>
          </div>
        </div>
      )}

      <section className="panel" style={{ marginBottom: 20 }}>
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: 14,
            alignItems: "flex-end",
            justifyContent: "space-between",
          }}
        >
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap", flex: 1 }}>
            <label style={{ minWidth: 240, flex: 1, maxWidth: 360 }}>
              Tìm học phần hoặc khoa
              <input
                placeholder="Mã môn, tên môn hoặc khoa…"
                value={q}
                onChange={(e) => setQ(e.target.value)}
              />
            </label>
            <label style={{ width: 200 }}>
              Trạng thái mở lớp
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <option value="ALL">Tất cả trạng thái</option>
                <option value="OPENED">Đủ sĩ số (Đã mở lớp)</option>
                <option value="NOT_OPENED">Thiếu sĩ số (Không mở lớp)</option>
                <option value="PENDING">Chờ duyệt</option>
              </select>
            </label>
          </div>

          <div
            style={{
              display: "flex",
              gap: 10,
              alignItems: "flex-end",
              flexWrap: "wrap",
            }}
          >
            <label style={{ width: 170 }}>
              Ngưỡng tối thiểu (SV)
              <input
                type="number"
                min="1"
                max="200"
                value={minThreshold}
                onChange={(e) => setMinThreshold(Number(e.target.value) || 15)}
              />
            </label>
            <button
              type="button"
              className="btn-tdtu-red"
              disabled={busy}
              style={{ height: 42 }}
              onClick={() => void handleFinalize()}
            >
              {busy ? "Đang chốt…" : "Chốt mở lớp theo ngưỡng"}
            </button>
          </div>
        </div>
      </section>

      <section className="panel">
        <div className="section-title">
          <h3>
            Danh sách học phần theo nhu cầu ĐKKHHT ({filtered.length} môn)
          </h3>
        </div>
        {loading ? (
          <div className="skeleton">Đang tải thống kê nhu cầu ĐKKHHT…</div>
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Mã môn</th>
                  <th>Tên học phần</th>
                  <th>Khoa / Nhóm</th>
                  <th>TC</th>
                  <th>Số SV ĐKKHHT</th>
                  <th>Trạng thái mở lớp</th>
                  <th>Lớp mở / Đề xuất</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((item) => {
                  const pct = Math.min(
                    100,
                    Math.round((item.plannedCount / item.minRequired) * 100),
                  );
                  return (
                    <tr key={item.courseId}>
                      <td>
                        <b className="mono-id">{item.code}</b>
                      </td>
                      <td>{item.name}</td>
                      <td className="muted">{item.faculty}</td>
                      <td>{item.credits}</td>
                      <td>
                        <div style={{ fontWeight: 700, fontSize: 12.5 }}>
                          {item.plannedCount} / {item.minRequired} SV
                        </div>
                        <div className="capacity" style={{ width: 100 }}>
                          <i
                            style={{
                              width: `${pct}%`,
                              background:
                                item.status === "NOT_OPENED"
                                  ? "#d71920"
                                  : "#004b91",
                            }}
                          />
                        </div>
                      </td>
                      <td>
                        {item.status === "OPENED" ? (
                          <span
                            style={{
                              fontSize: 11,
                              fontWeight: 700,
                              padding: "3px 8px",
                              background: "#ecfdf5",
                              color: "#047857",
                            }}
                          >
                            Đã mở lớp
                          </span>
                        ) : item.status === "NOT_OPENED" ? (
                          <span
                            style={{
                              fontSize: 11,
                              fontWeight: 700,
                              padding: "3px 8px",
                              background: "#fdecee",
                              color: "#d71920",
                            }}
                          >
                            Không mở lớp
                          </span>
                        ) : (
                          <span className="pill">Chờ chốt</span>
                        )}
                      </td>
                      <td>
                        <b>{item.offeringsCount}</b> lớp{" "}
                        <span className="muted">
                          (đề xuất {item.recommendedSections})
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
