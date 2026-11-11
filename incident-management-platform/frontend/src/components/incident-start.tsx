"use client";

import { useRef, useState } from "react";
import { useAuth } from "@/components/auth-provider";
import { AdminError } from "@/components/assignment-controls";
import { Button } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { canStartIncident } from "@/lib/permissions";
import { startIncident } from "@/services/incident.service";
import type { IncidentResponse } from "@/types/incident";

const descriptions = {
  403: "Vous devez être responsable de cet incident pour commencer son traitement.",
  404: "L’incident est introuvable ou inaccessible.",
  409: "Le traitement ne peut plus démarrer : vérifiez le statut et l’affectation de l’incident.",
  422: "Le changement de statut demandé est invalide.",
};

export function useIncidentStart(saved: (item: IncidentResponse) => void, refresh: () => void) {
  const { user } = useAuth();
  const lock = useRef(false);
  const [pending, setPending] = useState<number | null>(null);
  const [notice, notify] = useState("");
  const [error, setError] = useState<Error | null>(null);
  async function begin(incident: IncidentResponse) {
    if (lock.current || !canStartIncident(user, incident)) return;
    lock.current = true;
    setPending(incident.id); setError(null); notify("");
    try {
      const result = await startIncident(incident.id);
      saved(result);
      notify(`${result.reference} : traitement commencé.`);
    } catch (cause) {
      setError(cause instanceof Error ? cause : new Error());
      if (cause instanceof ApiError && [403, 404, 409].includes(cause.status)) refresh();
    } finally {
      lock.current = false; setPending(null);
    }
  }
  function action(incident: IncidentResponse) {
    if (!canStartIncident(user, incident)) return null;
    return <Button type="button" variant="secondary" disabled={pending !== null} onClick={() => void begin(incident)}>
      {pending === incident.id ? "Démarrage…" : "Commencer le traitement"}
    </Button>;
  }
  const feedback = error ? <AdminError error={error} descriptions={descriptions} /> :
    notice ? <p className="comment-confirmation" role="status">{notice}</p> : null;
  return { action, feedback };
}
