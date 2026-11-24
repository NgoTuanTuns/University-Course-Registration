import { ReceiptText, Printer } from "lucide-react";
import { formatVnd, type TuitionEstimate } from "../api/tuition";

export function TuitionPanel({
  tuition,
  id,
}: {
  tuition: TuitionEstimate | null;
  id?: string;
}) {
  if (!tuition) return null;

  const deadlineText = tuition.paymentDeadline
    ? new Date(`${tuition.paymentDeadline}T00:00:00`).toLocaleDateString(
        "vi-VN",
      )
    : "—";

  return (
    <section className="panel" id={id} style={{ marginTop: 18 }}>
      <div className="section-title">
        <h3>
          <ReceiptText size={16} /> Bảng kê học phí tạm tính — Học kỳ{" "}
          {tuition.term}
        </h3>
        <div className="actions" style={{ marginTop: 0, alignItems: "center" }}>
          <span className="pill">Hạn đóng dự kiến: {deadlineText}</span>
          <button
            type="button"
            className="btn-outline"
            onClick={() => window.print()}
          >
            <Printer size={14} /> In phiếu tạm tính
          </button>
        </div>
      </div>

      <div className="metric-strip" style={{ marginBottom: 16 }}>
        <div className="metric-cell" style={{ cursor: "default" }}>
          <span className="metric-label">Tổng học phí tạm tính</span>
          <strong
            className="metric-value"
            style={{ color: "var(--red)", fontSize: 22 }}
          >
            {formatVnd(tuition.totalAmount)}
          </strong>
          <small>
            {tuition.totalCourses} học phần · {tuition.totalCredits} tín chỉ
          </small>
        </div>
        <div className="metric-cell" style={{ cursor: "default" }}>
          <span className="metric-label">Học phí theo tín chỉ</span>
          <strong className="metric-value" style={{ fontSize: 22 }}>
            {formatVnd(tuition.tuitionSubtotal)}
          </strong>
          <small>Đơn giá theo nhóm môn học</small>
        </div>
        <div className="metric-cell" style={{ cursor: "default" }}>
          <span className="metric-label">Phụ phí thực hành / phòng máy</span>
          <strong className="metric-value" style={{ fontSize: 22 }}>
            {formatVnd(tuition.labFeeTotal)}
          </strong>
          <small>Áp dụng nhóm chuyên ngành Công nghệ & Kỹ thuật</small>
        </div>
      </div>

      {!tuition.items.length ? (
        <p className="empty" style={{ padding: "18px 12px" }}>
          Bạn chưa đăng ký lớp học phần nào trong Học kỳ {tuition.term}. Học phí
          tạm tính sẽ tự động cập nhật ngay khi bạn đăng ký môn.
        </p>
      ) : (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Mã môn</th>
                <th>Tên học phần</th>
                <th>Lớp</th>
                <th>Nhóm đơn giá</th>
                <th>TC</th>
                <th style={{ textAlign: "right" }}>Đơn giá / TC</th>
                <th style={{ textAlign: "right" }}>Phụ phí</th>
                <th style={{ textAlign: "right" }}>Thành tiền</th>
              </tr>
            </thead>
            <tbody>
              {tuition.items.map((item) => (
                <tr key={item.enrollmentId}>
                  <td>
                    <b className="mono-id">{item.courseCode}</b>
                  </td>
                  <td>
                    <strong>{item.courseName}</strong>
                  </td>
                  <td>Lớp {item.section}</td>
                  <td>
                    <small className="muted">{item.category}</small>
                  </td>
                  <td>
                    <span className="credit">{item.credits}</span>
                  </td>
                  <td
                    style={{
                      textAlign: "right",
                      fontVariantNumeric: "tabular-nums",
                    }}
                  >
                    {formatVnd(item.unitPrice)}
                  </td>
                  <td
                    style={{
                      textAlign: "right",
                      fontVariantNumeric: "tabular-nums",
                    }}
                  >
                    {item.labFee > 0 ? formatVnd(item.labFee) : "—"}
                  </td>
                  <td
                    style={{
                      textAlign: "right",
                      fontWeight: 700,
                      fontVariantNumeric: "tabular-nums",
                    }}
                  >
                    {formatVnd(item.subtotal)}
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr style={{ background: "var(--soft)" }}>
                <td colSpan={4} style={{ fontWeight: 700 }}>
                  Tổng cộng học phí tạm tính kỳ {tuition.term}
                </td>
                <td style={{ fontWeight: 700 }}>{tuition.totalCredits}</td>
                <td
                  style={{
                    textAlign: "right",
                    fontWeight: 600,
                    fontVariantNumeric: "tabular-nums",
                  }}
                >
                  {formatVnd(tuition.tuitionSubtotal)}
                </td>
                <td
                  style={{
                    textAlign: "right",
                    fontWeight: 600,
                    fontVariantNumeric: "tabular-nums",
                  }}
                >
                  {tuition.labFeeTotal > 0
                    ? formatVnd(tuition.labFeeTotal)
                    : "—"}
                </td>
                <td
                  style={{
                    textAlign: "right",
                    fontWeight: 800,
                    color: "var(--red)",
                    fontSize: 14.5,
                    fontVariantNumeric: "tabular-nums",
                  }}
                >
                  {formatVnd(tuition.totalAmount)}
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      )}
    </section>
  );
}
