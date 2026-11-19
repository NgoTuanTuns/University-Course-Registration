import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import * as api from "../../api";
import { formatPrereqCycleMessage } from "../registration/helpers";

export default function AdminPanel({
  notify,
}: {
  notify: (s: string) => void;
}) {
  return (
    <div className="panel">
      <span className="eyebrow">KHÔNG GIAN QUẢN TRỊ</span>
      <h1>Quản trị hệ thống</h1>
      <Routes>
        <Route path="courses" element={<AdminCourses notify={notify} />} />
        <Route path="prereqs" element={<AdminPrereqs notify={notify} />} />
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
      <div className="actions" style={{ marginBottom: 16 }}>
        <input
          aria-label="Tìm học phần quản trị"
          placeholder="Tìm theo mã hoặc tên học phần…"
          value={q}
          onChange={(e) => {
            setQ(e.target.value);
            setPage(1);
          }}
        />
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
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Mã</th>
              <th>Tên học phần</th>
              <th>Tín chỉ</th>
              <th>Thao tác</th>
            </tr>
          </thead>
          <tbody>
            {items.map((c) => (
              <tr key={c.id}>
                <td>
                  <b>{c.code}</b>
                </td>
                <td>{c.name}</td>
                <td>{c.credits}</td>
                <td>
                  <button onClick={() => setEditing(c)}>Sửa</button>{" "}
                  <button
                    onClick={async () => {
                      if (window.confirm(`Bạn có chắc muốn xóa ${c.code}?`)) {
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
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="pagination">
        <span className="muted">Tổng {total} học phần</span>
        <button
          disabled={page <= 1}
          onClick={() => setPage((p) => Math.max(1, p - 1))}
        >
          ← Trước
        </button>
        <b>{page}</b>
        <button
          disabled={page * pageSize >= total}
          onClick={() => setPage((p) => p + 1)}
        >
          Sau →
        </button>
      </div>
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
      <p className="muted">
        Dữ liệu seed được thực hiện bằng lệnh <code>python -m app.seed</code>;
        hiện chưa có endpoint seed cho giao diện.
      </p>
      <label>
        Chọn học phần ({courses.length} môn)
        <select
          value={courseId}
          onChange={(e) => void load(Number(e.target.value))}
        >
          <option value={0}>-- Chọn --</option>
          {courses.map((c) => (
            <option key={c.id} value={c.id}>
              {c.code} · {c.name}
            </option>
          ))}
        </select>
      </label>
      {data && (
        <>
          <h3>{data.courseCode} · Điều kiện tiên quyết</h3>
          <div className="panel">
            <b>AND — bắt buộc</b>
            {data.andPrerequisites.length ? (
              data.andPrerequisites.map((p) => (
                <div className="enrolled" key={p.prereqCourseId}>
                  {p.prereqCode} · {p.prereqName}
                  <button onClick={() => void remove(p.prereqCourseId)}>
                    Xóa
                  </button>
                </div>
              ))
            ) : (
              <p className="muted">Không có.</p>
            )}
            {data.orGroups.map((g) => (
              <div key={g.groupNo}>
                <b>OR nhóm {g.groupNo}</b>
                {g.options.map((p) => (
                  <div className="enrolled" key={p.prereqCourseId}>
                    {p.prereqCode} · {p.prereqName}
                    <button onClick={() => void remove(p.prereqCourseId)}>
                      Xóa
                    </button>
                  </div>
                ))}
              </div>
            ))}
          </div>
          <form className="panel actions" onSubmit={add}>
            <select name="prereq" required defaultValue="">
              <option value="">Điều kiện mới</option>
              {courses
                .filter((c) => c.id !== courseId)
                .map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.code} · {c.name}
                  </option>
                ))}
            </select>
            <select name="type" defaultValue="AND">
              <option value="AND">AND</option>
              <option value="OR">OR</option>
            </select>
            <input
              name="groupNo"
              type="number"
              min="1"
              defaultValue="1"
              placeholder="Số nhóm OR"
            />
            <button className="primary" disabled={busy}>
              {busy ? "Đang lưu…" : "Thêm"}
            </button>
          </form>
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
    <div className="modal-backdrop">
      <form
        className="modal"
        role="dialog"
        aria-modal="true"
        onSubmit={(e) => {
          e.preventDefault();
          void save(form);
        }}
      >
        <h2>{value.id ? "Sửa học phần" : "Thêm học phần"}</h2>
        <input
          required
          placeholder="Mã học phần"
          value={form.code}
          onChange={(e) => setForm({ ...form, code: e.target.value })}
        />
        <input
          required
          placeholder="Tên học phần"
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
        />
        <input
          required
          type="number"
          min="1"
          max="10"
          placeholder="Tín chỉ"
          value={form.credits}
          onChange={(e) =>
            setForm({ ...form, credits: Number(e.target.value) })
          }
        />
        <textarea
          placeholder="Mô tả"
          value={form.description}
          onChange={(e) => setForm({ ...form, description: e.target.value })}
        />
        <div className="actions">
          <button type="button" onClick={close}>
            Đóng
          </button>
          <button className="primary">Lưu</button>
        </div>
      </form>
    </div>
  );
}
