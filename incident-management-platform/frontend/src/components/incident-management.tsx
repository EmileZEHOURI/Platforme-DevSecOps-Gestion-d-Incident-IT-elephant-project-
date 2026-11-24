"use client";

import { IncidentFiltersBar, hasIncidentFilters, filterErrors } from "@/components/incident-filters-bar";
import { IncidentPagination } from "@/components/incident-pagination";
import { useEffect, useState } from "react";
import { useIncidentClose } from "@/components/incident-close";
import { useIncidentResolve } from "@/components/incident-resolve";
import { useIncidentStart } from "@/components/incident-start";
import { useAuth } from "@/components/auth-provider";
import { PriorityDialog } from "@/components/priority-dialog";
import { IncidentTable } from "@/components/incident-table";
import { AdminError, AssignmentButton, AssignmentDialog, ownerLabel, useTechnicians } from "@/components/assignment-controls";
import { Button, PageHeader, StatePanel } from "@/components/ui";
import { listAllIncidents } from "@/services/incident.service";
import { incidentPriorities, type IncidentFilters, type IncidentResponse, type PaginatedIncidentsResponse } from "@/types/incident";
import type { User } from "@/types/auth";

function Management({ admin }: { admin: User }) {
  const directory = useTechnicians();
  const [data, setData] = useState<PaginatedIncidentsResponse | null>(null);
  const items = data?.items;
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [error, setError] = useState<Error | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [filters, setFilters] = useState<IncidentFilters>({});
  const [editing, edit] = useState<{ kind: "priority" | "assignment"; incident: IncidentResponse } | null>(null);
  const [notice, notify] = useState("");
  useEffect(() => {
    let current = true;
    const controller = new AbortController();
    listAllIncidents({ ...filters, page, page_size: pageSize }, controller.signal).then(result => {
      if (!current) return;
      const lastPage = Math.max(1, result.total_pages);
      if (result.items.length === 0 && page > lastPage) { setPage(lastPage); return; }
      setData(result);
    }).catch(e => { if (current) setError(e); });
    return () => { current = false; controller.abort(); };
  }, [attempt, filters, page, pageSize]);
  function reload() { setError(null); setData(null); setAttempt(n => n + 1); directory.reload(); }
  function changeFilters(next: IncidentFilters) { setData(null); setError(null); setFilters(next); setPage(1); }
  function changePage(next: number) { setData(null); setError(null); setPage(next); }
  function changePageSize(next: number) { setData(null); setError(null); setPageSize(next); setPage(1); }
  const start = useIncidentStart(() => {
    reload();
    notify("");
  }, reload);
  const resolve = useIncidentResolve(() => {
    reload();
    notify("");
  }, reload);
  const close = useIncidentClose(() => {
    reload();
    notify("");
  }, reload);
  function saved(updated: IncidentResponse) {
    reload();
    notify(editing?.kind === "priority" ? `${updated.reference} : priorité modifiée — ${incidentPriorities[updated.priority]}.` : `${updated.reference} : assignation enregistrée. Responsable : ${ownerLabel(updated.assigned_to_id, admin, directory.users)}.`);
    edit(null);
  }
  return <>
    <PageHeader eyebrow="ADMINISTRATION" title="Gestion des incidents" description="Consultez les signalements de la plateforme et répartissez leur prise en charge." />
    {start.feedback}
    {resolve.feedback}
    {close.feedback}
    {notice && <p role="status" className="comment-confirmation">{notice}</p>}
    <section className="panel"><div className="panel-heading"><h2>Tous les incidents</h2>
      <Button variant="ghost" disabled={!items && !error} onClick={reload}>Actualiser ↻</Button></div>
      <IncidentFiltersBar filters={filters} onChange={changeFilters} count={data?.total} />
      {error ? <AdminError error={error} retry={reload} descriptions={filterErrors} /> : !items ? <p className="incident-list-loading" role="status"><span className="spinner" />Chargement des incidents…</p>
        : items.length === 0 ? <StatePanel title={hasIncidentFilters(filters) ? "Aucun résultat" : "Aucun incident"} description={hasIncidentFilters(filters) ? "Aucun incident ne correspond aux filtres sélectionnés." : "Les nouveaux signalements apparaîtront ici."}>{hasIncidentFilters(filters) && <Button variant="secondary" onClick={() => changeFilters({})}>Réinitialiser les filtres</Button>}</StatePanel> : <>
          {directory.error && <AdminError error={directory.error} directory retry={directory.reload} />}
          <IncidentTable incidents={items} management={{
            owner: i => ownerLabel(i.assigned_to_id, admin, directory.users),
            action: i => <div className="flex flex-col items-start gap-2">
              {start.action(i)}
              {resolve.action(i)}
              {close.action(i)}
              <AssignmentButton incident={i} open={() => edit({ kind: "assignment", incident: i })} />
              <Button variant="secondary" disabled={i.status === "CLOSED"} onClick={() => edit({ kind: "priority", incident: i })}>Modifier la priorité</Button>
              {i.status === "CLOSED" && <small className="muted">La priorité d’un incident clos ne peut plus être modifiée.</small>}
            </div>,
          }} />
        </>}
      <IncidentPagination data={data ?? undefined} pageSize={pageSize} onPageChange={changePage} onPageSizeChange={changePageSize} />
    </section>
    {editing?.kind === "priority" && <PriorityDialog incident={editing.incident} close={() => edit(null)} saved={saved} />}
    {editing?.kind === "assignment" && <AssignmentDialog admin={admin} incident={editing.incident} directory={directory} close={() => edit(null)} saved={saved} />}
  </>;
}

export function IncidentManagement() {
  const { user } = useAuth();
  if (!user) return null;
  return user.role === "ADMIN" ? <Management key={user.id} admin={user} /> : <StatePanel error title="Accès refusé" description="La gestion des assignations est réservée aux administrateurs." />;
}
