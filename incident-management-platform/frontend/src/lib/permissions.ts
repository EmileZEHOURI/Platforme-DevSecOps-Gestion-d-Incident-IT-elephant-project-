import type { IncidentResponse } from "@/types/incident";
import type { User } from "@/types/auth";

// Navigation only: the API remains responsible for authorization.
export function canViewAssignedIncidents(role: User["role"]): boolean {
  return role === "TECHNICIAN" || role === "ADMIN";
}

export function canStartIncident(user: User | null, incident: IncidentResponse): boolean {
  return !!user && canViewAssignedIncidents(user.role) && incident.assigned_to_id === user.id && incident.status === "OPEN";
}

export function canResolveIncident(user: User | null, incident: IncidentResponse): boolean {
  return !!user && canViewAssignedIncidents(user.role) && incident.assigned_to_id === user.id && incident.status === "IN_PROGRESS";
}

export function canCloseIncident(user: User | null, incident: IncidentResponse): boolean {
  return !!user && incident.status === "RESOLVED" && (user.role === "ADMIN" || user.id === incident.created_by_id);
}
