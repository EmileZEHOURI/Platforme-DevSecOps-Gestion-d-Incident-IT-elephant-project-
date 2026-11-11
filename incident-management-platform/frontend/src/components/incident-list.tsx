"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth-provider";
import { Button, StatePanel } from "@/components/ui";
import { IncidentTable } from "@/components/incident-table";
import { ApiError } from "@/lib/api";
import { canViewAssignedIncidents } from "@/lib/permissions";
import { listIncidents, listAssignedIncidents } from "@/services/incident.service";
import type { IncidentResponse } from "@/types/incident";

type IncidentScope = "created" | "assigned";

type ListState =
  | { status: "loading" }
  | { status: "success"; incidents: IncidentResponse[] }
  | { status: "error"; message: string; code?: number };

function UserIncidentList({ scope }: { scope: IncidentScope }) {
  const assigned = scope === "assigned";
  const [state, setState] = useState<ListState>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    const fetchIncidents = assigned ? listAssignedIncidents : listIncidents;
    void fetchIncidents(controller.signal).then(incidents => {
      if (active) setState({ status: "success", incidents });
    }).catch(error => {
      if (active) setState({
        status: "error",
        message: error instanceof Error ? error.message : "Impossible de charger vos incidents.",
        code: error instanceof ApiError ? error.status : undefined,
      });
    });
    return () => { active = false; controller.abort(); };
  }, [attempt, assigned]);

  function reload() { setState({ status: "loading" }); setAttempt(value => value + 1); }

  return (
    <section className="panel" aria-labelledby="incident-list-heading" aria-busy={state.status === "loading"}>
      <div className="panel-heading">
        <h2 id="incident-list-heading">{assigned ? "Mes incidents assignés" : "Mes incidents"}</h2>
        <Button variant="ghost" disabled={state.status === "loading"} onClick={reload}>Actualiser ↻</Button>
      </div>
      {state.status === "loading" && <div className="incident-list-loading" role="status"><span className="spinner" aria-hidden="true" />Chargement de vos incidents…</div>}
      {state.status === "error" && <StatePanel error
        title={state.code === 401 ? "Session expirée" : state.code === 403 ? "Accès refusé" : "Impossible de charger les incidents"}
        description={state.message}>
        {state.code === 401
          ? <Link className="button button-primary" href={`/login?next=${encodeURIComponent(assigned ? "/dashboard/incidents/assigned" : "/dashboard/incidents")}`}>Se reconnecter</Link>
          : <Button variant="secondary" onClick={reload}>Réessayer</Button>}
      </StatePanel>}
      {state.status === "success" && (state.incidents.length === 0
        ? assigned ? <StatePanel title="Aucun incident assigné" description="Aucun incident ne vous est actuellement assigné. Votre file de travail apparaîtra ici dès une nouvelle assignation." /> : <StatePanel title="Aucun incident pour le moment" description="Vos prochains signalements apparaîtront ici. Vous pouvez créer un incident dès maintenant.">
          <Link className="button button-secondary" href="/dashboard/incidents/new">Créer mon premier incident</Link>
        </StatePanel>
        : <>
          <p className="incident-list-summary" role="status">{state.incidents.length} incident{state.incidents.length > 1 ? "s" : ""} · {assigned ? "Dans votre file de travail" : "Du plus récent au plus ancien"}</p>
          <IncidentTable incidents={state.incidents} />
        </>)}
    </section>
  );
}

export function IncidentList({ scope = "created" }: { scope?: IncidentScope }) {
  const { user } = useAuth();
  if (user && scope === "assigned" && !canViewAssignedIncidents(user.role)) {
    return <StatePanel error title="Accès refusé" description="Cette vue est réservée aux techniciens et aux administrateurs.">
      <Link className="button button-secondary" href="/dashboard/incidents">Retour à mes incidents</Link>
    </StatePanel>;
  }
  // Reset cached UI if the session changes; authorization and filtering stay on the API.
  return user ? <UserIncidentList key={`${user.id}:${user.role}:${scope}`} scope={scope} /> : null;
}
