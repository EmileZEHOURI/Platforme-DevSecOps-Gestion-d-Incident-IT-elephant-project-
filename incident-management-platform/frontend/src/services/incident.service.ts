import { api } from "@/lib/api";
import type { IncidentCreate, IncidentResponse } from "@/types/incident";

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
