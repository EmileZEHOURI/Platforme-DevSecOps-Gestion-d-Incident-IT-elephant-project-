import { notifyIncidentUpdate } from "@/lib/incident-updates";
import type { IncidentHistoryEvent } from "@/types/incident-history";
import type { User } from "@/types/auth";
import { api } from "@/lib/api";
import type { IncidentCreate, IncidentPriority, IncidentResponse, IncidentListParams, PaginatedIncidentsResponse } from "@/types/incident";

export function getIncident(id: string, signal?: AbortSignal): Promise<IncidentResponse> {
  return api<IncidentResponse>(`/incidents/${encodeURIComponent(id)}`, {
    method: "GET",
    signal: signal ? AbortSignal.any([signal, AbortSignal.timeout(12000)]) : undefined,
  });
}

export function listIncidents(signal?: AbortSignal): Promise<IncidentResponse[]> {
  return api<IncidentResponse[]>("/incidents", {
    method: "GET",
    signal: signal ? AbortSignal.any([signal, AbortSignal.timeout(12000)]) : undefined,
  });
}

export function createIncident(data: IncidentCreate): Promise<IncidentResponse> {
  // Explicit allowlist: server-owned fields can never enter the request body.
  return api<IncidentResponse>("/incidents", {
    method: "POST",
    body: JSON.stringify({
      title: data.title.trim(),
      description: data.description.trim(),
      category: data.category,
      priority: data.priority,
    }),
  }).then(result => notifyIncidentUpdate(result.id, result));
}

function filteredIncidents(path: string, filters: IncidentListParams, signal?: AbortSignal) {
  const params = new URLSearchParams({ page: String(filters.page ?? 1), page_size: String(filters.page_size ?? 20) });
  for (const key of ["status", "priority", "category"] as const) {
    if (filters[key]) params.set(key, filters[key]);
  }
  const query = params.toString();
  return api<PaginatedIncidentsResponse>(`${path}${query ? `?${query}` : ""}`, {
    method: "GET",
    signal: signal ? AbortSignal.any([signal, AbortSignal.timeout(12000)]) : undefined,
  });
}
export function listAssignedIncidents(filters?: IncidentListParams, signal?: AbortSignal): Promise<PaginatedIncidentsResponse>;
export function listAssignedIncidents(signal?: AbortSignal): Promise<PaginatedIncidentsResponse>;
export function listAssignedIncidents(filters: IncidentListParams | AbortSignal = {}, signal?: AbortSignal): Promise<PaginatedIncidentsResponse> {
  return filters instanceof AbortSignal
    ? filteredIncidents("/incidents/assigned", {}, filters)
    : filteredIncidents("/incidents/assigned", filters, signal);
}
export function listAllIncidents(filters: IncidentListParams = {}, signal?: AbortSignal): Promise<PaginatedIncidentsResponse> {
  return filteredIncidents("/incidents/all", filters, signal);
}
export const listTechnicians = () => api<User[]>("/users/technicians");
export function assignIncident(id: number, target: number) {
  return api<IncidentResponse>(`/incidents/${id}/assignment`, {
    method: "PATCH", body: JSON.stringify({ assigned_to_id: target }),
  }).then(result => notifyIncidentUpdate(id, result));
}

export function updateIncidentPriority(id: number, priority: IncidentPriority) {
  return api<IncidentResponse>(`/incidents/${id}/priority`, {
    method: "PATCH",
    body: JSON.stringify({ priority }),
  }).then(result => notifyIncidentUpdate(id, result));
}

export function startIncident(id: number): Promise<IncidentResponse> {
  return api<IncidentResponse>(`/incidents/${id}/status`, {
    method: "PATCH", body: JSON.stringify({ status: "IN_PROGRESS" }),
  }).then(result => notifyIncidentUpdate(id, result));
}

export function resolveIncident(id: number, resolution: string): Promise<IncidentResponse> {
  return api<IncidentResponse>(`/incidents/${id}/resolve`, {
    method: "PATCH", body: JSON.stringify({ resolution: resolution.trim() }),
  }).then(result => notifyIncidentUpdate(id, result));
}

export function closeIncident(id: number): Promise<IncidentResponse> {
  return api<IncidentResponse>(`/incidents/${id}/close`, { method: "PATCH" }).then(result => notifyIncidentUpdate(id, result));
}
export function getIncidentHistory(id: string, signal?: AbortSignal): Promise<IncidentHistoryEvent[]> {
  return api<IncidentHistoryEvent[]>(`/incidents/${encodeURIComponent(id)}/history`, {
    method: "GET", signal: signal ? AbortSignal.any([signal, AbortSignal.timeout(12000)]) : undefined,
  });
}


export function listCreatedIncidents(filters: IncidentListParams = {}, signal?: AbortSignal): Promise<PaginatedIncidentsResponse> {
  return filteredIncidents("/incidents", filters, signal);
}

export interface IncidentMetrics {
  open: number;
  inProgress: number;
  criticalActive: number;
  resolved: number;
}

export async function getIncidentMetrics(role: User["role"], signal?: AbortSignal): Promise<IncidentMetrics> {
  const list = role === "ADMIN" ? listAllIncidents : role === "TECHNICIAN" ? listAssignedIncidents : listCreatedIncidents;
  const filters = [
    { status: "OPEN" },
    { status: "IN_PROGRESS" },
    { status: "OPEN", priority: "CRITICAL" },
    { status: "IN_PROGRESS", priority: "CRITICAL" },
    { status: "RESOLVED" },
  ] satisfies IncidentListParams[];
  const [open, inProgress, criticalOpen, criticalInProgress, resolved] = await Promise.all(
    filters.map(filter => list({ ...filter, page: 1, page_size: 1 }, signal)),
  );
  return { open: open.total, inProgress: inProgress.total,
    criticalActive: criticalOpen.total + criticalInProgress.total, resolved: resolved.total };
}
