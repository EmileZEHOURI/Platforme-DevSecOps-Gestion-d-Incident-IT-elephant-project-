import { api } from "@/lib/api";
import type { User } from "@/types/auth";

export const getMe = () => api<User>("/auth/me");
export const login = (email: string, password: string) => api<User>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
export const logout = () => api<{ message: string }>("/auth/logout", { method: "POST" });
