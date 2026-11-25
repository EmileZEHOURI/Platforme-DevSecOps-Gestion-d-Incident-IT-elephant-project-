import { api } from "@/lib/api";
import type { AuditFilters, PaginatedAuditLogsResponse } from "@/types/audit";

export function listAuditLogs(filters: AuditFilters, page = 1, pageSize = 20, signal?: AbortSignal) {
  const query = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  for (const key of ["user_id", "event_type", "result", "date_from", "date_to"] as const) {
    const value = filters[key];
    if (value !== undefined && value !== "") query.set(key, String(value));
  }
  return api<PaginatedAuditLogsResponse>(`/audit-logs?${query}`, { method: "GET",
    signal: signal ? AbortSignal.any([signal, AbortSignal.timeout(12000)]) : undefined });
}
