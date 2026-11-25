import { api } from "@/lib/api";
import type { User } from "@/types/auth";

export interface UserFilters { role?: User["role"]; is_active?: boolean }
export function listUsers(filters: UserFilters = {}, signal?: AbortSignal): Promise<User[]> {
  const query = new URLSearchParams();
  if (filters.role) query.set("role", filters.role);
  if (filters.is_active !== undefined) query.set("is_active", String(filters.is_active));
  return api<User[]>(`/users${query.size ? `?${query}` : ""}`, {
    method: "GET", signal: signal ? AbortSignal.any([signal, AbortSignal.timeout(12000)]) : undefined,
  });
}
export function updateUserActivation(id: number, isActive: boolean): Promise<User> {
  return api<User>(`/users/${id}/activation`, { method: "PATCH", body: JSON.stringify({ is_active: isActive }) });
}
