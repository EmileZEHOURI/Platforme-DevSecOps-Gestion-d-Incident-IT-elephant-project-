"use client";

import { useId, useRef, useState, type FormEvent } from "react";
import { useAuth } from "@/components/auth-provider";
import { IncidentEditDialog } from "@/components/incident-edit-dialog";
import { AdminError } from "@/components/assignment-controls";
import { Button } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { canResolveIncident } from "@/lib/permissions";
import { resolveIncident } from "@/services/incident.service";
import type { IncidentResponse } from "@/types/incident";

const messages: Record<number, string> = {
  403: "Seul le technicien ou administrateur responsable peut résoudre cet incident.",
  404: "Incident introuvable ou inaccessible.",
  409: "La résolution est impossible : le statut ou l’affectation a changé. Fermez cette fenêtre pour actualiser les données.",
  422: "La description de résolution est obligatoire ou invalide.",
};
// Only display known business messages, never raw server diagnostics.
const businessDetails = new Set([
  "L'incident n'a pas de responsable",
  "Impossible de résoudre un incident fermé",
  "Cet incident a déjà été résolu",
  "Seul un incident en cours de traitement peut être résolu",
  "Le contenu ne doit pas être vide",
]);

function ResolveDialog({ incident, close, saved, refresh }: {
  incident: IncidentResponse; close: () => void;
  saved: (updated: IncidentResponse) => void; refresh: () => void;
}) {
  const { user } = useAuth();
  const [text, setText] = useState("");
  const [validation, setValidation] = useState("");
  const [error, setError] = useState<Error | null>(null);
  const [pending, setPending] = useState(false);
  const lock = useRef(false);
  const field = useRef<HTMLTextAreaElement>(null);
  const id = useId();
  const code = error instanceof ApiError ? error.status : 0;
  const stale = [403, 404, 409].includes(code);
  const blocked = stale || code === 401 || !canResolveIncident(user, incident);
  const descriptions = { ...messages };
  if (error instanceof ApiError && typeof error.detail === "string" && businessDetails.has(error.detail) && [409, 422].includes(code)) {
    descriptions[code] = error.detail;
  }
  function cancel() {
    if (lock.current) return;
    close();
    if (stale) refresh();
  }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (lock.current || blocked) return;
    const content = text.trim();
    if (!content) {
      setValidation("Décrivez la résolution : le champ ne peut pas être vide.");
      field.current?.focus();
      return;
    }
    lock.current = true; setPending(true); setError(null); setValidation("");
    try { saved(await resolveIncident(incident.id, content)); }
    catch (cause) {
      const failure = cause instanceof Error ? cause : new Error();
      setError(failure);
      if (failure instanceof ApiError && failure.status === 422) {
        setValidation("La description est invalide. Vérifiez le texte saisi.");
        field.current?.focus();
      }
    } finally { lock.current = false; setPending(false); }
  }
  return <IncidentEditDialog incident={incident} title="Résoudre l’incident" pending={pending} close={cancel} submit={submit}>
    <p className="muted mb-5" id={id + "-help"}>Décrivez les actions effectuées pour résoudre cet incident. Cette description sera conservée dans son historique.</p>
    <div className="field">
      <label htmlFor={id}>Description de la résolution</label>
      <textarea ref={field} id={id} rows={6} aria-required="true" aria-invalid={!!validation}
        aria-describedby={id + "-help" + (validation ? " " + id + "-error" : "")}
        placeholder="Décrivez la correction apportée et les vérifications effectuées…"
        value={text} disabled={pending || blocked}
        onChange={event => { setText(event.target.value); setValidation(""); setError(null); }} />
      {validation && <p id={id + "-error"} role="alert" className="incident-field-error">{validation}</p>}
    </div>
    {error && <AdminError error={error} descriptions={descriptions} />}
    {stale && <p className="muted">Fermez cette fenêtre pour actualiser l’incident.</p>}
    <div className="incident-actions">
      <Button type="submit" disabled={pending || blocked}>{pending ? "Résolution en cours…" : "Confirmer la résolution"}</Button>
      <Button type="button" variant="secondary" disabled={pending} onClick={cancel}>Annuler</Button>
    </div>
  </IncidentEditDialog>;
}

export function useIncidentResolve(saved: (updated: IncidentResponse) => void, refresh: () => void) {
  const { user } = useAuth();
  const [selected, select] = useState<IncidentResponse | null>(null);
  const [notice, notify] = useState("");
  function action(incident: IncidentResponse) {
    if (!canResolveIncident(user, incident)) return null;
    return <Button type="button" variant="secondary" onClick={() => { notify(""); select(incident); }}>Résoudre l’incident</Button>;
  }
  const feedback = <>
    {notice && <p className="comment-confirmation" role="status">{notice}</p>}
    {selected && canResolveIncident(user, selected) && <ResolveDialog key={selected.id} incident={selected} refresh={refresh} close={() => select(null)}
      saved={updated => { saved(updated); select(null); notify(`${updated.reference} : incident résolu.`); }} />}
  </>;
  return { action, feedback };
}
