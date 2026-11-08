import { ApiError } from "./http";

// Chưa có POST /enroll và DELETE /enroll/{id} trong backend nhóm hiện tại.
// Không gửi request và không giả lập đăng ký thành công.
export function enroll(_offeringId: number, _idempotencyKey: string): never {
  void _offeringId;
  void _idempotencyKey;
  throw new ApiError(
    "FEATURE_PENDING",
    "Chức năng đăng ký đang chờ API POST /api/v1/enroll từ M3.",
    501,
  );
}

export function cancel(_enrollmentId: number): never {
  void _enrollmentId;
  throw new ApiError(
    "FEATURE_PENDING",
    "Chức năng hủy đăng ký đang chờ API DELETE /api/v1/enroll/{id} từ M3.",
    501,
  );
}
