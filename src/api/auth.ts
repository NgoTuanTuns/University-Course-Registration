import type { Session } from "../types";
import { http } from "./http";

export const login = (email: string, password: string) =>
  http<Session>("/auth/login", "POST", { email, password });

export const logout = (refreshToken: string) =>
  http<{ message: string }>("/auth/logout", "POST", { refreshToken });
