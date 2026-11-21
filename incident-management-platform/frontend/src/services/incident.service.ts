import { notifyIncidentUpdate } from "@/lib/incident-updates";
import type { IncidentHistoryEvent } from "@/types/incident-history";
import type { User } from "@/types/auth";
import { api } from "@/lib/api";
import type { IncidentCreate, IncidentPriority, IncidentResponse, IncidentFilters } from "@/types/incident";

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
  });
}

function filteredIncidents(path: string, filters: IncidentFilters, signal?: AbortSignal) {
  const params = new URLSearchParams();
  for (const key of ["status", "priority", "category"] as const) {
    if (filters[key]) params.set(key, filters[key]);
  }
  const query = params.toString();
  return api<IncidentResponse[]>(`${path}${query ? `?${query}` : ""}`, {
    method: "GET",
    signal: signal ? AbortSignal.any([signal, AbortSignal.timeout(12000)]) : undefined,
  });
}
export function listAssignedIncidents(filters?: IncidentFilters, signal?: AbortSignal): Promise<IncidentResponse[]>;
export function listAssignedIncidents(signal?: AbortSignal): Promise<IncidentResponse[]>;
export function listAssignedIncidents(filters: IncidentFilters | AbortSignal = {}, signal?: AbortSignal): Promise<IncidentResponse[]> {
  return filters instanceof AbortSignal
    ? filteredIncidents("/incidents/assigned", {}, filters)
    : filteredIncidents("/incidents/assigned", filters, signal);
}
export function listAllIncidents(filters: IncidentFilters = {}, signal?: AbortSignal): Promise<IncidentResponse[]> {
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
