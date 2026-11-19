import { setupWorker } from "msw/browser";
import { http, HttpResponse } from "msw";
import {
  offerings,
  registrations,
  removeRegistration,
  getStaticOfferings,
} from "./data";
import { findConflicts } from "../features/timetable/conflicts";

const mockWaitlist: Array<{
  id: number;
  offeringId: number;
  position: number;
  enqueuedAt: string;
}> = [];

const error = (code: string, status = 409) =>
  HttpResponse.json({ detail: { code, message: code } }, { status });

const adminCourses = getStaticOfferings().map(
  ({ courseId, code, name, credits }) => ({
    id: courseId,
    code,
    name,
    credits,
    description: "",
  }),
);
const adminEdges: Array<{
  course_id: number;
  prereq_course_id: number;
  type: string;
  group_no: number;
}> = [];

export const worker = setupWorker(
  http.get("/api/v1/admin/courses", ({ request }) => {
    const params = new URL(request.url).searchParams;
    const q = (params.get("q") || "").toLowerCase();
    const page = Number(params.get("page") || 1);
    const size = Number(params.get("page_size") || 20);
    const items = adminCourses.filter((c) =>
      `${c.code} ${c.name}`.toLowerCase().includes(q),
    );
    return HttpResponse.json({
      items: items.slice((page - 1) * size, page * size),
      total: items.length,
      page,
      page_size: size,
    });
  }),
  http.post("/api/v1/admin/courses", async ({ request }) => {
    const body = (await request.json()) as {
      code: string;
      name: string;
      credits: number;
      description: string;
    };
    if (adminCourses.some((c) => c.code === body.code))
      return error("ALREADY_EXISTS");
    const item = {
      ...body,
      id: Math.max(...adminCourses.map((c) => c.id), 0) + 1,
    };
    adminCourses.push(item);
    return HttpResponse.json(item, { status: 201 });
  }),
  http.put("/api/v1/admin/courses/:id", async ({ request, params }) => {
    const item = adminCourses.find((c) => c.id === Number(params.id));
    if (!item) return error("NOT_FOUND", 404);
    Object.assign(item, await request.json());
    return HttpResponse.json(item);
  }),
  http.delete("/api/v1/admin/courses/:id", ({ params }) => {
    const index = adminCourses.findIndex((c) => c.id === Number(params.id));
    if (index >= 0) adminCourses.splice(index, 1);
    return HttpResponse.json({ message: "Đã xóa học phần" });
  }),
  http.get("/api/v1/admin/prereqs/:id", ({ params }) => {
    const course = adminCourses.find((c) => c.id === Number(params.id));
    if (!course) return error("NOT_FOUND", 404);
    const items = adminEdges
      .filter((e) => e.course_id === course.id)
      .map((e) => {
        const p = adminCourses.find((c) => c.id === e.prereq_course_id);
        return {
          ...e,
          prereq_code: p?.code,
          prereq_name: p?.name,
          credits: p?.credits,
        };
      });
    return HttpResponse.json({
      course_id: course.id,
      course_code: course.code,
      course_name: course.name,
      items,
      and_prerequisites: items.filter((e) => e.type === "AND"),
      or_groups: [
        ...new Set(items.filter((e) => e.type === "OR").map((e) => e.group_no)),
      ].map((group_no) => ({
        group_no,
        options: items.filter(
          (e) => e.type === "OR" && e.group_no === group_no,
        ),
      })),
    });
  }),
  http.post("/api/v1/admin/prereqs", async ({ request }) => {
    const edge = (await request.json()) as (typeof adminEdges)[number];
    const reaches = (id: number, seen = new Set<number>()): boolean => {
      if (id === edge.course_id) return true;
      if (seen.has(id)) return false;
      seen.add(id);
      return adminEdges
        .filter((e) => e.course_id === id)
        .some((e) => reaches(e.prereq_course_id, seen));
    };
    if (reaches(edge.prereq_course_id)) return error("PREREQ_CYCLE", 422);
    adminEdges.push(edge);
    return HttpResponse.json(edge, { status: 201 });
  }),
  http.delete("/api/v1/admin/prereqs/:course/:prereq", ({ params }) => {
    const index = adminEdges.findIndex(
      (e) =>
        e.course_id === Number(params.course) &&
        e.prereq_course_id === Number(params.prereq),
    );
    if (index >= 0) adminEdges.splice(index, 1);
    return HttpResponse.json({ message: "Đã xóa điều kiện" });
  }),
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
    // Course search uses the seeded catalog; use the same source here so an
    // offering id cannot resolve to a different course in the timetable.
    const offering = getStaticOfferings().find(
      (item) => item.id === body.offering_id,
    );
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
    if (offering.enrolledCount >= offering.capacity) {
      let entry = mockWaitlist.find((item) => item.offeringId === offering.id);
      if (!entry) {
        entry = {
          id: Date.now(),
          offeringId: offering.id,
          position: mockWaitlist.length + 1,
          enqueuedAt: new Date().toISOString(),
        };
        mockWaitlist.push(entry);
      }
      return HttpResponse.json({
        id: entry.id,
        offering_id: offering.id,
        status: "WAITLISTED",
        position: entry.position,
      });
    }
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
  http.get("/api/v1/waitlist", () =>
    HttpResponse.json({
      items: mockWaitlist.map((entry) => ({
        ...getStaticOfferings().find((item) => item.id === entry.offeringId),
        waitlist_id: entry.id,
        position: entry.position,
        enqueued_at: entry.enqueuedAt,
        blocked_reason: null,
        my_status: "WAITLISTED",
      })),
      total: mockWaitlist.length,
      page: 1,
      page_size: 100,
    }),
  ),
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
  http.delete("/api/v1/waitlist/:id", ({ params }) => {
    const index = mockWaitlist.findIndex(
      (entry) => entry.id === Number(params.id),
    );
    if (index >= 0) mockWaitlist.splice(index, 1);
    mockWaitlist.forEach((entry, position) => {
      entry.position = position + 1;
    });
    return HttpResponse.json({ id: Number(params.id), status: "REMOVED" });
  }),
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
