"use client";

import { useRef, useState, type FormEvent } from "react";
import { AdminError } from "@/components/assignment-controls";
import { IncidentEditDialog } from "@/components/incident-edit-dialog";
import { Button } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { updateIncidentPriority } from "@/services/incident.service";
import { incidentPriorities, type IncidentPriority, type IncidentResponse } from "@/types/incident";

const messages = {
  404: "Cet incident est introuvable. Fermez cette fenêtre et actualisez la liste.",
  409: "Cet incident est fermé. Sa priorité ne peut plus être modifiée.",
  422: "La priorité sélectionnée est invalide. Choisissez une autre valeur.",
};

export function PriorityDialog({ incident, close, saved }: {
  incident: IncidentResponse; close: () => void; saved: (updated: IncidentResponse) => void;
}) {
  const [priority, setPriority] = useState<IncidentPriority>(incident.priority);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const locked = useRef(false);
  const blocked = incident.status === "CLOSED" || (error instanceof ApiError && [401, 403, 404, 409].includes(error.status));
  const unchanged = incident.priority === priority;
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (blocked || unchanged || locked.current) return;
    locked.current = true;
    setPending(true); setError(null);
    try { saved(await updateIncidentPriority(incident.id, priority)); }
    catch (cause) { setError(cause instanceof Error ? cause : new Error()); }
    finally { locked.current = false; setPending(false); }
  }
  return <IncidentEditDialog incident={incident} title="Modifier la priorité" pending={pending} close={close} submit={submit}>
    <div className="field"><label htmlFor="new-priority">Nouvelle priorité</label>
      <select id="new-priority" value={priority} disabled={blocked || pending} onChange={event => {
        const value = event.target.value;
        if (Object.hasOwn(incidentPriorities, value)) { setPriority(value as IncidentPriority); setError(null); }
      }}>{Object.entries(incidentPriorities).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select>
    </div>
    {unchanged && <p className="muted" role="status">Cette priorité est déjà enregistrée.</p>}
    {error && <AdminError error={error} descriptions={messages} />}
    <div className="incident-actions">
      <Button type="submit" disabled={pending || blocked || unchanged}>{pending ? "Enregistrement…" : "Confirmer"}</Button>
      <Button type="button" variant="secondary" disabled={pending} onClick={close}>Annuler</Button>
    </div>
  </IncidentEditDialog>;
}
