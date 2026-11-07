import type { Session } from "../types";
import { messages } from "./errorMessages";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api/v1";
let refreshPromise: Promise<void> | null = null;

export const mockMode = import.meta.env.DEV && import.meta.env.VITE_USE_MOCK === "true";

function toCamel(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(toCamel);
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value).map(([key, child]) => [
        key.replace(/_([a-z])/g, (_, letter: string) => letter.toUpperCase()),
        toCamel(child),
      ]),
    );
  }
  return value;
}

function toSnake(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(toSnake);
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value).map(([key, child]) => [
        key.replace(/[A-Z]/g, (letter) => `_${letter.toLowerCase()}`),
        toSnake(child),
      ]),
    );
  }
  return value;
}

export class ApiError extends Error {
  code: string;
  status: number;
  retryAfter?: number;

  constructor(code: string, message: string, status: number, retryAfter?: number) {
    super(message || code);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
    this.retryAfter = retryAfter;
  }
}

export function getSession(): Session | null {
  const raw = sessionStorage.getItem("m1_session");
  if (!raw) return null;
  try {
    return JSON.parse(raw) as Session;
  } catch {
    sessionStorage.removeItem("m1_session");
    return null;
  }
}

export function setSession(session: Session | null): void {
  if (!session) {
    sessionStorage.removeItem("m1_session");
    sessionStorage.removeItem("access_token");
    sessionStorage.removeItem("refresh_token");
    return;
  }
  sessionStorage.setItem("m1_session", JSON.stringify(session));
  sessionStorage.setItem("access_token", session.accessToken);
  sessionStorage.setItem("refresh_token", session.refreshToken);
}

async function refreshTokens(): Promise<void> {
  const refreshToken = sessionStorage.getItem("refresh_token");
  if (!refreshToken) throw new ApiError("UNAUTHENTICATED", "Phiên đã hết hạn", 401);

  const response = await fetch(`${API_BASE}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    setSession(null);
    window.dispatchEvent(new Event("session-expired"));
    throw new ApiError("UNAUTHENTICATED", "Phiên đã hết hạn. Vui lòng đăng nhập lại.", response.status);
  }

  const next = toCamel(payload) as Session;
  const current = getSession();
  if (current) setSession({ ...current, accessToken: next.accessToken, refreshToken: next.refreshToken, expiresIn: next.expiresIn });
}

export async function http<T>(
  path: string,
  method = "GET",
  body?: unknown,
  signal?: AbortSignal,
  retry = true,
  extraHeaders: Record<string, string> = {},
): Promise<T> {
  const headers: Record<string, string> = { ...extraHeaders };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const accessToken = sessionStorage.getItem("access_token");
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`;

  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(toSnake(body)),
    signal,
  });
  const raw = response.status === 204 ? null : await response.json().catch(() => null);

  if (!response.ok) {
    const detail = raw && typeof raw === "object" ? ((raw as { detail?: unknown }).detail ?? raw) : null;
    const error = detail && typeof detail === "object" ? (detail as Record<string, unknown>) : {};
    const code = typeof error.code === "string" ? error.code : `HTTP_${response.status}`;
    if (code === "TOKEN_EXPIRED" && retry) {
      refreshPromise ??= refreshTokens().finally(() => { refreshPromise = null; });
      await refreshPromise;
      return http<T>(path, method, body, signal, false, extraHeaders);
    }
    const retryAfterHeader = response.headers.get("Retry-After");
    const retryAfter = retryAfterHeader ? Number(retryAfterHeader) : undefined;
    if (response.status === 401 && code === "UNAUTHENTICATED" && !path.includes("/auth/login")) {
      setSession(null);
      window.dispatchEvent(new Event("session-expired"));
    }
    const friendly = messages[code] || (typeof error.message === "string" ? error.message : code);
    const message = code === "RATE_LIMITED" && retryAfter
      ? `${friendly} Thử lại sau ${retryAfter} giây.`
      : friendly;
    throw new ApiError(code, message, response.status, retryAfter);
  }

  return toCamel(raw) as T;
}
