"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth-provider";
import { Button, StatePanel } from "@/components/ui";
import { IncidentPriorityBadge, IncidentStatusBadge } from "@/components/incident-badges";
import { ApiError } from "@/lib/api";
import { listIncidents } from "@/services/incident.service";
import { incidentCategories, type IncidentResponse } from "@/types/incident";

type ListState =
  | { status: "loading" }
  | { status: "success"; incidents: IncidentResponse[] }
  | { status: "error"; message: string; code?: number };

const dateFormat = new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium", timeStyle: "short" });

function IncidentTable({ incidents }: { incidents: IncidentResponse[] }) {
  return (
    <div className="incident-table-scroll" role="region" aria-label="Liste des incidents, défilement horizontal disponible" tabIndex={0}>
      <table className="incident-table">
        <caption className="sr-only">Vos incidents, dans l’ordre renvoyé par le service</caption>
        <thead><tr><th scope="col">Référence</th><th scope="col">Titre</th><th scope="col">Catégorie</th><th scope="col">Priorité</th><th scope="col">Statut</th><th scope="col">Créé le</th></tr></thead>
        <tbody>{incidents.map(incident => (
          <tr key={incident.id}>
            <th scope="row" className="incident-reference"><Link className="incident-detail-link" href={`/dashboard/incidents/${incident.id}`} aria-label={`Voir le détail de ${incident.reference}`}>{incident.reference}</Link></th>
            <td className="incident-list-title">{incident.title}</td>
            <td>{incidentCategories[incident.category]}</td>
            <td><IncidentPriorityBadge priority={incident.priority} /></td>
            <td><IncidentStatusBadge status={incident.status} /></td>
            <td className="incident-list-date"><time dateTime={incident.created_at}>{dateFormat.format(new Date(incident.created_at))}</time></td>
          </tr>
        ))}</tbody>
      </table>
    </div>
  );
}

function UserIncidentList() {
  const [state, setState] = useState<ListState>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    void listIncidents(controller.signal).then(incidents => {
      if (active) setState({ status: "success", incidents });
    }).catch(error => {
      if (active) setState({
        status: "error",
        message: error instanceof Error ? error.message : "Impossible de charger vos incidents.",
        code: error instanceof ApiError ? error.status : undefined,
      });
    });
    return () => { active = false; controller.abort(); };
  }, [attempt]);

  function reload() { setState({ status: "loading" }); setAttempt(value => value + 1); }

  return (
    <section className="panel" aria-labelledby="incident-list-heading" aria-busy={state.status === "loading"}>
      <div className="panel-heading">
        <h2 id="incident-list-heading">Mes incidents</h2>
        <Button variant="ghost" disabled={state.status === "loading"} onClick={reload}>Actualiser ↻</Button>
      </div>
      {state.status === "loading" && <div className="incident-list-loading" role="status"><span className="spinner" aria-hidden="true" />Chargement de vos incidents…</div>}
      {state.status === "error" && <StatePanel error
        title={state.code === 401 ? "Session expirée" : state.code === 403 ? "Accès refusé" : "Impossible de charger les incidents"}
        description={state.message}>
        {state.code === 401
          ? <Link className="button button-primary" href="/login?next=%2Fdashboard%2Fincidents">Se reconnecter</Link>
          : <Button variant="secondary" onClick={reload}>Réessayer</Button>}
      </StatePanel>}
      {state.status === "success" && (state.incidents.length === 0
        ? <StatePanel title="Aucun incident pour le moment" description="Vos prochains signalements apparaîtront ici. Vous pouvez créer un incident dès maintenant.">
          <Link className="button button-secondary" href="/dashboard/incidents/new">Créer mon premier incident</Link>
        </StatePanel>
        : <>
          <p className="incident-list-summary" role="status">{state.incidents.length} incident{state.incidents.length > 1 ? "s" : ""} · Du plus récent au plus ancien</p>
          <IncidentTable incidents={state.incidents} />
        </>)}
    </section>
  );
}

export function IncidentList() {
  const { user } = useAuth();
  // Reset cached UI if the session changes; authorization and filtering stay on the API.
  return user ? <UserIncidentList key={user.id} /> : null;
}
