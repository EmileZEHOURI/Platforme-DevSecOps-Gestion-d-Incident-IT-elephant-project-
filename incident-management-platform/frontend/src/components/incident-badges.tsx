import { Badge } from "@/components/ui";
import { incidentPriorities, incidentStatuses, type IncidentResponse } from "@/types/incident";

export function IncidentPriorityBadge({ priority }: { priority: IncidentResponse["priority"] }) {
  return <Badge tone={priority === "HIGH" || priority === "CRITICAL" ? "warning" : "neutral"}>{incidentPriorities[priority]}</Badge>;
}

export function IncidentStatusBadge({ status }: { status: IncidentResponse["status"] }) {
  return <Badge tone={status === "RESOLVED" || status === "CLOSED" ? "success" : status === "IN_PROGRESS" ? "warning" : "neutral"}>{incidentStatuses[status]}</Badge>;
}
