"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Button, StatePanel } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { subscribeIncidentUpdates } from "@/lib/incident-updates";
import { getIncidentHistory } from "@/services/incident.service";
import { historyActions, type IncidentHistoryEvent } from "@/types/incident-history";
import { incidentPriorities, incidentStatuses } from "@/types/incident";

type State = { status: "loading" } | { status: "success"; events: IncidentHistoryEvent[] } | { status: "error"; code?: number };
const dates = new Intl.DateTimeFormat("fr-FR", { dateStyle: "long", timeStyle: "short" });
const fields: Record<string, string> = { status: "Statut", priority: "Priorité", assigned_to_id: "Assignation", resolution: "Résolution" };
function valueLabel(field: string, value: string | null): string {
  if (value === null || value === "") return field === "assigned_to_id" ? "Non assigné" : "Non renseigné";
  if (field === "status") return Object.hasOwn(incidentStatuses, value) ? incidentStatuses[value as keyof typeof incidentStatuses] : value;
  if (field === "priority") return Object.hasOwn(incidentPriorities, value) ? incidentPriorities[value as keyof typeof incidentPriorities] : value;
  return field === "assigned_to_id" ? `Utilisateur n° ${value}` : value;
}
export function IncidentHistory({ id }: { id: string }) {
  const [state, setState] = useState<State>({ status: "loading" });
  const [attempt, retry] = useState(0);
  useEffect(() => {
    let active = true;
    let controller: AbortController;
    let generation = 0;
    function load() {
      controller?.abort();
      controller = new AbortController();
      const current = ++generation;
      setState({ status: "loading" });
      void getIncidentHistory(id, controller.signal).then(events => {
        if (active && current === generation) setState({ status: "success", events });
      }).catch(error => {
        if (active && current === generation) setState({ status: "error", code: error instanceof ApiError ? error.status : undefined });
      });
    }
    const unsubscribe = subscribeIncidentUpdates(incidentId => { if (String(incidentId) === id) load(); });
    load();
    return () => { active = false; controller?.abort(); unsubscribe(); };
  }, [id, attempt]);
  const code = state.status === "error" ? state.code : undefined;
  const messages: Record<number, string> = {
    401: "Votre session a expiré. Reconnectez-vous pour consulter l’historique.",
    403: "Vous ne disposez pas des autorisations nécessaires pour consulter cet historique.",
    404: "L’incident ou son historique est introuvable ou inaccessible.",
    422: "L’identifiant de l’incident est invalide.",
  };
  return <section className="panel" aria-labelledby="incident-history-heading" aria-busy={state.status === "loading"}>
    <div className="panel-heading"><h2 id="incident-history-heading">Historique de l’incident</h2>
      <Button variant="ghost" disabled={state.status === "loading"} onClick={() => retry(n => n + 1)}>Actualiser l’historique</Button></div>
    {state.status === "loading" && <div className="incident-list-loading" role="status"><span className="spinner" aria-hidden="true" />Chargement de l’historique…</div>}
    {state.status === "error" && <StatePanel error title={code === 401 ? "Session expirée" : code === 403 ? "Accès refusé à l’historique" : "Historique indisponible"}
      description={messages[code ?? 0] ?? "Impossible de charger l’historique. Vérifiez votre connexion ou réessayez dans un instant."}>
      {code === 401 ? <Link className="button button-secondary" href={`/login?next=${encodeURIComponent("/dashboard/incidents/" + id)}`}>Se reconnecter</Link>
        : <Button variant="secondary" onClick={() => retry(n => n + 1)}>Réessayer</Button>}
    </StatePanel>}
    {state.status === "success" && (state.events.length === 0
      ? <p className="panel-note" role="status">Aucun événement disponible pour cet incident.</p>
      : <ol className="incident-history-list">{state.events.map(event => {
        const date = new Date(event.created_at);
        return <li key={event.id}>
          <h3>{Object.hasOwn(historyActions, event.action) ? historyActions[event.action] : "Événement enregistré"}</h3>
          <p className="muted"><time dateTime={event.created_at}>{Number.isNaN(date.valueOf()) ? "Date indisponible" : dates.format(date)}</time> · Auteur : utilisateur n° {event.actor_id}</p>
          {event.field_name && (event.old_value !== null || event.new_value !== null) && <p className="history-change">
            {Object.hasOwn(fields, event.field_name) ? fields[event.field_name] : "Modification"} : {valueLabel(event.field_name, event.old_value)}
            <span aria-hidden="true"> → </span><span className="sr-only"> devient </span>{valueLabel(event.field_name, event.new_value)}
          </p>}
        </li>;
      })}</ol>)}
  </section>;
}
