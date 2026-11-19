import { useEffect, useMemo, useState } from "react";
import * as api from "../../api";
import type { AcademicRecordResponse } from "../../types";

function toLetterGrade(grade: number | null): string {
  if (grade === null) return "—";
  if (grade >= 8.5) return "A";
  if (grade >= 8.0) return "B+";
  if (grade >= 7.0) return "B";
  if (grade >= 6.5) return "C+";
  if (grade >= 5.5) return "C";
  if (grade >= 5.0) return "D+";
  return "D";
}

export default function AcademicRecordView({
  notify,
}: {
  notify: (s: string) => void;
}) {
  const [record, setRecord] = useState<AcademicRecordResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [termFilter, setTermFilter] = useState("ALL");
  const [q, setQ] = useState("");

  useEffect(() => {
    let active = true;
    setLoading(true);
    void api
      .getAcademicRecord()
      .then((res) => {
        if (active) setRecord(res);
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

  const terms = useMemo(() => {
    if (!record) return [];
    return Array.from(
      new Set(
        record.completedCourses
          .map((c) => c.term)
          .filter((t): t is string => Boolean(t)),
      ),
    ).sort();
  }, [record]);

  const filtered = useMemo(() => {
    if (!record) return [];
    const keyword = q.trim().toLowerCase();
    return record.completedCourses.filter((c) => {
      if (termFilter !== "ALL" && c.term !== termFilter) return false;
      if (
        keyword &&
        !c.code.toLowerCase().includes(keyword) &&
        !c.name.toLowerCase().includes(keyword)
      ) {
        return false;
      }
      return true;
    });
  }, [record, termFilter, q]);

  return (
    <div>
      <div className="page-heading">
        <div>
          <div className="eyebrow">TIẾN ĐỘ TÍCH LŨY</div>
          <h1>Hồ sơ học tập & Môn đã hoàn thành</h1>
          <p className="muted">
            Tổng hợp số tín chỉ tích lũy và danh sách các học phần bạn đã đạt để
            làm cơ sở kiểm tra điều kiện tiên quyết.
          </p>
        </div>
        {record?.mssv && <span className="pill">MSSV: {record.mssv}</span>}
      </div>

      {loading ? (
        <div className="skeleton">Đang tải hồ sơ học tập…</div>
      ) : !record ? (
        <div className="panel empty">Không thể tải dữ liệu hồ sơ học tập.</div>
      ) : (
        <>
          <div className="stats" style={{ marginBottom: 20 }}>
            <article>
              <span>Tín chỉ tích lũy</span>
              <strong>{record.accumulatedCredits}</strong>
              <small>tín chỉ đã hoàn thành</small>
            </article>
            <article>
              <span>Điểm trung bình (GPA)</span>
              <strong>{record.gpa.toFixed(2)}</strong>
              <small>thang điểm 10</small>
            </article>
            <article>
              <span>Số môn đã đạt</span>
              <strong>{record.completedCount}</strong>
              <small>học phần tích lũy</small>
            </article>
            <article>
              <span>Khoa / Ngành</span>
              <strong style={{ fontSize: 16 }}>
                {record.faculty || "Chưa cập nhật"}
              </strong>
              <small>
                {record.program || "Đại học"} · Hạn mức kỳ: {record.maxCredits}{" "}
                TC
              </small>
            </article>
          </div>

          <section className="panel">
            <div className="section-title">
              <h3>Danh sách môn học đã hoàn thành ({filtered.length})</h3>
              <div className="actions">
                <input
                  placeholder="Tìm mã hoặc tên môn…"
                  value={q}
                  onChange={(e) => setQ(e.target.value)}
                />
                <select
                  aria-label="Lọc theo học kỳ"
                  value={termFilter}
                  onChange={(e) => setTermFilter(e.target.value)}
                >
                  <option value="ALL">Tất cả học kỳ</option>
                  {terms.map((t) => (
                    <option key={t} value={t}>
                      Học kỳ {t}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {!filtered.length ? (
              <p className="empty">
                {record.completedCount === 0
                  ? "Bạn chưa hoàn thành học phần nào (Tân sinh viên 0 tín chỉ tích lũy — có thể đăng ký các môn năm nhất yêu cầu 0 TC)."
                  : "Không tìm thấy học phần phù hợp với bộ lọc."}
              </p>
            ) : (
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Mã môn</th>
                      <th>Tên học phần</th>
                      <th>Tín chỉ</th>
                      <th>Điểm số</th>
                      <th>Điểm chữ</th>
                      <th>Học kỳ đạt</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.map((c) => (
                      <tr key={c.courseId}>
                        <td>
                          <b>{c.code}</b>
                        </td>
                        <td>{c.name}</td>
                        <td>{c.credits}</td>
                        <td>{c.grade !== null ? c.grade.toFixed(1) : "—"}</td>
                        <td>
                          <span className="pill">{toLetterGrade(c.grade)}</span>
                        </td>
                        <td>{c.term || "—"}</td>
                      </tr>
                    ))}
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
