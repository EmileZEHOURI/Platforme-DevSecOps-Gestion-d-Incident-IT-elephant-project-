"use client";

import { IncidentFiltersBar, hasIncidentFilters, filterErrors } from "@/components/incident-filters-bar";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useIncidentResolve } from "@/components/incident-resolve";
import { useIncidentStart } from "@/components/incident-start";
import { useAuth } from "@/components/auth-provider";
import { Button, StatePanel } from "@/components/ui";
import { IncidentTable } from "@/components/incident-table";
import { ApiError } from "@/lib/api";
import { canViewAssignedIncidents } from "@/lib/permissions";
import { listIncidents, listAssignedIncidents } from "@/services/incident.service";
import type { IncidentFilters, IncidentResponse } from "@/types/incident";

type IncidentScope = "created" | "assigned";

type ListState =
  | { status: "loading" }
  | { status: "success"; incidents: IncidentResponse[] }
  | { status: "error"; message: string; code?: number };

function UserIncidentList({ scope }: { scope: IncidentScope }) {
  const assigned = scope === "assigned";
  const [state, setState] = useState<ListState>({ status: "loading" });
  const [filters, setFilters] = useState<IncidentFilters>({});
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    const request = assigned ? listAssignedIncidents(filters, controller.signal) : listIncidents(controller.signal);
    void request.then(incidents => {
      if (active) setState({ status: "success", incidents });
    }).catch(error => {
      if (active) setState({
        status: "error",
        message: error instanceof Error ? error.message : "Impossible de charger vos incidents.",
        code: error instanceof ApiError ? error.status : undefined,
      });
    });
    return () => { active = false; controller.abort(); };
  }, [attempt, assigned, filters]);

  function reload() { setState({ status: "loading" }); setAttempt(value => value + 1); }

  function changeFilters(next: IncidentFilters) { setState({ status: "loading" }); setFilters(next); }

  const start = useIncidentStart(updated => {
    if (assigned) { reload(); return; }
    setState(current => current.status === "success" ? { ...current, incidents: current.incidents.map(i => i.id === updated.id ? updated : i) } : current);
  }, reload);
  const resolve = useIncidentResolve(updated => {
    if (assigned) { reload(); return; }
    setState(current => current.status === "success" ? { ...current, incidents: current.incidents.map(i => i.id === updated.id ? updated : i) } : current);
  }, reload);
  return (
    <section className="panel" aria-labelledby="incident-list-heading" aria-busy={state.status === "loading"}>
      {start.feedback}
      {resolve.feedback}
      <div className="panel-heading">
        <h2 id="incident-list-heading">{assigned ? "Mes incidents assignés" : "Mes incidents"}</h2>
        <Button variant="ghost" disabled={state.status === "loading"} onClick={reload}>Actualiser ↻</Button>
      </div>
      {assigned && <IncidentFiltersBar filters={filters} onChange={changeFilters} count={state.status === "success" ? state.incidents.length : undefined} />}
      {state.status === "loading" && <div className="incident-list-loading" role="status"><span className="spinner" aria-hidden="true" />Chargement de vos incidents…</div>}
      {state.status === "error" && <StatePanel error
        title={state.code === 401 ? "Session expirée" : state.code === 403 ? "Accès refusé" : "Impossible de charger les incidents"}
        description={(assigned && filterErrors[state.code ?? 0]) || state.message}>
        {state.code === 401
          ? <Link className="button button-primary" href={`/login?next=${encodeURIComponent(assigned ? "/dashboard/incidents/assigned" : "/dashboard/incidents")}`}>Se reconnecter</Link>
          : <Button variant="secondary" onClick={reload}>Réessayer</Button>}
      </StatePanel>}
      {state.status === "success" && (state.incidents.length === 0
        ? assigned && hasIncidentFilters(filters) ? <StatePanel title="Aucun résultat" description="Aucun incident ne correspond aux filtres sélectionnés."><Button variant="secondary" onClick={() => changeFilters({})}>Réinitialiser les filtres</Button></StatePanel> : assigned ? <StatePanel title="Aucun incident assigné" description="Aucun incident ne vous est actuellement assigné. Votre file de travail apparaîtra ici dès une nouvelle assignation." /> : <StatePanel title="Aucun incident pour le moment" description="Vos prochains signalements apparaîtront ici. Vous pouvez créer un incident dès maintenant.">
          <Link className="button button-secondary" href="/dashboard/incidents/new">Créer mon premier incident</Link>
        </StatePanel>
        : <>
          <p className="incident-list-summary" role="status">{state.incidents.length} incident{state.incidents.length > 1 ? "s" : ""} · {assigned ? "Dans votre file de travail" : "Du plus récent au plus ancien"}</p>
          <IncidentTable incidents={state.incidents} action={assigned ? i => <>{start.action(i)}{resolve.action(i)}</> : undefined} />
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
