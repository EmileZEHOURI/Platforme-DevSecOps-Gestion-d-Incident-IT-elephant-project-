export const auditEvents = {
  LOGIN_SUCCESS: "Connexion réussie", LOGIN_FAILURE: "Échec de connexion", LOGOUT: "Déconnexion", ACCESS_DENIED: "Accès refusé",
  USER_CREATED: "Utilisateur créé", USER_UPDATED: "Utilisateur modifié", USER_ACTIVATED: "Utilisateur activé", USER_DEACTIVATED: "Utilisateur désactivé", ROLE_CHANGED: "Rôle modifié",
  INCIDENT_CREATED: "Incident créé", INCIDENT_ASSIGNED: "Incident assigné", INCIDENT_REASSIGNED: "Incident réassigné", INCIDENT_PRIORITY_CHANGED: "Priorité modifiée", INCIDENT_STATUS_CHANGED: "Statut modifié", INCIDENT_RESOLVED: "Incident résolu", INCIDENT_CLOSED: "Incident clôturé",
} as const;
export const auditResults = { SUCCESS: "Succès", FAILURE: "Échec", DENIED: "Accès refusé" } as const;
export type AuditResult = keyof typeof auditResults;
export interface AuditLog {
  id: number; user_id: number | null; event_type: string; resource_type: string | null; resource_id: number | null;
  result: AuditResult; ip_address: string | null; user_agent: string | null; details: Record<string, unknown>; created_at: string;
}
export interface PaginatedAuditLogsResponse {
  items: AuditLog[]; total: number; page: number; page_size: number; total_pages: number; has_next: boolean; has_previous: boolean;
}
export interface AuditFilters {
  user_id?: number; event_type?: keyof typeof auditEvents; result?: AuditResult; date_from?: string; date_to?: string;
}
export function auditEventLabel(event: string): string {
  return Object.hasOwn(auditEvents, event) ? auditEvents[event as keyof typeof auditEvents] : event;
}
