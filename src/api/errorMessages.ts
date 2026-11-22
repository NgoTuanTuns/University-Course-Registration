export const messages: Record<string, string> = {
  UNAUTHENTICATED: "Vui lòng đăng nhập lại.",
  TOKEN_EXPIRED: "Phiên đăng nhập đã hết hạn.",
  FORBIDDEN: "Bạn không có quyền thực hiện thao tác này.",
  NOT_FOUND: "Không tìm thấy dữ liệu yêu cầu.",
  PREREQ_NOT_MET: "Bạn chưa hoàn thành điều kiện tiên quyết.",
  MIN_ACCUMULATED_CREDITS_NOT_MET:
    "Bạn chưa đạt số tín chỉ tích lũy tối thiểu cho học phần này.",
  STUDY_PLAN_PERIOD_CLOSED:
    "Đợt Đăng ký Kế hoạch học tập đã kết thúc. Không thể thêm hoặc xóa học phần.",
  REGISTRATION_PHASE_CLOSED:
    "Cổng đăng ký học phần hiện đang đóng theo lịch điều hành của Phòng Đào tạo.",
  INVALID_PHASE: "Giai đoạn đợt đăng ký không hợp lệ.",
  COURSE_NOT_OPENED:
    "Học phần này không mở lớp trong học kỳ do không đủ số lượng sinh viên ĐKKHHT.",
  FACULTY_MISMATCH:
    "Học phần này không thuộc chương trình đào tạo của khoa bạn.",
  CREDIT_LIMIT_EXCEEDED: "Thao tác vượt quá hạn mức tín chỉ.",
  MAX_CREDITS_EXCEEDED: "Thao tác vượt quá hạn mức tín chỉ học kỳ.",
  SCHEDULE_CONFLICT: "Học phần bị trùng lịch với lớp đã chọn.",
  SECTION_FULL:
    "Lớp học phần đích đã hết chỗ. Lớp cũ của bạn vẫn được giữ nguyên.",
  SAME_SECTION: "Bạn đang đăng ký chính lớp học phần này.",
  DIFFERENT_COURSE: "Chỉ được phép đổi giữa các lớp thuộc cùng một học phần.",
  DIFFERENT_TERM: "Chỉ được phép đổi sang lớp học phần thuộc cùng học kỳ.",
  ENROLLMENT_NOT_ACTIVE:
    "Chỉ có thể đổi lớp đối với học phần đang ở trạng thái đã đăng ký.",
  ALREADY_ENROLLED: "Bạn đã đăng ký học phần này.",
  CONCURRENT_UPDATE: "Dữ liệu vừa thay đổi. Vui lòng tải lại và thử lại.",
  RATE_LIMITED: "Bạn thao tác quá nhanh. Vui lòng thử lại sau.",
  ALREADY_EXISTS: "Mã học phần đã tồn tại.",
  IN_USE: "Học phần đang được sử dụng nên không thể xóa.",
  INTERNAL_ERROR: "Hệ thống đang gặp sự cố. Vui lòng thử lại sau.",
  NETWORK_ERROR: "Không thể kết nối máy chủ. Kiểm tra mạng và thử lại.",
  FEATURE_PENDING: "Chức năng đang chờ API backend được bàn giao.",
};
