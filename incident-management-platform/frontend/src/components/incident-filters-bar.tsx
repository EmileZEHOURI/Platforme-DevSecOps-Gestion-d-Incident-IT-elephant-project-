"use client";

import { useId } from "react";
import { Button } from "@/components/ui";
import { incidentStatuses, incidentPriorities, incidentCategories, type IncidentFilters } from "@/types/incident";

export const filterErrors: Record<number, string> = {
  404: "Utilisateur introuvable ou inaccessible.",
  422: "Un filtre est invalide. Modifiez votre sélection puis réessayez.",
};
export function hasIncidentFilters(filters: IncidentFilters) {
  return Boolean(filters.status || filters.priority || filters.category);
}
export function IncidentFiltersBar({ filters, onChange, count }: {
  filters: IncidentFilters; onChange: (filters: IncidentFilters) => void; count?: number;
}) {
  const id = useId();
  const fields = [
    ["status", "Statut", "Tous les statuts", incidentStatuses],
    ["priority", "Priorité", "Toutes les priorités", incidentPriorities],
    ["category", "Catégorie", "Toutes les catégories", incidentCategories],
  ] as const;
  return <div>
    <div className="assignment-filters incident-form" role="group" aria-label="Filtres des incidents">
      {fields.map(([key, label, all, options]) => <div className="field" key={key}>
        <label htmlFor={`${id}-${key}`}>{label}</label>
        <select id={`${id}-${key}`} value={filters[key] ?? ""} onChange={event => {
          const next = { ...filters };
          delete next[key];
          if (event.target.value) Object.assign(next, { [key]: event.target.value });
          onChange(next);
        }}><option value="">{all}</option>{Object.entries(options).map(([value, text]) => <option value={value} key={value}>{text}</option>)}</select>
      </div>)}
      <Button variant="secondary" disabled={!hasIncidentFilters(filters)} onClick={() => onChange({})}>Réinitialiser les filtres</Button>
    </div>
    {count !== undefined && <p className="incident-list-summary" role="status">{count} résultat{count > 1 ? "s" : ""}</p>}
  </div>;
}
