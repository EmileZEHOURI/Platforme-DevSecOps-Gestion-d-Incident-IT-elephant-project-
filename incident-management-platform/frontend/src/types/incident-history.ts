export interface IncidentHistoryEvent {
  id: number;
  incident_id: number;
  actor_id: number;
  action: string;
  field_name: string | null;
  old_value: string | null;
  new_value: string | null;
  created_at: string;
}
export const historyActions: Record<string, string> = {
  INCIDENT_CREATED: "Incident créé", ASSIGNED: "Incident assigné", REASSIGNED: "Incident réassigné",
  PRIORITY_CHANGED: "Priorité modifiée", STATUS_CHANGED: "Statut modifié", COMMENT_ADDED: "Commentaire ajouté",
  RESOLVED: "Incident résolu", CLOSED: "Incident clôturé",
};
