export const incidentCategories = {
  SUPPORT: "Assistance", SECURITY: "Sécurité", ACCESS: "Accès",
  ANOMALY: "Anomalie", DATA: "Données",
} as const;

export const incidentPriorities = {
  LOW: "Faible", MEDIUM: "Moyenne", HIGH: "Élevée", CRITICAL: "Critique",
} as const;

export type IncidentCategory = keyof typeof incidentCategories;
export type IncidentPriority = keyof typeof incidentPriorities;

export const incidentStatuses = {
  OPEN: "Ouvert", IN_PROGRESS: "En cours", RESOLVED: "Résolu", CLOSED: "Clos",
} as const;

export interface IncidentCreate {
  title: string;
  description: string;
  category: IncidentCategory;
  priority: IncidentPriority;
}

export interface IncidentResponse extends IncidentCreate {
  id: number;
  reference: string;
  status: "OPEN" | "IN_PROGRESS" | "RESOLVED" | "CLOSED";
  created_by_id: number;
  assigned_to_id: number | null;
  resolution: string | null;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
  closed_at: string | null;
}
