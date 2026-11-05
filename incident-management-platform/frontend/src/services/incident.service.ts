import { api } from "@/lib/api";
import type { IncidentCreate, IncidentResponse } from "@/types/incident";

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
