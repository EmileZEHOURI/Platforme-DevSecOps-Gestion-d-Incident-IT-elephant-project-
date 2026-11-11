"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth-provider";
import { IncidentTable } from "@/components/incident-table";
import { AdminError, AssignmentButton, AssignmentDialog, ownerLabel, useTechnicians } from "@/components/assignment-controls";
import { Button, PageHeader, StatePanel } from "@/components/ui";
import { listAllIncidents } from "@/services/incident.service";
import { incidentPriorities, incidentStatuses, type IncidentResponse } from "@/types/incident";
import type { User } from "@/types/auth";

function Management({ admin }: { admin: User }) {
  const directory = useTechnicians();
  const [items, setItems] = useState<IncidentResponse[] | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [query, search] = useState("");
  const [status, setStatus] = useState("");
  const [priority, setPriority] = useState("");
  const [ownership, setOwnership] = useState("");
  const [editing, edit] = useState<IncidentResponse | null>(null);
  const [notice, notify] = useState("");
  useEffect(() => {
    let current = true;
    listAllIncidents().then(data => { if (current) setItems(data); }).catch(e => { if (current) setError(e); });
    return () => { current = false; };
  }, [attempt]);
  function reload() { setError(null); setItems(null); setAttempt(n => n + 1); directory.reload(); }
  const keyword = query.trim().toLocaleLowerCase("fr");
  const visible = (items ?? []).filter(i =>
    (!keyword || [i.title, i.reference].some(v => v.toLocaleLowerCase("fr").includes(keyword))) &&
    (!status || i.status === status) && (!priority || i.priority === priority) &&
    (!ownership || (ownership === "assigned") === (i.assigned_to_id !== null))
  ).sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at) || b.id - a.id);
  function reset() { search(""); setStatus(""); setPriority(""); setOwnership(""); }
  function saved(updated: IncidentResponse) {
    setItems(list => list?.map(i => i.id === updated.id ? updated : i) ?? null);
    notify(`${updated.reference} : assignation enregistrée. Responsable : ${ownerLabel(updated.assigned_to_id, admin, directory.users)}.`);
    edit(null);
  }
  return <>
    <PageHeader eyebrow="ADMINISTRATION" title="Gestion des incidents" description="Consultez les signalements de la plateforme et répartissez leur prise en charge." />
    {notice && <p role="status" className="comment-confirmation">{notice}</p>}
    <section className="panel"><div className="panel-heading"><h2>Tous les incidents</h2>
      <Button variant="ghost" disabled={!items && !error} onClick={reload}>Actualiser ↻</Button></div>
      {error ? <AdminError error={error} retry={reload} /> : !items ? <p className="incident-list-loading" role="status"><span className="spinner" />Chargement des incidents…</p>
        : items.length === 0 ? <StatePanel title="Aucun incident" description="Les nouveaux signalements apparaîtront ici." /> : <>
          <div className="assignment-filters incident-form">
            <div className="field"><label htmlFor="admin-query">Recherche</label><input type="search" id="admin-query" placeholder="Référence ou titre" value={query} onChange={e => search(e.target.value)} /></div>
            <div className="field"><label htmlFor="admin-status">Statut</label><select id="admin-status" value={status} onChange={e => setStatus(e.target.value)}><option value="">Tous les statuts</option>{Object.entries(incidentStatuses).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></div>
            <div className="field"><label htmlFor="admin-priority">Priorité</label><select id="admin-priority" value={priority} onChange={e => setPriority(e.target.value)}><option value="">Toutes les priorités</option>{Object.entries(incidentPriorities).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></div>
            <div className="field"><label htmlFor="admin-owner">Affectation</label><select id="admin-owner" value={ownership} onChange={e => setOwnership(e.target.value)}><option value="">Tous les incidents</option><option value="unassigned">Non assignés</option><option value="assigned">Assignés</option></select></div>
          </div>
          {directory.error && <AdminError error={directory.error} directory retry={directory.reload} />}
          <p role="status" className="incident-list-summary">{visible.length} sur {items.length} · Du plus récent au plus ancien</p>
          {visible.length ? <IncidentTable incidents={visible} management={{
            owner: i => ownerLabel(i.assigned_to_id, admin, directory.users),
            action: i => <AssignmentButton incident={i} open={() => edit(i)} />,
          }} /> : <StatePanel title="Aucun résultat" description="Modifiez votre recherche ou vos filtres."><Button variant="secondary" onClick={reset}>Effacer les filtres</Button></StatePanel>}
        </>}
    </section>
    {editing && <AssignmentDialog admin={admin} incident={editing} directory={directory} close={() => edit(null)} saved={saved} />}
  </>;
}

export function IncidentManagement() {
  const { user } = useAuth();
  if (!user) return null;
  return user.role === "ADMIN" ? <Management key={user.id} admin={user} /> : <StatePanel error title="Accès refusé" description="La gestion des assignations est réservée aux administrateurs." />;
}
