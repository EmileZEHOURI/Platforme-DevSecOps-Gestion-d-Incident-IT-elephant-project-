"use client";

import { useRef, useState, type FormEvent } from "react";
import { useAuth } from "@/components/auth-provider";
import { IncidentEditDialog } from "@/components/incident-edit-dialog";
import { AdminError } from "@/components/assignment-controls";
import { Button } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { canCloseIncident } from "@/lib/permissions";
import { closeIncident } from "@/services/incident.service";
import type { IncidentResponse } from "@/types/incident";

const descriptions = {
  403: "Seul le créateur de l’incident ou un administrateur peut le clôturer.",
  404: "Incident introuvable ou inaccessible.",
  409: "Cet incident ne peut plus être clôturé dans son état actuel. Les données sont en cours d’actualisation.",
};

function CloseDialog({ incident, cancel, saved, refresh }: {
  incident: IncidentResponse; cancel: () => void; saved: (item: IncidentResponse) => void; refresh: () => void;
}) {
  const { user } = useAuth();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const lock = useRef(false);
  const blocked = !canCloseIncident(user, incident) || (error instanceof ApiError && [401, 403, 404, 409].includes(error.status));
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (lock.current || blocked) return;
    lock.current = true; setPending(true); setError(null);
    try { saved(await closeIncident(incident.id)); }
    catch (cause) {
      setError(cause instanceof Error ? cause : new Error());
      if (cause instanceof ApiError && [403, 404, 409].includes(cause.status)) refresh();
    } finally { lock.current = false; setPending(false); }
  }
  function dismiss() { if (!lock.current) cancel(); }
  return <IncidentEditDialog incident={incident} title="Clôturer l’incident ?" pending={pending} close={dismiss} submit={submit}>
    <p className="muted mb-5">Confirmez la clôture de cet incident résolu. La solution restera consultable et aucun nouveau commentaire ne pourra être ajouté.</p>
    {error && <AdminError error={error} descriptions={descriptions} />}
    <div className="incident-actions">
      <Button type="submit" disabled={pending || blocked}>{pending ? "Clôture en cours…" : "Confirmer la clôture"}</Button>
      <Button type="button" variant="secondary" disabled={pending} onClick={dismiss}>Annuler</Button>
    </div>
  </IncidentEditDialog>;
}

export function useIncidentClose(saved: (item: IncidentResponse) => void, refresh: () => void) {
  const { user } = useAuth();
  const [selected, select] = useState<IncidentResponse | null>(null);
  const [notice, notify] = useState("");
  function action(incident: IncidentResponse) {
    if (!canCloseIncident(user, incident)) return null;
    return <Button type="button" variant="secondary" onClick={() => { notify(""); select(incident); }}>Clôturer l’incident</Button>;
  }
  const feedback = <>
    {notice && <p className="comment-confirmation" role="status">{notice}</p>}
    {selected && canCloseIncident(user, selected) && <CloseDialog key={selected.id} incident={selected} cancel={() => select(null)} refresh={refresh}
      saved={updated => { saved(updated); select(null); notify(`${updated.reference} : incident clôturé.`); }} />}
  </>;
  return { action, feedback };
}
