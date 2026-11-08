import { setupWorker } from "msw/browser";
import { http, HttpResponse } from "msw";
import { offerings, registrations, removeRegistration } from "./data";
import { findConflicts } from "../features/timetable/conflicts";

const error = (code: string, status = 409) =>
  HttpResponse.json({ detail: { code, message: code } }, { status });

export const worker = setupWorker(
  http.post("/api/v1/auth/login", async ({ request }) => {
    const body = (await request.json()) as { email: string; password: string };
    if (!body.email.includes("@") || !body.password)
      return error("UNAUTHENTICATED", 401);
    const admin = body.email.toLowerCase().startsWith("admin");
    return HttpResponse.json({
      access_token: "mock-access-token",
      refresh_token: "mock-refresh-token",
      expires_in: 1800,
      token_type: "bearer",
      user: {
        id: admin ? 999 : 1,
        email: body.email,
        full_name: admin ? "Quản trị viên" : "Nguyễn Minh Anh",
        role: admin ? "admin" : "student",
        mssv: admin ? null : "SV0001",
        max_credits: 25,
      },
    });
  }),
  http.post("/api/v1/auth/refresh", () =>
    HttpResponse.json({
      access_token: "mock-access-token-renewed",
      refresh_token: "mock-refresh-token-renewed",
      expires_in: 1800,
      token_type: "bearer",
      user: {
        id: 1,
        email: "student@uni.edu.vn",
        full_name: "Nguyễn Minh Anh",
        role: "student",
        mssv: "SV0001",
        max_credits: 25,
      },
    }),
  ),
  http.post("/api/v1/auth/logout", () =>
    HttpResponse.json({ message: "Đăng xuất thành công" }),
  ),
  http.get("/api/v1/courses", ({ request }) => {
    const params = new URL(request.url).searchParams;
    const q = (params.get("q") || "").toLowerCase();
    const section = (params.get("section") || "").toLowerCase();
    const credits = params.get("credits");
    const instructor = (params.get("instructor") || "").toLowerCase();
    const day = params.get("day");
    const start = params.get("start");
    const end = params.get("end");
    const filtered = offerings.filter(
      (item) =>
        `${item.code} ${item.name}`.toLowerCase().includes(q) &&
        item.section.toLowerCase().includes(section) &&
        (!credits || item.credits === Number(credits)) &&
        item.instructor.toLowerCase().includes(instructor) &&
        item.schedule.some(
          (slot) =>
            (!day || slot.day === Number(day)) &&
            (!start || slot.end > start) &&
            (!end || slot.start < end),
        ),
    );
    const page = Math.max(1, Number(params.get("page") || 1));
    const pageSize = Math.min(
      100,
      Math.max(1, Number(params.get("page_size") || 20)),
    );
    return HttpResponse.json({
      items: filtered.slice((page - 1) * pageSize, page * pageSize),
      total: filtered.length,
      page,
      page_size: pageSize,
    });
  }),
  http.get("/api/v1/timetable", () => HttpResponse.json(registrations)),
  http.get("/api/v1/prerequisites/check", ({ request }) => {
    const courseId = Number(new URL(request.url).searchParams.get("course_id"));
    const eligible = courseId % 4 !== 0;
    return HttpResponse.json({
      course_id: courseId,
      course_code: `INT${130 + courseId}`,
      eligible,
      missing_courses: eligible ? [] : ["INT131"],
      unmet_or_groups: eligible
        ? []
        : [{ group_no: 1, options: ["INT221", "INT231"] }],
    });
  }),
  http.post("/api/v1/prerequisites/explain", () =>
    HttpResponse.json({
      course_id: 4,
      course_code: "INT134",
      course_name: "Học phần minh họa",
      eligible: false,
      missing: [
        {
          course_code: "INT131",
          course_name: "Lập trình hướng đối tượng",
          kind: "TRANSITIVE",
          required_by: "INT132",
          path: ["INT134", "INT132", "INT131"],
        },
      ],
      unmet_or_groups: [
        {
          group_no: 1,
          required_by: "INT134",
          options: [
            {
              course_code: "INT221",
              course_name: "Cấu trúc dữ liệu",
              can_take_now: false,
              missing_courses: ["INT131"],
            },
            {
              course_code: "INT231",
              course_name: "Giải thuật",
              can_take_now: true,
              missing_courses: [],
            },
          ],
        },
      ],
      suggested_order: ["INT131", "INT132"],
      total_missing: 1,
      truncated: false,
    }),
  ),
  http.post("/api/v1/enroll", async ({ request }) => {
    const body = (await request.json()) as { offering_id: number };
    const offering = offerings.find((item) => item.id === body.offering_id);
    if (!offering) return error("NOT_FOUND", 404);
    if (registrations.some((entry) => entry.offering.id === offering.id))
      return error("ALREADY_ENROLLED");
    if (
      findConflicts(
        offering,
        registrations.map((entry) => entry.offering),
      ).length
    )
      return error("SCHEDULE_CONFLICT");
    if (offering.enrolledCount >= offering.capacity)
      return HttpResponse.json({ status: "WAITLISTED" });
    registrations.push({ id: Date.now(), offering, status: "ACTIVE" });
    offering.enrolledCount += 1;
    return HttpResponse.json({ status: "ACTIVE" }, { status: 201 });
  }),
  http.delete("/api/v1/enroll/:id", ({ params }) => {
    const id = Number(params.id);
    const entry = registrations.find((item) => item.id === id);
    if (entry)
      entry.offering.enrolledCount = Math.max(
        0,
        entry.offering.enrolledCount - 1,
      );
    removeRegistration(id);
    return new HttpResponse(null, { status: 204 });
  }),
  http.get("/api/v1/waitlist", () => HttpResponse.json([])),
  http.post("/api/v1/waitlist", async ({ request }) => {
    const body = (await request.json()) as { offering_id: number };
    const offering = offerings.find((item) => item.id === body.offering_id);
    if (!offering) return error("NOT_FOUND", 404);
    return HttpResponse.json(
      {
        id: Date.now(),
        offering_id: offering.id,
        position: 1,
        enqueued_at: new Date().toISOString(),
      },
      { status: 201 },
    );
  }),
  http.delete("/api/v1/waitlist/:id", () =>
    HttpResponse.json({ message: "Đã rời danh sách chờ" }),
  ),
  http.get("/api/v1/__mock-error/:code", ({ params }) => {
    const code = String(params.code);
    const statuses: Record<string, number> = {
      UNAUTHENTICATED: 401,
      TOKEN_EXPIRED: 401,
      FORBIDDEN: 403,
      NOT_FOUND: 404,
      PREREQ_NOT_MET: 422,
      CREDIT_LIMIT_EXCEEDED: 422,
      SCHEDULE_CONFLICT: 409,
      ALREADY_ENROLLED: 409,
      CONCURRENT_UPDATE: 409,
      RATE_LIMITED: 429,
    };
    return error(code, statuses[code] || 409);
  }),
);
