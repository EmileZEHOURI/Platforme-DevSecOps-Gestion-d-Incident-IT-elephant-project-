import type { User } from "@/types/auth";

// Navigation only: the API remains responsible for authorization.
export function canViewAssignedIncidents(role: User["role"]): boolean {
  return role === "TECHNICIAN" || role === "ADMIN";
}
