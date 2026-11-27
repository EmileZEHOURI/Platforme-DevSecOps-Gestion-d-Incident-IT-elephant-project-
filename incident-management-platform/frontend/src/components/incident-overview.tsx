"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth-provider";
import { IncidentFiltersBar, hasIncidentFilters } from "@/components/incident-filters-bar";
import { IncidentPagination } from "@/components/incident-pagination";
import { IncidentTable } from "@/components/incident-table";
import { Button, StatePanel } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { listAllIncidents, listAssignedIncidents, listCreatedIncidents } from "@/services/incident.service";
import type { User } from "@/types/auth";
import type { IncidentFilters, PaginatedIncidentsResponse } from "@/types/incident";

type Scope = "created" | "assigned" | "all";
const loaders = { created: listCreatedIncidents, assigned: listAssignedIncidents, all: listAllIncidents };
const destinations = { created: "/dashboard/incidents", assigned: "/dashboard/incidents/assigned", all: "/dashboard/admin/incidents" };

function OverviewResults({ scope }: { scope: Scope }) {
  const [filters, setFilters] = useState<IncidentFilters>({});
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [attempt, setAttempt] = useState(0);
  const [data, setData] = useState<PaginatedIncidentsResponse>();
  const [error, setError] = useState<Error>();
  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    void loaders[scope]({ ...filters, page, page_size: pageSize }, controller.signal)
      .then(result => {
        if (!active) return;
        const lastPage = Math.max(1, result.total_pages);
        if (!result.items.length && page > lastPage) { setPage(lastPage); return; }
        setData(result);
      })
      .catch(reason => {
        if (active) setError(reason instanceof Error ? reason : new Error("Impossible de charger les incidents."));
      });
    return () => { active = false; controller.abort(); };
  }, [scope, filters, page, pageSize, attempt]);

  function clear() { setData(undefined); setError(undefined); }
  function changeFilters(next: IncidentFilters) { clear(); setFilters(next); setPage(1); }
  const expired = error instanceof ApiError && error.status === 401;
  return <div aria-busy={!data && !error}>
    <div className="overview-list-toolbar">
      <span className="muted">Du plus récent au plus ancien</span>
      <Link className="incident-detail-link" href={destinations[scope]}>Voir tous les incidents →</Link>
    </div>
    <IncidentFiltersBar filters={filters} onChange={changeFilters} count={data?.total} />
    {error ? <StatePanel error title={expired ? "Session expirée" : "Impossible de charger les incidents"} description={error.message}>
      {expired ? <Link className="button button-primary" href="/login?next=%2Fdashboard">Se reconnecter</Link>
        : <Button variant="secondary" onClick={() => { clear(); setAttempt(n => n + 1); }}>Réessayer</Button>}
    </StatePanel> : !data ? <div className="incident-list-loading" role="status"><span className="spinner" aria-hidden="true" />Chargement des incidents…</div>
      : data.items.length ? <IncidentTable incidents={data.items} />
      : <StatePanel title={hasIncidentFilters(filters) ? "Aucun résultat" : scope === "assigned" ? "Aucun incident ne vous est actuellement attribué." : scope === "all" ? "Aucun incident enregistré pour le moment." : "Aucun incident pour le moment."}
        description={hasIncidentFilters(filters) ? "Aucun incident ne correspond aux filtres sélectionnés." : "Les nouveaux incidents apparaîtront ici."}>
        {hasIncidentFilters(filters) ? <Button variant="secondary" onClick={() => changeFilters({})}>Effacer les filtres</Button>
          : scope === "created" && <Link className="button button-secondary" href="/dashboard/incidents/new">Signaler un incident</Link>}
      </StatePanel>}
    <IncidentPagination data={data} pageSize={pageSize}
      onPageChange={next => { clear(); setPage(next); }}
      onPageSizeChange={next => { clear(); setPageSize(next); setPage(1); }} />
  </div>;
}

function Overview({ user }: { user: User }) {
  const [scope, setScope] = useState<Scope>(user.role === "ADMIN" ? "all" : user.role === "TECHNICIAN" ? "assigned" : "created");
  return <section className="panel incident-overview" aria-labelledby="incident-overview-title">
    <div className="panel-heading"><div>
      <h2 id="incident-overview-title">{user.role === "ADMIN" ? "Suivi des incidents" : "Mes incidents"}</h2>
      <p className="muted">{user.role === "ADMIN" ? "Consultez et supervisez les incidents de la plateforme." : "Retrouvez et suivez les incidents qui vous concernent."}</p>
    </div></div>
    {user.role === "TECHNICIAN" && <div className="overview-scopes" role="group" aria-label="Périmètre des incidents">
      <Button variant={scope === "assigned" ? "primary" : "secondary"} aria-pressed={scope === "assigned"} onClick={() => setScope("assigned")}>Mes affectations</Button>
      <Button variant={scope === "created" ? "primary" : "secondary"} aria-pressed={scope === "created"} onClick={() => setScope("created")}>Mes déclarations</Button>
    </div>}
    <OverviewResults key={scope} scope={scope} />
  </section>;
}

export function IncidentOverview() {
  const { user } = useAuth();
  return user ? <Overview key={user.id + ":" + user.role} user={user} /> : null;
}
