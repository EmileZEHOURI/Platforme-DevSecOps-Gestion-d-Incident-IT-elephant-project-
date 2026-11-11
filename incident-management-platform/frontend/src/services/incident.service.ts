import type { User } from "@/types/auth";
import { api } from "@/lib/api";
import type { IncidentCreate, IncidentPriority, IncidentResponse } from "@/types/incident";

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

export function listAssignedIncidents(signal?: AbortSignal): Promise<IncidentResponse[]> {
  return api<IncidentResponse[]>("/incidents/assigned", {
    method: "GET",
    signal: signal ? AbortSignal.any([signal, AbortSignal.timeout(12000)]) : undefined,
  });
}
export const listAllIncidents = () => api<IncidentResponse[]>("/incidents/all");
export const listTechnicians = () => api<User[]>("/users/technicians");
export function assignIncident(id: number, target: number) {
  return api<IncidentResponse>(`/incidents/${id}/assignment`, {
    method: "PATCH", body: JSON.stringify({ assigned_to_id: target }),
  });
}

export function updateIncidentPriority(id: number, priority: IncidentPriority) {
  return api<IncidentResponse>(`/incidents/${id}/priority`, {
    method: "PATCH",
    body: JSON.stringify({ priority }),
  });
}
